import json
import numpy as np
import faiss
import bm25s
import Stemmer
from sentence_transformers import SentenceTransformer


# ── Config ────────────────────────────────────────────────────────────────────

CHUNKS_PATH = "chunks.json"
QUERIES_PATH = "questions.json"
MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 8


# ── Corpus ────────────────────────────────────────────────────────────────────

_chunks = json.load(open(CHUNKS_PATH))
_corpus = [item['content'] for item in _chunks]


# ── Dense (FAISS) ─────────────────────────────────────────────────────────────

_encoder = SentenceTransformer(MODEL_NAME)
_embeddings = _encoder.encode(_corpus, show_progress_bar=True)

faiss.normalize_L2(_embeddings)
_dense_index = faiss.IndexFlatIP(_embeddings.shape[1])
_dense_index.add(_embeddings)


def dense_retrieve(query: str, k: int = TOP_K) -> list[str]:
    query_embedding = _encoder.encode([query])
    faiss.normalize_L2(query_embedding)
    _, indices = _dense_index.search(query_embedding, k)
    return indices[0].tolist()


# ── Sparse (BM25) ─────────────────────────────────────────────────────────────

_stemmer = Stemmer.Stemmer("english")
_corpus_tokens = bm25s.tokenize(_corpus, stopwords="en", stemmer=_stemmer)
_sparse_index = bm25s.BM25()
_sparse_index.index(_corpus_tokens)


def sparse_retrieve(query: str, k: int = TOP_K) -> list[str]:
    query_tokens = bm25s.tokenize(query, stopwords="en", stemmer=_stemmer)
    results, _ = _sparse_index.retrieve(query_tokens, k=k)
    return results[0].tolist()


# ── Combined ──────────────────────────────────────────────────────────────────

def retrieve(query: str, k: int = TOP_K) -> list[str]:
    """Merge dense and sparse results, deduplicated, dense-first."""
    seen = set()
    combined = []
    for doc in dense_retrieve(query, k) + sparse_retrieve(query, k):
        if doc not in seen:
            seen.add(doc)
            combined.append(doc)
    return combined[:k]


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    queries = json.load(open(QUERIES_PATH))
    results = {}

    for q in queries:
        query = q['question']
        dense_indices = dense_retrieve(query, TOP_K)
        sparse_indices = sparse_retrieve(query, 10-TOP_K)

        results[q['id']] = {
            "dense": dense_indices,
            "sparse": sparse_indices,
        }

    json.dump(results, open("question_retrieved.json", "w"), indent=2)