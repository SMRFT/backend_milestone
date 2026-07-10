import os

pb_path = 'C:/Users/Manib/.gemini/antigravity/conversations/9de23203-df1d-40f5-8dc4-b9fd626b9800.pb'

if not os.path.exists(pb_path):
    print("PB path does not exist")
else:
    with open(pb_path, 'rb') as f:
        data = f.read()
    
    # Search for the start of the domains list
    target = b'[{"id": "69e05b0c4ae1ff103aa98124"'
    idx = data.find(target)
    if idx == -1:
        # try without space or different quotes
        target = b'[{"id":"69e05b0c4ae1ff103aa98124"'
        idx = data.find(target)
        
    if idx == -1:
        print("Target string not found in PB file")
        # Let's search for some other known goal IDs or domains from the prompt
        for sub in [b'69e05b0c4ae1ff103aa98124', b'AT001', b'Social Skills']:
            pos = data.find(sub)
            print(f"Sub {sub}: found at {pos}")
    else:
        print(f"Target found at index {idx}")
        # Let's extract 200,000 bytes from idx
        extracted = data[idx:idx+250000]
        # Find where it ends. It's inside a protobuf string field. It might contain some binary markers at the end.
        # But we can try to decode as utf-8 (ignoring errors) and find the end of the text.
        text = extracted.decode('utf-8', errors='ignore')
        
        # Let's save the extracted text to a scratch file
        out_path = 'd:/All projects/SMRFT/milestone/backend_milestone/scratch/extracted_prompt.txt'
        with open(out_path, 'w', encoding='utf-8') as out_f:
            out_f.write(text)
        print("Successfully extracted text and wrote to", out_path)
        print("Length of extracted text:", len(text))
        print("Ending of extracted text (last 1000 chars):")
        print(text[-1000:])
