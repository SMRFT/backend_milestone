import json

log_path = 'C:/Users/Manib/.gemini/antigravity/brain/9de23203-df1d-40f5-8dc4-b9fd626b9800/.system_generated/logs/overview.txt'

with open(log_path, encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        if data.get('step_index') == 1:
            print("Step 1 content:")
            print(data.get('content'))
