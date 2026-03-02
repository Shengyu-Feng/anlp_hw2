import asyncio
import httpx
import re
from pathlib import Path
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator


def parse_url_file(path: str) -> list[tuple[str, int]]:
    entries = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.rsplit(None, 1)
        if len(parts) == 2 and parts[1].isdigit():
            entries.append((parts[0], int(parts[1])))
        else:
            entries.append((parts[0], 0))
    return entries


def url_to_filename(url: str) -> str:
    name = re.sub(r'^https?://', '', url)
    name = re.sub(r'[^\w\-]', '_', name)
    return name[:120]


def is_pdf_url(url: str) -> bool:
    return url.lower().endswith(".pdf") or "/pdf/" in url.lower()


async def crawl_one(crawler: AsyncWebCrawler, url: str, depth: int, output_dir: Path):
    print(f"  crawling depth={depth}: {url}")

    if url.lower().endswith(".pdf"):
        async with httpx.AsyncClient(follow_redirects=True) as client:
            r = await client.get(url)
            out_file = output_dir / (url_to_filename(url) + ".pdf")
            out_file.write_bytes(r.content)
            print(f"    → PDF: {out_file.name}")
        return

    if depth == 0:
        results = await crawler.arun(url=url, config=CrawlerRunConfig(
            excluded_tags=["form", "header", "footer", "script", "link", "source", "img", "a"],
            exclude_external_links=True,
            exclude_social_media_links=True,
            keep_data_attributes=False,
        ))
        results = [results] if not isinstance(results, list) else results
    else:
        config = CrawlerRunConfig(
            deep_crawl_strategy=BFSDeepCrawlStrategy(max_depth=depth, max_pages=50),
            excluded_tags=["header", "footer", "img"],
            exclude_external_links=True,
            exclude_social_media_links=True,
            keep_data_attributes=False,
        )
        results = await crawler.arun(url=url, config=config, follow_links=True, same_domain_only=True)
        if not isinstance(results, list):
            results = [results]

    saved = 0
    for r in results:
        page_url = getattr(r, 'url', url)
        stem = url_to_filename(page_url)

        # ── HTML: save raw html ───────────────────────────────────────────
        html = r.cleaned_html
        if html.strip():
            out_file = output_dir / (stem + ".htm")
            out_file.write_text(html, encoding="utf-8")
            print(f"    → HTM: {out_file.name}")
            saved += 1

    print(f"    → saved {saved} file(s)")


async def main():
    output_dir = Path("crawled_raw")
    output_dir.mkdir(exist_ok=True)

    entries = parse_url_file("urls.txt")
    print(f"Loaded {len(entries)} URLs\n")

    async with AsyncWebCrawler() as crawler:
        for url, depth in entries:
            try:
                await crawl_one(crawler, url, depth, output_dir)
            except Exception as e:
                print(f"  ✗ failed {url}: {e}")

    print(f"\nCrawling done → {output_dir}/")

asyncio.run(main())