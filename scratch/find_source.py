import os

root_dir = 'C:/Users/Manib/.gemini/antigravity'
target = '69e05b0c4ae1ff103aa98124'

print(f"Searching for '{target}' under '{root_dir}'...")

found = []
for dirpath, dirnames, filenames in os.walk(root_dir):
    # Skip browser recordings to save time
    if 'browser_recordings' in dirpath:
        continue
    for filename in filenames:
        filepath = os.path.join(dirpath, filename)
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
                if bytes(target, 'utf-8') in content:
                    found.append(filepath)
                    print(f"Found in: {filepath} (size: {len(content)} bytes)")
        except Exception as e:
            # print(f"Error reading {filepath}: {e}")
            pass

print("Search completed. Found in:", found)
