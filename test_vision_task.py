import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone

CRED_PATH = "serviceAccountKey.json"

def trigger_vision_task():
    try:
        cred = credentials.Certificate(CRED_PATH)
        firebase_admin.initialize_app(cred)
    except ValueError:
        pass # Already initialized
        
    db = firestore.client()
    doc_ref = db.collection('casi_local_tasks').document()
    doc_ref.set({
        'task_name': 'Test Google Search (Vision)',
        'platform': 'cloud',
        'status': 'pending',
        'task_type': 'agentic',
        'agentic_prompt': 'Navigate to https://google.com, type "What is the best vacuum cleaner 2026", and press enter to search.',
        'created_at': firestore.SERVER_TIMESTAMP
    })
    
    print(f"SUCCESS! Mock Vision Task pushed to Firebase with ID: {doc_ref.id}")
    print("The CASI Desktop Agent should instantly pick it up and launch Playwright!")

if __name__ == "__main__":
    trigger_vision_task()
