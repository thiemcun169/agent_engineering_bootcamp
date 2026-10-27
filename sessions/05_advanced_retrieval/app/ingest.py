"""Turn the PDFs in data/pdfs/ into chunks for Qdrant: page routing (text layer or OCR), table-aware chunking.

    uv run app/ingest.py            # parse every PDF (OCR from the cache), rebuild the Qdrant collection
    uv run app/ingest.py --no-cache # OCR the scanned pages again with the session MODEL (costs about $0.01)

The notebook 02_qdrant_documents_agent.ipynb calls the same functions step by step.
"""
import base64
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import pymupdf
from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))  # so `import kb` works with `uv run app/ingest.py` and from the notebooks
SESSION_DIR = APP_DIR.parent
PDF_DIR = SESSION_DIR / "data" / "pdfs"
OCR_DIR = SESSION_DIR / "data" / "ocr"  # cached OCR markdown, one file per scanned page (shipped with the lab)
load_dotenv(SESSION_DIR / ".env")
pymupdf.no_recommend_layout()  # PyMuPDF prints a hint about an optional package otherwise
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Doc:
    file: str
    title: str
    source_url: str
    effective_date: str  # RFC 3339, the date the document takes effect
    access_group: str    # who may read it: "public" or a team such as "finance"


DOCS = {
    "qd2699": Doc("qd2699_bct_2024.pdf", "Quyết định 2699/QĐ-BCT (2024) về giá bán điện",
                  "https://moit.gov.vn/upload/2005517/20241014/2024-10-11_QD2699-QD-BCT_quy_dinh_ve_gia_dien_a5f1d.pdf",
                  "2024-10-11T00:00:00Z", "public"),
    "qd1279": Doc("qd1279_bct_2025.pdf", "Quyết định 1279/QĐ-BCT (2025) về giá bán điện",
                  "https://evn.com.vn/userfile/User/tcdl/files/2025/5/QD1279-QD-BCT-20250509163514982.pdf",
                  "2025-05-10T00:00:00Z", "public"),
    "qd14_2025": Doc("qd14_2025_ttg.pdf", "Quyết định 14/2025/QĐ-TTg về cơ cấu biểu giá bán lẻ điện",
                     "https://congbaocdn.chinhphu.vn/CongBaoCP/VanBan/2025/5/44975/56495-1-2025741-74214-2025-qd-ttg.pdf",
                     "2025-05-29T00:00:00Z", "public"),
    "minhan_2026": Doc("minhan_du_toan_dien_2026.pdf", "Gốm Minh An – Dự toán chi phí điện năm 2026 (nội bộ)",
                       "internal://finance/minhan_du_toan_dien_2026.pdf", "2025-12-15T00:00:00Z", "finance"),
}

# ── 1. Pages: text layer or OCR ──────────────────────────────────────────────
MIN_TEXT_CHARS = 50  # fewer characters than this on a page = a scan (the text layer is empty or almost empty)
# Lines that are not content: page numbers, the running header of the Official Gazette, the digital-signature stamp.
NOISE = re.compile(r"^(\d{1,3}|CÔNG BÁO/.*|Người ký:.*|Email:.*|Cơ quan:.*|Thời gian ký:.*)$")
OCR_PROMPT = ("Convert this page of a Vietnamese document to GitHub-flavoured Markdown. Keep every Vietnamese word, "
              "diacritic and number exactly as printed. Write tables as Markdown tables with their header row; do not "
              "merge or drop rows. Ignore stamps, signatures and watermarks. Return only the Markdown.")


def has_text_layer(page: pymupdf.Page) -> bool:
    return len(page.get_text().strip()) >= MIN_TEXT_CHARS


def digital_page_markdown(page: pymupdf.Page) -> str:
    """Text blocks outside tables, plus each table as Markdown at its place on the page.
    get_text() alone would return the table cells as loose lines (and twice, with the table)."""
    tables = page.find_tables().tables
    items = [(t.bbox[1], t.to_markdown().replace("<br>", " ").strip()) for t in tables]
    for x0, y0, x1, y1, text, *_ in page.get_text("blocks", sort=True):
        if any(pymupdf.Rect(x0, y0, x1, y1).intersects(t.bbox) for t in tables):
            continue
        for line in text.splitlines():
            line = " ".join(line.split())
            if line and not NOISE.match(line):
                items.append((y0, line))
    return "\n".join(text for _, text in sorted(items, key=lambda item: item[0]))


def page_png(page: pymupdf.Page, dpi: int = 150) -> bytes:
    return page.get_pixmap(dpi=dpi).tobytes("png")


def ocr_images(images: list[bytes], model=None) -> list[str]:
    """OCR page images with the session vision model, several pages at a time (model.batch runs them concurrently)."""
    from langchain.chat_models import init_chat_model

    model = model or init_chat_model(os.environ["MODEL"], reasoning_effort="low")  # low effort: transcription, not reasoning
    messages = [[{"role": "user", "content": [
        {"type": "text", "text": OCR_PROMPT},
        # OpenAI image block with detail="high": small table digits need the full-resolution tiles
        {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(png).decode(),
                                            "detail": "high"}}]}] for png in images]
    replies = model.batch(messages, config={"max_concurrency": 6})
    return [re.sub(r"^```(?:markdown)?\n|\n```$", "", r.text.strip()) for r in replies]


def load_pages(doc_id: str, use_cache: bool = True) -> list[tuple[int, str]]:
    """[(page number, markdown)] for one PDF. Digital pages are parsed with PyMuPDF; scanned pages come from
    data/ocr/<doc>_p<N>.md, or are OCR'd (all missing pages in one concurrent batch) and written to that cache."""
    pages, to_ocr = {}, []
    with pymupdf.open(PDF_DIR / DOCS[doc_id].file) as pdf:
        for page in pdf:
            n, cache = page.number + 1, OCR_DIR / f"{doc_id}_p{page.number + 1}.md"
            if has_text_layer(page):
                pages[n] = digital_page_markdown(page)
            elif use_cache and cache.exists():  # an existing file is a hit, also when the page is blank
                pages[n] = cache.read_text(encoding="utf-8")
            else:
                to_ocr.append((n, page_png(page)))
    if to_ocr:
        logger.info("OCR %s: %d scanned pages with the session model", doc_id, len(to_ocr))
        OCR_DIR.mkdir(parents=True, exist_ok=True)
        for (n, _), markdown in zip(to_ocr, ocr_images([png for _, png in to_ocr])):
            (OCR_DIR / f"{doc_id}_p{n}.md").write_text(markdown + "\n", encoding="utf-8")
            pages[n] = markdown
    return sorted(pages.items())


# ── 2. Table-aware chunking ──────────────────────────────────────────────────
HEADING = re.compile(r"^\**(Điều \d+|[IVX]+\.\s|Phụ lục\**$|Nơi nhận)")  # an article, a roman-numbered part, the appendix
ROW_ID = re.compile(r"\d+(\.\d+)*")  # TT column of the price tables: 1, 1.1, 6.1.1, 6.1.1.1 …
MAX_TABLE_LEVEL = 2  # a new chunk starts at TT levels 1, 1.1 and 1.1.1; deeper rows stay inside their parent


def cells(line: str) -> list[str]:
    line = line.strip()
    line = line[1:-1] if line.endswith("|") else line[1:]  # one outer pipe each side: "||a) …|84%|" has an empty TT cell
    return [c.strip().strip("*").strip() for c in line.split("|")]


def chunk_pages(doc_id: str, pages: list[tuple[int, str]]) -> list[dict]:
    """Section-based chunks.
    - Prose is split by article (Điều N) or part heading; the distribution list (Nơi nhận) is dropped.
    - Tables: one chunk per table section (TT 1, 1.1, 6.1.1), kept whole even when it continues on the next page,
      with the table header row repeated and a breadcrumb line `Mục: 4 Giá bán lẻ điện cho sinh hoạt > 4.1 …`.
      The breadcrumb is taken when the chunk STARTS: taken when it is flushed, it would name the next section."""
    doc, chunks = DOCS[doc_id], []
    header, path, table, prose = None, {}, None, {"section": "Phần mở đầu", "lines": [], "pages": set()}

    def add(section, pages_, body):
        chunks.append({"doc_id": doc_id, "title": doc.title, "source_url": doc.source_url, "page": min(pages_),
                       "section": section, "effective_date": doc.effective_date, "access_group": doc.access_group,
                       "text": f"{doc.title}\nMục: {body}"})

    def flush_table():
        nonlocal table
        if table and any(any(c for c in cells(r)[2:]) for r in table["rows"]):  # skip headings without values
            crumbs = table["crumbs"] + " > " if table["crumbs"] else ""
            add(table["title"], table["pages"], f"{crumbs}{table['title']}\n\n{header}\n" + "\n".join(table["rows"]))
        table = None

    def flush_prose():
        if prose["lines"] and not prose["section"].startswith("Nơi nhận"):
            add(prose["section"], prose["pages"], prose["section"] + "\n\n" + "\n".join(prose["lines"]))

    for n, markdown in pages:
        for line in markdown.splitlines():
            line = line.strip()
            if not line or NOISE.match(line.strip("*# ")):
                continue
            if line.startswith("|"):
                c = cells(line)
                if c[0] in ("TT", "STT") or all(set(x) <= set("-: ") for x in c):  # header / separator row
                    if c[0] in ("TT", "STT") and header is None:
                        header = "| " + " | ".join(c) + " |\n|" + "---|" * len(c)
                    continue
                if header is None:  # a table without a TT column: its first row is the header
                    header = "| " + " | ".join(c) + " |\n|" + "---|" * len(c)
                    continue
                if ROW_ID.fullmatch(c[0]):
                    level = c[0].count(".")
                    path = {k: v for k, v in path.items() if k < level} | {level: f"{c[0]} {c[1]}"}
                    if level <= MAX_TABLE_LEVEL:
                        flush_table()
                        table = {"title": f"{c[0]} {c[1]}", "rows": [], "pages": set(),
                                 "crumbs": " > ".join(path[k] for k in sorted(path) if k < level)}
                row = "| " + " | ".join(c) + " |"
                if table is None:  # a small table that is not numbered stays whole inside its prose section
                    prose["lines"] += ([header] if header not in prose["lines"] else []) + [row]
                    prose["pages"].add(n)
                    continue
                table["rows"].append(row)
                table["pages"].add(n)
                continue
            flush_table()
            text = line.strip("*# ").strip()
            if HEADING.match(line.strip("# ")):
                flush_prose()
                title = re.match(r"(Điều \d+|[IVX]+\.\s[^.]*|[^.:]*)", text).group(1)  # "Điều 2", "II. Chi phí …"
                prose = {"section": title, "lines": [], "pages": set()}
            prose["lines"].append(text)
            prose["pages"].add(n)
            header = None  # the next table brings its own header row (OCR repeats it on every page)
    flush_table()
    flush_prose()
    return chunks


def load_corpus(use_cache: bool = True) -> list[dict]:
    """Chunks of every document in DOCS."""
    chunks = []
    for doc_id in DOCS:
        chunks += chunk_pages(doc_id, load_pages(doc_id, use_cache))
    return chunks


if __name__ == "__main__":
    import kb

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    for noisy in ("httpx", "httpx2"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    corpus = load_corpus(use_cache="--no-cache" not in sys.argv)
    logger.info("%d chunks from %d documents", len(corpus), len(DOCS))
    kb.create_collection()
    kb.upsert_chunks(corpus)
    logger.info("collection %s: %d points", kb.COLLECTION, kb.client().count(kb.COLLECTION).count)
    kb.client().close()
