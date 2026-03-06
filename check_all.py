import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

docs = list(db.collection('casi_local_tasks').stream())
print(f"Total docs: {len(docs)}")
for doc in docs:
    d = doc.to_dict()
    print(f"{doc.id} | Name: {d.get('task_name')} | Status: {d.get('status')} | Time: {d.get('completed_at', d.get('created_at'))}")
