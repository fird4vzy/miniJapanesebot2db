import json

with open('words.json', 'r', encoding='utf-8') as f:
    words = json.load(f)

for word in words:
    if 'level' not in word:
        word['level'] = 'N5' # Assign N5 to your current 150 words

with open('words.json', 'w', encoding='utf-8') as f:
    json.dump(words, f, ensure_ascii=False, indent=2)

print("Successfully tagged 150 words with Level: N5!")
