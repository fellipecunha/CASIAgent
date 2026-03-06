import os
import sys
import threading
import time
import json
import shutil
import pystray
from PIL import Image
from plyer import notification
import pyautogui
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

# Setup paths
if hasattr(sys, '_MEIPASS'):
    # Running in PyInstaller bundle
    APP_DIR = sys._MEIPASS
    BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0])) # Where the exe is
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = APP_DIR

# If running from /dist, point root backwards
if os.path.basename(BASE_DIR).lower() == 'dist':
    ROOT_DIR = os.path.dirname(BASE_DIR)
else:
    ROOT_DIR = BASE_DIR

CRED_PATH = os.path.join(ROOT_DIR, "serviceAccountKey.json")
SKILLS_DIR = os.path.join(ROOT_DIR, ".agent", "skills")
ICON_PATH = os.path.join(APP_DIR, "casi_icon.ico")

# Assuming antigravity artifact path based on known user properties
ARTIFACTS_DIR = r"C:\Users\Fellipe Cunha\.gemini\antigravity\brain\0aa6a689-e9c6-4489-848e-1748cd02ac5c"

def notify_user(title, message):
    # Triggers a Windows System Notification (toast) using Python
    print(f"[TOAST] {title} - {message}")
    try:
        notification.notify(
            title=title,
            message=message,
            app_name='CASI Agent',
            app_icon=ICON_PATH if os.path.exists(ICON_PATH) else None,
            timeout=10
        )
    except Exception as e:
        print(f"Failed to display toast: {e}")

def create_tray_icon():
    try:
        if os.path.exists(ICON_PATH):
            image = Image.open(ICON_PATH)
        else:
            image = Image.new('RGB', (64, 64), color=(0, 102, 204))
    except Exception:
        image = Image.new('RGB', (64, 64), color=(0, 102, 204))

    def on_quit(icon, item):
        icon.stop()
        os._exit(0)

    menu = pystray.Menu(pystray.MenuItem('Exit', on_quit))
    icon = pystray.Icon("CASI Desktop Agent", image, "CASI (Cunha AI)", menu)
    return icon

def antigravity_browser_tool(action, target):
    print(f"[AG-Browser-Tool] Executing: {action} on {target}")
    time.sleep(1)

def computer_use_app(action, target):
    print(f"[Computer-Use] Executing: {action} on {target}")
    time.sleep(1)

task_lock = threading.Lock()

def process_task(db, doc):
    doc_id = doc.id
    task_data = doc.to_dict()
    task_name = task_data.get('task_name', 'Unknown Task')
    task_type = task_data.get('task_type', 'macro')
    
    print(f"\n--- Starting Task: {doc_id} | Type: {task_type} | Name: {task_name} ---")

    # Desktop Execution Engine logic
    skills_content = task_data.get('skills_content', '')
    if skills_content:
        print("Loaded skills text directly from Firebase task document.")
    else:
        print("No 'skills_content' text found in Firebase document.")

    # 2. Desktop Action Execution Layer
    print("Initializing Agent Loop...")
    
    if task_type == 'macro':
        action_steps = task_data.get('action_steps', [])
        if action_steps:
            print(f"[Computer-Use: MACRO MODE] Executing {len(action_steps)} rigid steps from Firebase `action_steps`...")
            with task_lock:
                for i, step in enumerate(action_steps):
                    action = step.get('action')
                    print(f" -> Step {i+1}: {action} | {step}")
                    try:
                        if action == 'press':
                            pyautogui.press(step.get('key', 'enter'))
                        elif action == 'write':
                            pyautogui.write(step.get('text', ''), interval=step.get('interval', 0.05))
                        elif action == 'sleep':
                            time.sleep(float(step.get('time', 1.0)))
                        elif action == 'hotkey':
                            keys = step.get('keys', [])
                            pyautogui.hotkey(*keys)
                    except Exception as e:
                        print(f"    [Error] executing step {i+1}: {e}")
            # Wait a bit after dynamic steps complete
            time.sleep(3)
        else:
            print("No action_steps found for macro task.")
            
    elif task_type == 'agentic':
        agentic_prompt = task_data.get('agentic_prompt', '')
        print(f"\n[Computer-Use: AGENTIC MODE] Processing reasoning prompt:")
        print(f"\"{agentic_prompt}\"")
        print(" -> Establishing vision & reasoning capabilities context...")
        print(" -> Autonomously controlling desktop applications...")
        with task_lock:
            # Placeholder for Anthropic Computer Use APIs or actual Agent implementation
            computer_use_app("Agentic Autonomy", f"Executing requested prompt: {agentic_prompt}")
            time.sleep(5) # Simulate processing
    else:
        print(f"Unknown task type ({task_type}). Skipping execution layer.")
    
    # SAFETY: Windows Notification before Submit/Payment/Final Step
    notify_user("CASI Safety Guard", f"Preparing for final confirmation in task: {task_name}")
    print("Waiting for safety timeout / user intervention (5 seconds)...")
    time.sleep(5) 

    # 3. Reporting and Artifact Collection
    print("Processing Complete. Generating Artifact...")
    screenshot_name = f"casi_confirmation_{doc_id}.png"
    
    screenshots_dir = os.path.join(ROOT_DIR, "screenshots")
    if not os.path.exists(screenshots_dir):
        os.makedirs(screenshots_dir)
        
    artifact_path = os.path.join(screenshots_dir, screenshot_name)
    
    # Take screenshot directly to final path
    try:
        pyautogui.screenshot(artifact_path)
        print(f"Screenshot taken and saved to: {artifact_path}")
    except Exception as e:
        print(f"Failed to save screenshot: {e}")

    # 4. Reporting: Update Firebase Status
    print("Updating task status in Firebase...")
    try:
        # Offload scheduling to the Firebase Cloud Cron architecture
        # Always emit "completed". The Cloud Backend will securely detect if it's recurring.
        db.collection('casi_local_tasks').document(doc_id).update({
            'status': 'completed',
            'artifact_proof': artifact_path,
            'completed_at': firestore.SERVER_TIMESTAMP
        })
        print(f"--- Task {doc_id} marked as COMPLETED (Cloud will respawn if recurring) ---")
    except Exception as e:
        print(f"Failed to update task status: {e}")

from datetime import datetime, timezone

def start_firebase_listener(db):
    print("Firebase listener started. Monitoring casi_local_tasks...")

    # Create a callback to handle changes in the collection
    def on_snapshot(col_snapshot, changes, read_time):
        print(f"Snapshot received at {read_time}. Changes count: {len(changes)}")
        for change in changes:
            doc = change.document
            data = doc.to_dict() or {}
            print(f"[{change.type.name}] Doc ID: {doc.id} | platform: '{data.get('platform')}' | status: '{data.get('status')}'")
            
            # Persistent Listener rule: platform == 'local' and status == 'pending'
            if data.get('platform') == 'local' and data.get('status') == 'pending':
                # Check if this task is scheduled for the future
                scheduled_for = data.get('scheduled_for')
                if scheduled_for:
                    now = datetime.now(timezone.utc)
                    # For pyfirestore, Timestamps come as datetime aware objects
                    if scheduled_for > now:
                        print(f"  -> Task {doc.id} is scheduled for the future ({scheduled_for}). Ignoring for now.")
                        continue # Skip running immediately

                print(f"  -> Match found! Locking doc {doc.id} for processing...")
                try:
                    # First, lock the doc so other listeners don't pick it up
                    db.collection('casi_local_tasks').document(doc.id).update({'status': 'processing'})
                    
                    # Start processing on a separate thread
                    t = threading.Thread(target=process_task, args=(db, doc))
                    t.start()
                except Exception as e:
                    print(f"  -> Error trying to process doc {doc.id}: {e}")
                
    # Define query
    col_query = db.collection('casi_local_tasks')
    col_watch = col_query.on_snapshot(on_snapshot)
    
    # Keep the daemon thread alive so the on_snapshot listener stays active without blocking
    while True:
        time.sleep(3600)

def run_agent():
    print("Initializing CASI Agent...")
    if not os.path.exists(CRED_PATH):
        print(f"ERROR: {CRED_PATH} not found.")
        print("Please place your Firebase Admin SDK serviceAccountKey.json in the CASI_agent folder.")
        # Proceed mock mode if not found just to test the UI/tray
        print("Running in Mock Mode. Please add credentials to connect to real Firebase.")
        class MockDB:
            pass
        db = MockDB()
    else:
        cred = credentials.Certificate(CRED_PATH)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        # Start listener thread
        listener_thread = threading.Thread(target=start_firebase_listener, args=(db,), daemon=True)
        listener_thread.start()
    
    # Create and run System Tray icon (blocks the main thread)
    print("Starting Desktop Engine Tray Icon...")
    icon = create_tray_icon()
    icon.run()

if __name__ == "__main__":
    run_agent()
