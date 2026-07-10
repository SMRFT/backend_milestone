import json

log_path = 'C:/Users/Manib/.gemini/antigravity/brain/0e5f3117-b5c2-4de8-a914-1588d19721bc/.system_generated/logs/overview.txt'

with open(log_path, encoding='utf-8') as f:
    for i, line in enumerate(f):
        data = json.loads(line)
        content = data.get('content', '')
        if '69e05b0c4ae1ff103aa98124' in content:
            print(f"Line {i}: index={data.get('step_index')}, source={data.get('source')}, type={data.get('type')}, len={len(content)}")
            print("Snippet:")
            print(content[:500])
            print("...")
            print(content[-500:])
            print("="*40)
