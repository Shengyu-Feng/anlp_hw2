# Setup

The folder `baseline_data` contains the extracted files from the baseline data. The file  `urls.txt` contains the additional urls to crawl the data from, along with the depth label mannully annotated.

# Crawl the data

```
python crawl.py
```

# Data cleaning and chunking

```
python process.py baseline_data processed_docs
python process.py crawled_raw processed_docs
python aggregate.py
```

# Retrieval

Specify the embedding model (default: all-MiniLM-L6-v2) and the number of retrieved documents (default: 10) inside, and run

```
python retrieve.py
```

# RAG

First serve the Ollama model via

```
ollama serve
```

Then run the RAG model via

```
python query.py
```