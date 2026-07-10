import os

log_path = 'C:/Users/Manib/.gemini/antigravity/brain/0e5f3117-b5c2-4de8-a914-1588d19721bc/.system_generated/logs/overview.txt'

if not os.path.exists(log_path):
    print("Log path does not exist:", log_path)
else:
    with open(log_path, 'r', encoding='utf-8') as f:
        content = f.read()
    print("Total length:", len(content))
    print("Beginning:")
    print(content[:2000])
    print("\n...\nEnding:")
    print(content[-3000:])
