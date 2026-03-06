import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

docs = list(db.collection('casi_local_tasks').where('status', '==', 'pending').stream())
print(f"Found {len(docs)} pending docs.")
for doc in docs:
    print(f"{doc.id}: {doc.to_dict()}")
