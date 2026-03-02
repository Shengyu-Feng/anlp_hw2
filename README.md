# Setup

- The folder `baseline_data/` contains the extracted baseline documents.
- The file `urls.txt` lists additional URLs for web crawling. Each URL is annotated with a manually specified crawling depth.

---

# Web Crawling

To crawl additional web data:

```bash
python crawl.py
```

This script reads from `urls.txt`, crawls the specified URLs up to the annotated depth, and stores the raw crawled content.

---

# Data Cleaning and Chunking

To clean and process the documents:

```bash
python process.py baseline_data processed_docs
python process.py crawled_raw processed_docs
python aggregate.py
```

- `process.py` cleans raw documents and splits them into structured chunks.
- The first command processes the baseline data.
- The second command processes the crawled data.
- `aggregate.py` merges all processed documents into a unified knowledge base.

---

# Retrieval

Before running retrieval, specify:
- The embedding model (default: `all-MiniLM-L6-v2`)
- The number of retrieved documents (default: 10)

Then run:

```bash
python retrieve.py
```

---

# RAG

First, start the Ollama server:

```bash
ollama serve
```

Then run the RAG pipeline:

```bash
python query.py
```