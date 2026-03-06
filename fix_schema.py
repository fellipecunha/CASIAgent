import os

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Revert collection names
    content = content.replace("db.collection('casi_tasks')", "db.collection('casi_local_tasks')")
    content = content.replace("Monitoring casi_tasks...", "Monitoring casi_local_tasks...")
    
    # Revert platforms
    content = content.replace("platform', '==', 'cloud'", "platform', '==', 'local'")
    content = content.replace("get('platform') == 'cloud'", "get('platform') == 'local'")
    content = content.replace("No cloud tasks pending", "No tasks pending")
    
    # Just in case there are other occurrences
    content = content.replace("casi_local_local_tasks", "casi_local_tasks")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

replace_in_file('casi_agent.py')
replace_in_file('casi_vision_agent.py')
replace_in_file('test_vision_task.py')
print("Reverted all cloud logic to local.")
