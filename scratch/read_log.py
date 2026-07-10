import json
import os

log_path = 'C:/Users/Manib/.gemini/antigravity/brain/9de23203-df1d-40f5-8dc4-b9fd626b9800/.system_generated/logs/overview.txt'

if not os.path.exists(log_path):
    print("Log path does not exist:", log_path)
else:
    with open(log_path, encoding='utf-8') as f:
        content = f.read()
        print("Total length of overview.txt:", len(content))
        # Print the first 1000 characters and last 2000 characters
        print("First 1000:")
        print(content[:1000])
        print("\n...\nLast 2000:")
        print(content[-2000:])
