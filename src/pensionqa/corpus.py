"""Split the raw GOV.UK pages into section-aware chunks: python -m pensionqa.corpus"""
import json
from pathlib import Path

from pensionqa.config import CHUNKS_FILE, RAW_DIR

MAX_WORDS = 180


def parse_raw(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    return {
        "doc_id": path.stem,
        "title": lines[0].removeprefix("# ").strip(),
        "url": lines[1].removeprefix("Source: ").strip(),
        "body": "\n".join(lines[2:]),
    }


def chunk_document(doc: dict, max_words: int = MAX_WORDS) -> list[dict]:
    chunks, section, buf = [], "Overview", []

    def flush():
        if buf:
            chunks.append({
                "chunk_id": f"{doc['doc_id']}#{len(chunks)}",
                "doc_id": doc["doc_id"],
                "title": doc["title"],
                "url": doc["url"],
                "section": section,
                "text": "\n".join(buf),
            })
            buf.clear()

    for line in doc["body"].splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("## "):
            flush()
            section = line[3:]
            continue
        if len(" ".join(buf).split()) + len(line.split()) > max_words:
            flush()
        buf.append(line)
    flush()
    return chunks


def build() -> list[dict]:
    chunks = [c for p in sorted(RAW_DIR.glob("*.md")) for c in chunk_document(parse_raw(p))]
    with CHUNKS_FILE.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    return chunks


def load_chunks() -> list[dict]:
    return [json.loads(line) for line in CHUNKS_FILE.read_text(encoding="utf-8").splitlines()]


if __name__ == "__main__":
    print(f"wrote {len(build())} chunks to {CHUNKS_FILE}")
