import json

log_path = 'C:/Users/Manib/.gemini/antigravity/brain/9de23203-df1d-40f5-8dc4-b9fd626b9800/.system_generated/logs/overview.txt'

with open(log_path, encoding='utf-8') as f:
    for i, line in enumerate(f):
        data = json.loads(line)
        content = data.get('content', '')
        if '69e05b0c4ae1ff103aa98124' in content:
            print(f"Line {i}: index={data.get('step_index')}, source={data.get('source')}, type={data.get('type')}, len={len(content)}")
            print("Contains the target!")
