import json

CHUNKS_PATH = "chunks.json"

_chunks = json.load(open(CHUNKS_PATH))
_corpus = [item['content'] for item in _chunks]

retrieved = json.load(open('t5_retrieved.json'))


print("\n\n".join([' ' + _corpus[i] for i in retrieved['130']['dense']]))