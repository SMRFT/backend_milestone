import json

log_path = 'C:/Users/Manib/.gemini/antigravity/brain/9de23203-df1d-40f5-8dc4-b9fd626b9800/.system_generated/logs/overview.txt'

with open(log_path, encoding='utf-8') as f:
    for i, line in enumerate(f):
        try:
            data = json.loads(line)
            print(f"Line {i}: index={data.get('step_index')}, source={data.get('source')}, type={data.get('type')}, content_len={len(data.get('content', ''))}")
            if data.get('step_index') == 0:
                print("Step 0 content starts with:")
                print(data['content'][:500])
                print("Step 0 content ends with:")
                print(data['content'][-500:])
        except Exception as e:
            print(f"Line {i} error: {e}")
            print(line[:200])
