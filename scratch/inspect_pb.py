import os

pb_path = 'C:/Users/Manib/.gemini/antigravity/conversations/9de23203-df1d-40f5-8dc4-b9fd626b9800.pb'

if not os.path.exists(pb_path):
    print("PB path does not exist")
else:
    with open(pb_path, 'rb') as f:
        data = f.read(500)
        print("First 500 bytes of PB file:")
        print(data)
        print("Is it printable ASCII?")
        try:
            print(data.decode('utf-8'))
        except Exception as e:
            print("Cannot decode as utf-8:", e)
