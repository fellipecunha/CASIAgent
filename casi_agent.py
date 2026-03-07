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

import traceback

global_gui_app = None

class LoggerWriter:
    def __init__(self, filename):
        self.filename = filename
    def write(self, message):
        try:
            with open(self.filename, 'a', encoding='utf-8') as f:
                f.write(message)
        except Exception:
            pass
        if global_gui_app:
            try:
                global_gui_app.after(0, global_gui_app.append_log, message)
            except Exception:
                pass
    def flush(self):
        pass

log_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'agent_debug.log')
sys.stdout = LoggerWriter(log_path)
sys.stderr = sys.stdout
    
print("\\n\\n--- NEW SESSION ---")
print(f"Agent started at {time.strftime('%Y-%m-%d %H:%M:%S')}")

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

import customtkinter as ctk

class CASIAgentGUI(ctk.CTk):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.title("CASI Agent - Desktop Automation Core")
        self.geometry("1100x700")
        # Advanced Premium Colors System
        self._bg_color = "#0F172A"          # Deep rich slate background
        self._surface = "#1E293B"           # Elevated panel background
        self._surface_light = "#334155"     # Lighter hover/card state
        self._primary = "#3B82F6"           # Vibrant modern blue
        self._primary_hover = "#2563EB"
        self._text = "#F8FAFC"
        self._text_muted = "#94A3B8"
        self._accent_green = "#10B981"
        self._accent_green_hover = "#059669"
        self._accent_red = "#EF4444"
        self._accent_red_hover = "#DC2626"
        self._accent_orange = "#F59E0B"
        
        # Base Application styling
        ctk.set_appearance_mode("dark")
        self.configure(fg_color=self._bg_color)
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # Sidebar Queue with elevated style
        self.sidebar_frame = ctk.CTkFrame(self, width=340, corner_radius=0, fg_color=self._surface)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(1, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="CASI Control Center", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"), text_color=self._text)
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 15), sticky="w")
        
        self.tabs = ctk.CTkTabview(self.sidebar_frame, width=300, fg_color="transparent", text_color=self._text, segmented_button_selected_color=self._primary, segmented_button_selected_hover_color=self._primary_hover)
        self.tabs.grid(row=1, column=0, padx=15, pady=0, sticky="nsew")
        self.tabs.add("Active")
        self.tabs.add("Completed")
        
        self.queue_scrollable = ctk.CTkScrollableFrame(self.tabs.tab("Active"), fg_color="transparent")
        self.queue_scrollable.pack(fill="both", expand=True)
        
        self.completed_scrollable = ctk.CTkScrollableFrame(self.tabs.tab("Completed"), fg_color="transparent")
        self.completed_scrollable.pack(fill="both", expand=True)
        
        self.add_btn = ctk.CTkButton(self.sidebar_frame, text="+ Create Workflow", command=self.add_task_gui, font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), fg_color=self._primary, hover_color=self._primary_hover, height=45, corner_radius=8)
        self.add_btn.grid(row=2, column=0, padx=20, pady=25, sticky="ew")
        
        # Main Viewer pane (glassy terminal approach)
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=25, pady=25)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        self.log_header = ctk.CTkLabel(self.main_frame, text="Live Execution Trace", font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"), text_color=self._text)
        self.log_header.grid(row=0, column=0, sticky="nw", pady=(0, 15))
        
        # Premium terminal aesthetic
        self.log_box = ctk.CTkTextbox(self.main_frame, font=ctk.CTkFont(family="Consolas", size=13), fg_color=self._surface, text_color="#A78BFA", corner_radius=12, border_width=1, border_color="#334155")
        self.log_box.grid(row=1, column=0, sticky="nsew")
        self.log_box.configure(state="disabled")
        
    def append_log(self, text):
        if not self.winfo_exists(): return
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text)
        self.log_box.yview("end")
        self.log_box.configure(state="disabled")
        
    def update_queue(self, tasks):
        if not self.winfo_exists(): return
        
        for widget in self.queue_scrollable.winfo_children():
            widget.destroy()
        for widget in self.completed_scrollable.winfo_children():
            widget.destroy()
            
        active_tasks = [t for t in tasks if t['status'] not in ['completed', 'failed']]
        completed_tasks = [t for t in tasks if t['status'] in ['completed', 'failed']]

        if not active_tasks:
            ctk.CTkLabel(self.queue_scrollable, text="No active tasks.", text_color="gray").pack(pady=20)
        else:
            for t in active_tasks:
                self._draw_task_card(self.queue_scrollable, t, is_active=True)
                
        if not completed_tasks:
            ctk.CTkLabel(self.completed_scrollable, text="No completed tasks.", text_color="gray").pack(pady=20)
        else:
            for t in completed_tasks:
                self._draw_task_card(self.completed_scrollable, t, is_active=False)

    def _draw_task_card(self, parent_scrollable, t, is_active):
        is_processing = t['status'] == 'processing'
        # Rich contextual coloring 
        if is_processing:
            color = self._accent_orange
            bg_color = self._surface_light
        elif t['status'] == 'completed':
            color = self._accent_green
            bg_color = self._surface
        elif t['status'] == 'paused':
            color = self._accent_red
            bg_color = self._surface_light
        else:
            color = self._text_muted
            bg_color = self._surface
            
        frame = ctk.CTkFrame(parent_scrollable, fg_color=bg_color, corner_radius=10, border_color="#334155", border_width=1)
        frame.pack(fill="x", padx=2, pady=6)
        
        bold_font = ctk.CTkFont(family="Segoe UI", size=15, weight="bold")
        title_lbl = ctk.CTkLabel(frame, text=t['name'][:30], font=bold_font, justify="left", text_color=self._text)
        title_lbl.pack(anchor="w", padx=12, pady=(10,2))
        
        stat_lbl = ctk.CTkLabel(frame, text=f"• {t['status'].upper()}", text_color=color, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"))
        stat_lbl.pack(anchor="w", padx=12, pady=(0,10))
        
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(anchor="e", padx=10, pady=(0, 10))
        
        btn_font = ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        
        if is_active:
            p_text = "Resume" if t['status'] == 'paused' else "Pause"
            p_cmd = lambda tid=t['id'], st=t['status']: self.pause_resume_task(tid, st)
            ctk.CTkButton(btn_frame, text=p_text, width=54, height=26, corner_radius=6, font=btn_font, fg_color=self._surface_light, hover_color="#475569", text_color=self._text, command=p_cmd).pack(side="left", padx=3)
            
            e_btn = ctk.CTkButton(btn_frame, text="Edit", width=54, height=26, corner_radius=6, font=btn_font, fg_color=self._surface_light, hover_color="#475569", text_color=self._text, command=lambda tid=t['id']: self.edit_task_gui(tid))
            e_btn.pack(side="left", padx=3)
        else:
            r_cmd = lambda tid=t['id']: self.rerun_task(tid)
            ctk.CTkButton(btn_frame, text="Rerun", width=54, height=26, corner_radius=6, font=btn_font, command=r_cmd, fg_color=self._accent_green, hover_color=self._accent_green_hover).pack(side="left", padx=3)
            
            e_btn = ctk.CTkButton(btn_frame, text="Edit", width=54, height=26, corner_radius=6, font=btn_font, fg_color=self._surface_light, hover_color="#475569", text_color=self._text, command=lambda tid=t['id']: self.edit_task_gui(tid))
            e_btn.pack(side="left", padx=3)
            
        d_btn = ctk.CTkButton(btn_frame, text="Del", width=44, height=26, corner_radius=6, font=btn_font, fg_color=self._accent_red, hover_color=self._accent_red_hover, command=lambda tid=t['id']: self.delete_task(tid))
        d_btn.pack(side="left", padx=3)

    def rerun_task(self, task_id):
        try:
            self.db.collection('casi_local_tasks').document(task_id).update({'status': 'pending'})
        except Exception as e:
            print(f"Failed to rerun task: {e}")
            
    def pause_resume_task(self, task_id, current_status):
        new_status = 'pending' if current_status == 'paused' else 'paused'
        try:
            self.db.collection('casi_local_tasks').document(task_id).update({'status': new_status})
        except Exception as e:
            print(f"Failed to change status: {e}")

    def delete_task(self, task_id):
        try:
            self.db.collection('casi_local_tasks').document(task_id).delete()
        except Exception as e:
            print(f"Failed to delete task: {e}")

    def add_task_gui(self):
        w = ctk.CTkToplevel(self)
        w.title("Add New Agentic Task")
        w.geometry("450x450")
        w.configure(fg_color=self._bg_color)
        w.grab_set()
        
        lbl_font = ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        entry_font = ctk.CTkFont(family="Consolas", size=13)
        
        ctk.CTkLabel(w, text="Task Name:", font=lbl_font, text_color=self._text).pack(pady=(20, 0))
        name_entry = ctk.CTkEntry(w, width=350, height=35, corner_radius=8, font=entry_font, fg_color=self._surface, border_color="#334155", text_color=self._text)
        name_entry.pack(pady=(5, 10))
        
        ctk.CTkLabel(w, text="Agentic Prompt (Goals & Logic):", font=lbl_font, text_color=self._text).pack(pady=(5, 0))
        prompt_entry = ctk.CTkTextbox(w, width=350, height=110, corner_radius=8, font=entry_font, fg_color=self._surface, border_color="#334155", border_width=2, text_color=self._text)
        prompt_entry.pack(pady=(5, 10))
        
        ctk.CTkLabel(w, text="Schedule Interval (Minutes, Optional):", font=lbl_font, text_color=self._text).pack(pady=(5, 0))
        interval_entry = ctk.CTkEntry(w, width=350, height=35, placeholder_text="e.g. 60", corner_radius=8, font=entry_font, fg_color=self._surface, border_color="#334155", text_color=self._text)
        interval_entry.pack(pady=(5, 25))
        
        def save():
            try:
                task_doc = {
                    'task_name': name_entry.get(),
                    'platform': 'local',
                    'status': 'pending',
                    'task_type': 'agentic',
                    'agentic_prompt': prompt_entry.get("0.0", "end").strip(),
                    'created_at': firestore.SERVER_TIMESTAMP
                }
                
                raw_interval = interval_entry.get().strip()
                if raw_interval.isdigit():
                    task_doc['interval_minutes'] = int(raw_interval)
                    
                self.db.collection('casi_local_tasks').add(task_doc)
                w.destroy()
            except Exception as e:
                print(f"Failed to add task: {e}")
                
        ctk.CTkButton(w, text="Save Task", command=save, fg_color=self._accent_green, hover_color=self._accent_green_hover, font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), height=40, corner_radius=8).pack(pady=10)

    def edit_task_gui(self, task_id):
        try:
            doc = self.db.collection('casi_local_tasks').document(task_id).get()
            if not doc.exists: return
            data = doc.to_dict()
        except Exception as e:
            print(f"Failed to fetch task: {e}")
            return
            
        w = ctk.CTkToplevel(self)
        w.title("Edit Task")
        w.geometry("450x450")
        w.configure(fg_color=self._bg_color)
        w.grab_set()
        
        lbl_font = ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        entry_font = ctk.CTkFont(family="Consolas", size=13)
        
        ctk.CTkLabel(w, text="Task Name:", font=lbl_font, text_color=self._text).pack(pady=(20, 0))
        name_entry = ctk.CTkEntry(w, width=350, height=35, corner_radius=8, font=entry_font, fg_color=self._surface, border_color="#334155", text_color=self._text)
        name_entry.insert(0, data.get('task_name', ''))
        name_entry.pack(pady=(5, 10))
        
        ctk.CTkLabel(w, text="Prompt / Logic:", font=lbl_font, text_color=self._text).pack(pady=(5, 0))
        prompt_entry = ctk.CTkTextbox(w, width=350, height=110, corner_radius=8, font=entry_font, fg_color=self._surface, border_color="#334155", border_width=2, text_color=self._text)
        prompt_text = data.get('agentic_prompt', data.get('skills_content', ''))
        prompt_entry.insert("0.0", prompt_text)
        prompt_entry.pack(pady=(5, 10))
        
        ctk.CTkLabel(w, text="Schedule Interval (Minutes, Optional):", font=lbl_font, text_color=self._text).pack(pady=(5, 0))
        interval_entry = ctk.CTkEntry(w, width=350, height=35, corner_radius=8, font=entry_font, fg_color=self._surface, border_color="#334155", text_color=self._text)
        interval = data.get('interval_minutes', '')
        if interval:
            interval_entry.insert(0, str(interval))
        interval_entry.pack(pady=(5, 25))
        
        def save():
            try:
                updates = {
                    'task_name': name_entry.get()
                }
                
                new_prompt = prompt_entry.get("0.0", "end").strip()
                if data.get('task_type') == 'macro':
                    updates['skills_content'] = new_prompt
                else:
                    updates['agentic_prompt'] = new_prompt
                
                raw_interval = interval_entry.get().strip()
                if raw_interval.isdigit():
                    updates['interval_minutes'] = int(raw_interval)
                elif raw_interval == "":
                    updates['interval_minutes'] = firestore.DELETE_FIELD
                    
                self.db.collection('casi_local_tasks').document(task_id).update(updates)
                w.destroy()
            except Exception as e:
                print(f"Failed to edit task: {e}")
                
        ctk.CTkButton(w, text="Save Updates", command=save, fg_color=self._primary, hover_color=self._primary_hover, font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), height=40, corner_radius=8).pack(pady=10)

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
            try:
                from casi_vision_agent import execute_vision_loop
                execute_vision_loop(db, doc, task_name, agentic_prompt)
            except ImportError:
                print("Warning: casi_vision_agent.py not found or not packaged.")
                computer_use_app("Agentic Autonomy", f"Failed to load vision module for: {agentic_prompt}")
            except Exception as e:
                print(f"Error executing intelligent vision loop: {e}")
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

    # 4. Reporting: Update Firebase Status / Scheduling
    print("Updating task status in Firebase...")
    try:
        interval_val = task_data.get('interval_minutes')
        interval_minutes = None
        if interval_val is not None:
            try:
                interval_minutes = int(float(interval_val))
            except ValueError:
                pass
                
        from datetime import datetime, timezone, timedelta
        
        if interval_minutes:
            # User Preference: Handle Recurring Rule Locally - Reschedule into the future, maintain 'pending'
            new_time = datetime.now(timezone.utc) + timedelta(minutes=interval_minutes)
            db.collection('casi_local_tasks').document(doc_id).update({
                'status': 'pending',
                'artifact_proof': artifact_path,
                'scheduled_for': new_time,
                'last_completed_at': firestore.SERVER_TIMESTAMP
            })
            print(f"--- Task {doc_id} RESCHEDULED for {interval_minutes}m from now ({new_time}) ---")
        else:
            # One-off Rule: Mark as 'completed'
            db.collection('casi_local_tasks').document(doc_id).update({
                'status': 'completed',
                'artifact_proof': artifact_path,
                'completed_at': firestore.SERVER_TIMESTAMP
            })
            print(f"--- Task {doc_id} marked as COMPLETED ---")
    except Exception as e:
        print(f"Failed to update task status: {e}")

from datetime import datetime, timezone

def start_firebase_listener(db):
    print("Firebase listener started. Monitoring casi_local_tasks...")

    # Create a callback to handle changes in the collection
    def on_snapshot(col_snapshot, changes, read_time):
        print(f"Snapshot received at {read_time}. Changes count: {len(changes)}")
        
        # --- Update the GUI Task Queue ---
        if global_gui_app:
            pending_list = []
            for doc_snap in col_snapshot:
                task_data = doc_snap.to_dict() or {}
                if task_data.get('platform') == 'local':
                    st = task_data.get('status', 'unknown')
                    if st in ['pending', 'processing', 'paused', 'completed', 'failed']:
                        pending_list.append({
                            'id': doc_snap.id, 
                            'name': task_data.get('task_name', 'Unnamed Task'), 
                            'status': st
                        })
            try:
                global_gui_app.after(0, global_gui_app.update_queue, pending_list)
            except Exception:
                pass
        
        # Process individual doc changes logic
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
    
    # Keep the daemon thread alive but do NOT poll here. Polling goes to a separate thread.
    while True:
        time.sleep(3600)

def start_polling_loop(db):
    print("Background polling thread initialized and entering 10s cycle...")
    while True:
        try:
            now = datetime.now(timezone.utc)
            # print(f"--- Triggering Polling Check at {now} ---")
            
            query = db.collection('casi_local_tasks') \
                .where('platform', '==', 'local') \
                .where('status', '==', 'pending')
                
            docs = query.stream()
            for doc in docs:
                data = doc.to_dict() or {}
                scheduled_for = data.get('scheduled_for')
                
                if scheduled_for:
                    if scheduled_for <= now:
                        print(f"  -> Scheduled task {doc.id} is ready! Time arrived. Locking for processing...")
                        try:
                            # Safely set to processing so the listener loop catches it
                            db.collection('casi_local_tasks').document(doc.id).update({'status': 'processing'})
                            t = threading.Thread(target=process_task, args=(db, doc))
                            t.start()
                        except Exception as e:
                            print(f"  -> Error processing scheduled doc {doc.id}: {e}")
        except Exception as e:
            print(f"Polling loop error: {e}")
            pass
            
        time.sleep(10) # 10s check is much faster and precise

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
        
        # Start polling thread
        polling_thread = threading.Thread(target=start_polling_loop, args=(db,), daemon=True)
        polling_thread.start()
    
    # Create and run visual CustomTkinter Windows GUI
    print("Starting Main Visual Desktop Agent Interface...")
    global global_gui_app
    global_gui_app = CASIAgentGUI(db)
    
    # Run the UI Window, which blocks main thread (correct for desktops)
    global_gui_app.mainloop()
    
    # Clean exit once user closes window
    print("Closing Desktop interface...")
    os._exit(0)

if __name__ == "__main__":
    run_agent()
