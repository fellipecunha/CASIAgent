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
firebase_admin.initialize_app(cred)
db = firestore.client()

# Create a Recurring Agentic Task 
# This runs immediately (no scheduled_for) but sets interval_minutes so it loops forever.
new_task = {
    'task_name': 'Test Recurring Agentic Task',
    'platform': 'local',
    'status': 'pending', # It starts as pending
    'task_type': 'agentic', # Type: 'agentic' or 'macro'
    'agentic_prompt': 'Please check if I have any new emails.',
    'interval_minutes': 2, # Wait 2 minutes after finishing before running again!
    'created_at': firestore.SERVER_TIMESTAMP
}

print("Pushing a new Recurring Agentic task to Firebase...")
doc_ref = db.collection('casi_local_tasks').document()
doc_ref.set(new_task)

print(f"Successfully created Recurring Task ID: {doc_ref.id}")
print(f"Your CASI Agent will execute this as 'Agentic', and then RESCHEDULE it to run in exactly 2 minutes!")
print("To stop it later, manually go to Firebase console and delete this document.")
