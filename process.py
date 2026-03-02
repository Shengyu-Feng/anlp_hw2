import re
import json
from pathlib import Path
from dataclasses import dataclass, field
from bs4 import BeautifulSoup
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter, BM25ContentFilter

# ── Data model ────────────────────────────────────────────────────────────────

_generator = DefaultMarkdownGenerator(
    options={
        "ignore_links": True,
        "ignore_images": True,       # remove image tags
        "body_width": 0,             # no line wrapping
    }
)

_content_filter = PruningContentFilter(
    threshold=0.45,           # higher = more aggressive pruning
    threshold_type="dynamic",   # or "dynamic"
    #min_word_threshold=5,    # drop blocks with fewer than 20 words
)

@dataclass
class Chunk:
    id: int
    title: str
    content: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self):
        return {"id": self.id, "title": self.title,
                "content": self.content, "metadata": self.metadata}


# ── Markdown generation ───────────────────────────────────────────────────────
def preprocess_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    
    # Remove all tables (infobox, navbox, header tabs etc.)
    for table in soup.find_all("table"):
        table.decompose()
    return str(soup)


def html_to_fit_markdown(html: str) -> str:
    #html = preprocess_html(html)   # ← preprocess first
    result = _generator.generate_markdown(
        input_html=html,
        base_url="",
        content_filter=_content_filter,
    )
    return result.fit_markdown


REMOVE_SECTION_TITLES = re.compile(
    r'^(References|External links|Further reading|See also|Notes|'
    r'Bibliography|Sources|Citations|Footnotes|Works cited|'
    r'Legacy|Honors|Awards|Accolades)$',
    re.IGNORECASE
)


# ── Text cleaning ─────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    text = re.sub(r'\[\s*\d+\s*\]', '', text)
    text = re.sub(r'\[\s*note\s*\w+\s*\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[\s*[a-z]\s*\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'/[^/\n]{1,60}/', '', text)
    text = re.sub(r'[ˈˌːɑɒæɛɪɔʊəɜɐʌɑɒʃʒðθŋɡɹɾʔ]+', '', text)
    text = re.sub(r'\s+([.,;:!?)\]])', r'\1', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    lines = [l for l in text.splitlines() if len(l.strip()) > 1]
    return "\n".join(lines).strip()


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_markdown_text(text: str, source: str) -> list[Chunk]:
    chunks = []
    chunk_id = 0
    current_heading = None
    current_lines = []
    skip = False

    def flush():
        nonlocal chunk_id
        if skip:
            return
        content = clean_text("\n".join(current_lines))
        if len(content.strip()) < 30:
            return
        chunks.append(Chunk(
            id=chunk_id,
            title=current_heading or "",
            content=content,
            metadata={"source": source, "heading": current_heading}
        ))
        chunk_id += 1

    for line in text.splitlines():
        if re.match(r'^#{1,4}\s+', line):
            flush()
            current_lines = []
            current_heading = re.sub(r'^#{1,4}\s+', '', line).strip()
            skip = bool(REMOVE_SECTION_TITLES.match(current_heading))
        else:
            current_lines.append(line)


    flush()
    return chunks


# ── HTM processing ────────────────────────────────────────────────────────────

def process_htm_file(htm_file: Path, output_dir: Path):
    html = htm_file.read_text(encoding="utf-8", errors="replace")
    markdown = html_to_fit_markdown(html)
    chunks = chunk_markdown_text(markdown, source=htm_file.name)
    if chunks:
        save_chunks(chunks, htm_file, output_dir)


# ── MD processing ─────────────────────────────────────────────────────────────

def process_md_file(md_file: Path, output_dir: Path):
    text = md_file.read_text(encoding="utf-8", errors="replace")
    chunks = chunk_markdown_text(text, source=md_file.name)
    if chunks:
        save_chunks(chunks, md_file, output_dir)


# ── PDF processing ────────────────────────────────────────────────────────────

def process_pdf(pdf_file: Path, output_dir: Path):
    try:
        from pypdf import PdfReader
    except ImportError:
        print("    ! pip install pypdf")
        return

    reader = PdfReader(str(pdf_file))
    chunks = []

    outline = reader.outline
    if outline:
        print(f"    → chunking by TOC")

        def flatten_outline(items, level=0):
            flat = []
            for item in items:
                if isinstance(item, list):
                    flat.extend(flatten_outline(item, level + 1))
                else:
                    try:
                        page_num = reader.get_destination_page_number(item)
                        flat.append((level, item.title, page_num))
                    except Exception:
                        pass
            return flat

        toc = flatten_outline(outline)
        for i, (level, title, start_page) in enumerate(toc):
            end_page = toc[i + 1][2] if i + 1 < len(toc) else len(reader.pages)
            text = "".join(reader.pages[p].extract_text() or '' for p in range(start_page, end_page))
            text = clean_text(text)
            if len(text.strip()) < 30:
                continue
            chunks.append(Chunk(
                id=i, title=title, content=text,
                metadata={"source": pdf_file.name, "level": level,
                          "start_page": start_page + 1, "end_page": end_page}
            ))

    if not chunks:
        print(f"    → no TOC, falling back to page-by-page")
        for i, page in enumerate(reader.pages):
            text = clean_text(page.extract_text() or '')
            if len(text.strip()) < 30:
                continue
            chunks.append(Chunk(
                id=i, title=f"Page {i + 1}", content=text,
                metadata={"source": pdf_file.name, "page": i + 1}
            ))

    if chunks:
        save_chunks(chunks, pdf_file, output_dir)


# ── Save ──────────────────────────────────────────────────────────────────────

def save_chunks(chunks: list[Chunk], source_file: Path, output_dir: Path):
    stem = source_file.stem

    out_json = output_dir / (stem + "_chunks.json")
    out_json.write_text(
        json.dumps([c.to_dict() for c in chunks], indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    out_txt = output_dir / (stem + "_chunks.txt")
    lines = []
    for c in chunks:
        lines.append("=" * 60)
        lines.append(f"[{c.id}] {c.title}" if c.title else f"[{c.id}]")
        lines.append("=" * 60)
        lines.append(c.content)
        lines.append("")
    out_txt.write_text("\n".join(lines), encoding="utf-8")

    print(f"    → {len(chunks)} chunks → {out_json.name} + {out_txt.name}")


# ── Main ──────────────────────────────────────────────────────────────────────

def process_directory(input_dir: str, output_dir: str = None):
    input_path = Path(input_dir)
    output_path = Path(output_dir) if output_dir else input_path / "chunks"
    output_path.mkdir(parents=True, exist_ok=True)

    htm_files = list(input_path.glob("*.htm")) + list(input_path.glob("*.html"))
    md_files = list(input_path.glob("*.md"))
    pdf_files = list(input_path.glob("*.pdf"))

    print(f"Found {len(htm_files)} HTM + {len(md_files)} MD + {len(pdf_files)} PDF\n")

    for f in htm_files:
        #print(f"Processing HTM: {f.name}")
        #try:
        process_htm_file(f, output_path)
        #except Exception as e:
        #    print(f"  ✗ {e}")

    for f in md_files:
        print(f"Processing MD: {f.name}")
        try:
            process_md_file(f, output_path)
        except Exception as e:
            print(f"  ✗ {e}")

    for f in pdf_files:
        print(f"Processing PDF: {f.name}")
        try:
            process_pdf(f, output_path)
        except Exception as e:
            print(f"  ✗ {e}")

    print(f"\nDone → {output_path}/")


if __name__ == "__main__":
    import sys
    process_directory(
        sys.argv[1] if len(sys.argv) > 1 else "crawled_raw",
        sys.argv[2] if len(sys.argv) > 2 else None
    )