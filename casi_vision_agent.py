import os
import sys
import threading
import time
import json
import base64
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
from openai import OpenAI
from playwright.sync_api import sync_playwright

load_dotenv()

# Ensure paths are compatible whether running locally or compiled via PyInstaller on Windows/Mac
if hasattr(sys, '_MEIPASS'):
    # Running in PyInstaller bundle
    APP_DIR = sys._MEIPASS
    BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0])) # Where the executable is located
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = APP_DIR

# If running from /dist, point root backwards
if os.path.basename(BASE_DIR).lower() == 'dist':
    ROOT_DIR = os.path.dirname(BASE_DIR)
else:
    ROOT_DIR = BASE_DIR

CRED_PATH = os.path.join(ROOT_DIR, "serviceAccountKey.json")

# Ensure the OpenAI API Key is in the .env or environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

prompt_system = """You are a browser automation agent.
You are given a user task to perform on a web page, the current screenshot of the page, and the past actions you have taken.
You must output a JSON object representing your next action.

Allowed actions:
1. {"action": "goto", "url": "https://example.com"}
2. {"action": "click", "x": 100, "y": 200}
3. {"action": "type", "text": "hello world"}
4. {"action": "press", "key": "Enter"}
5. {"action": "wait", "seconds": 2}
6. {"action": "scroll", "direction": "down"}
7. {"action": "done", "reason": "Task completed successfully"}

Respond ONLY with the JSON format, no markdown wrap, no other text."""

def execute_vision_loop(db, doc, task_name, agentic_prompt):
    print(f"\n--- Starting Vision Agent Task: {doc.id} | Name: {task_name} ---")
    print(f"Goal: {agentic_prompt}")
    
    if not OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY not found in environment.")
        db.collection('casi_local_tasks').document(doc.id).update({'status': 'failed'})
        return

    client = OpenAI(api_key=OPENAI_API_KEY)
    
    with sync_playwright() as p:
        # Detect actual user Playwright install path on Windows instead of PyInstaller Temp
        # Usually: C:\Users\Username\AppData\Local\ms-playwright\chromium-XXXX\chrome-win64\chrome.exe
        import glob
        local_app_data = os.getenv('LOCALAPPDATA')
        playwright_path = os.path.join(local_app_data, 'ms-playwright', 'chromium-*', 'chrome-win*', 'chrome.exe')
        matched_paths = glob.glob(playwright_path)
        
        executable_path = matched_paths[0] if matched_paths else None
        print(f"Playwright routing to actual user executable: {executable_path}")
        
        # Launch non-headless browser with a persistent context to save logins/cookies
        user_data_dir = os.path.join(ROOT_DIR, "browser_data")
        browser_context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            executable_path=executable_path,
            viewport={"width": 1280, "height": 800}
        )
        
        # Use the default page created by persistent context
        page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()
        
        history = []
        max_steps = 20
        step = 0
        
        while step < max_steps:
            step += 1
            print(f"\n--- Vision Step {step}/{max_steps} ---")
            time.sleep(1) # Give page time to settle
            
            # Take screenshot
            screenshot_path = os.path.join(APP_DIR, "temp_screenshot.png")
            page.screenshot(path=screenshot_path)
            
            with open(screenshot_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            history_str = json.dumps(history, indent=2)
            
            prompt_user = f"Task: {agentic_prompt}\nPast Actions:\n{history_str}\n\nWhat is your next action based on the current screenshot?"
            
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": prompt_system
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt_user
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=300
                )
                
                content = response.choices[0].message.content.strip()
                if content.startswith('```json'):
                    content = content[7:-3].strip()
                elif content.startswith('```'):
                    content = content[3:-3].strip()
                    
                print(f"LLM Decision: {content}")
                action_data = json.loads(content)
                action = action_data.get("action")
                history.append(action_data)
                
                if action == "goto":
                    page.goto(action_data.get("url"))
                elif action == "click":
                    page.mouse.click(action_data.get("x"), action_data.get("y"))
                elif action == "type":
                    page.keyboard.type(action_data.get("text"))
                elif action == "press":
                    page.keyboard.press(action_data.get("key"))
                elif action == "wait":
                    time.sleep(action_data.get("seconds", 1))
                elif action == "scroll":
                    if action_data.get("direction") == "down":
                        page.mouse.wheel(0, 500)
                    else:
                        page.mouse.wheel(0, -500)
                elif action == "done":
                    print(f"Task Complete: {action_data.get('reason')}")
                    break
                else:
                    print(f"Unknown action: {action}")
                    
            except Exception as e:
                print(f"Vision loop error: {e}")
                time.sleep(2)
                
        browser_context.close()
    
    # Clean up temp screenshot
    if os.path.exists(os.path.join(APP_DIR, "temp_screenshot.png")):
        os.remove(os.path.join(APP_DIR, "temp_screenshot.png"))
        
    print("Vision Loop Completed. Deferring Firebase status update to main process_task handler.")

def start_firebase_listener(db):
    print("Firebase listener for AGENTIC tasks started. Monitoring casi_local_tasks...")

    def on_snapshot(col_snapshot, changes, read_time):
        for change in changes:
            doc = change.document
            data = doc.to_dict() or {}
            
            # Listen purely for agentic tasks
            if data.get('platform') == 'local' and data.get('status') == 'pending' and data.get('task_type') == 'agentic':
                print(f"  -> Agentic Match found! Locking doc {doc.id} for processing...")
                try:
                    # Lock for processing
                    db.collection('casi_local_tasks').document(doc.id).update({'status': 'processing'})
                    
                    # Start async vision execution
                    task_name = data.get('task_name', 'Unknown Task')
                    agentic_prompt = data.get('agentic_prompt', '')
                    t = threading.Thread(target=execute_vision_loop, args=(db, doc, task_name, agentic_prompt))
                    t.start()
                except Exception as e:
                    print(f"  -> Error trying to process doc {doc.id}: {e}")
                    
    col_query = db.collection('casi_local_tasks')
    col_watch = col_query.on_snapshot(on_snapshot)
    
    while True:
        time.sleep(3600)

def run_agent():
    print("Initializing Experimental CASI Vision Agent...")
    if not os.path.exists(CRED_PATH):
        print(f"ERROR: {CRED_PATH} not found.")
        print("Please place your Firebase Admin SDK serviceAccountKey.json in the CASI_agent folder.")
        return

    cred = credentials.Certificate(CRED_PATH)
    try:
        firebase_admin.initialize_app(cred, name="VisionAgent") # Use a different app name to avoid conflicts if both run
    except ValueError:
        pass # Already initialized
        
    db = firestore.client(app=firebase_admin.get_app("VisionAgent"))
    start_firebase_listener(db)

if __name__ == "__main__":
    run_agent()
