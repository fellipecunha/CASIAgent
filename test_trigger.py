import firebase_admin
from firebase_admin import credentials, firestore
import os

# Ensure credentials exist
CRED_PATH = "serviceAccountKey.json"

if not os.path.exists(CRED_PATH):
    print(f"ERROR: {CRED_PATH} not found.")
    print("Please place your Firebase Admin SDK serviceAccountKey.json in the CASI_agent folder before testing.")
    exit(1)

# Initialize Firebase
cred = credentials.Certificate(CRED_PATH)
firebase_admin.initialize_app(cred)
db = firestore.client()

from datetime import datetime, timedelta, timezone

# Create a new dynamic setup task to run in 60 seconds
future_time = datetime.now(timezone.utc) + timedelta(seconds=60)

new_task = {
    'task_name': 'Dynamic Firebase Skill: Scheduled Google Search',
    'platform': 'local',
    'status': 'pending',
    'skills_content': 'Scheduled run!',
    'action_steps': [
        {'action': 'press', 'key': 'win'},
        {'action': 'sleep', 'time': 1.0},
        {'action': 'write', 'text': 'chrome', 'interval': 0.05},
        {'action': 'press', 'key': 'enter'},
        {'action': 'sleep', 'time': 4.0},
        {'action': 'hotkey', 'keys': ['ctrl', 'l']},
        {'action': 'write', 'text': 'https://www.google.com', 'interval': 0.05},
        {'action': 'press', 'key': 'enter'}
    ],
    'created_at': firestore.SERVER_TIMESTAMP,
    'scheduled_for': future_time # <-- TELLS AGENT TO WAIT!
}

print(f"Pushing a new scheduled task to Firebase (Scheduled for 60 seconds from now: {future_time})...")
doc_ref = db.collection('casi_local_tasks').document()
doc_ref.set(new_task)

print(f"Successfully created Scheduled Task ID: {doc_ref.id}")
print("Your CASI Agent will see it, ignore it immediately, and then pick it up when the time arrives!")
