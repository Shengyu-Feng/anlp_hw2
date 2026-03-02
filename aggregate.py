import json
import glob
from pathlib import Path

data = []

for file in glob.glob('processed_docs/*json'):
    chunks = json.load(open(file))
    data.extend(chunks)


out_json = Path('./chunks.json')

out_json.write_text(
    json.dumps(data, indent=2, ensure_ascii=False),
    encoding="utf-8"
)
