import firebase_admin
from firebase_admin import credentials, firestore
import os
from datetime import datetime, timedelta, timezone

# Ensure credentials exist
CRED_PATH = "serviceAccountKey.json"

if not os.path.exists(CRED_PATH):
    print(f"ERROR: {CRED_PATH} not found.")
    print("Please place your Firebase Admin SDK serviceAccountKey.json in the CASI_agent folder before testing.")
    exit(1)

# Initialize Firebase
cred = credentials.Certificate(CRED_PATH)
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app(cred)
db = firestore.client()

# Create a Recurring Macro Task to open Facebook every 2 minutes
new_task = {
    'task_name': 'Recurring Facebook Macro',
    'platform': 'local',
    'status': 'pending', 
    'task_type': 'macro', # Strict keystrokes
    'skills_content': 'Open Chrome and navigate to Facebook.',
    'interval_minutes': 2, # Wait 2 minutes after finishing before running again
    'action_steps': [
        {'action': 'press', 'key': 'win'},
        {'action': 'sleep', 'time': 1.0},
        {'action': 'write', 'text': 'chrome', 'interval': 0.05},
        {'action': 'sleep', 'time': 1.0},
        {'action': 'press', 'key': 'enter'},
        {'action': 'sleep', 'time': 4.0},
        {'action': 'hotkey', 'keys': ['ctrl', 'l']},
        {'action': 'sleep', 'time': 0.5},
        {'action': 'write', 'text': 'https://www.facebook.com', 'interval': 0.05},
        {'action': 'press', 'key': 'enter'}
    ],
    'created_at': firestore.SERVER_TIMESTAMP
}

print("Pushing a new Recurring Facebook Macro to Firebase...")
doc_ref = db.collection('casi_local_tasks').document()
doc_ref.set(new_task)

print(f"Successfully created Recurring Task ID: {doc_ref.id}")
print("Your CASI Agent will execute this exact macro, and then RESCHEDULE it to run in exactly 2 minutes!")
print("To permanently stop it, you MUST go to the Firebase console and delete this document.")
