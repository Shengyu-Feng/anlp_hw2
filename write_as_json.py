import json

# Input and output paths
txt_path = "test_set_day_4.txt"
json_path = "questions.json"

data = []

with open(txt_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines, start=1):
    question = line.strip()
    if question:  # skip empty lines
        data.append({
            "question": question,
            "id": str(idx)
        })

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print(f"Saved {len(data)} questions to {json_path}")