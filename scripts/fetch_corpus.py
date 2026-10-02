"""Download the GOV.UK pages in data/sources.txt into data/raw/<slug>.md: python scripts/fetch_corpus.py"""
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "sources.txt"
RAW = ROOT / "data" / "raw"
DROP = ("nav, aside, script, style, .gem-c-contents-list, .govuk-pagination, .gem-c-print-link, "
        ".gem-c-related-navigation, .gem-c-step-nav, .gem-c-step-nav-header, .gem-c-step-nav-related, "
        ".gem-c-button")


def slug(url: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", url.split("gov.uk/")[-1].lower()).strip("-")


def extract(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup
    # a guide part has two h1s, the guide then the part; GOV.UK's own <title> joins them the same way
    title = ": ".join(h.get_text(" ", strip=True) for h in main.find_all("h1"))
    for tag in main.select(DROP):
        tag.decompose()
    lines, h2 = [], ""
    for el in main.find_all(["h2", "h3", "p", "li", "table"]):
        if el.find_parent(["li", "table"]):   # nested text is handled by its parent
            continue
        if el.name == "table":                # key figures often live in tables
            rows = [[c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])] for tr in el.find_all("tr")]
            header, *body = rows
            for row in body:
                cells = "; ".join(f"{h} {v}".strip() for h, v in zip(header[1:], row[1:]))
                lines.append(f"- {row[0]}: {cells}")
            continue
        text = el.get_text(" ", strip=True)
        if not text:
            continue
        if el.name == "h2":
            h2 = text
            lines.append(f"\n## {text}")
        elif el.name == "h3":                 # keep the parent: "Defined benefit pension schemes > What you’ll get"
            lines.append(f"\n## {h2} > {text}" if h2 else f"\n## {text}")
        elif el.name == "li":
            lines.append(f"- {text}")
        else:
            lines.append(text)
    return title, "\n".join(lines).strip()


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for url in SOURCES.read_text().split():
        r = requests.get(url, timeout=30, headers={"User-Agent": "pensionqa-evals (portfolio project)"})
        r.raise_for_status()                  # never save an error page as guidance
        # GOV.UK redirects unknown guide parts (even made-up ones) and serves some pages at two URLs,
        # always with a 200, so check the page's canonical link says this is the page we asked for
        link = BeautifulSoup(r.text, "html.parser").find("link", rel="canonical")
        canonical = link["href"] if link else None
        if canonical != url:
            raise SystemExit(f"{url} is a copy of {canonical}: list that URL in data/sources.txt instead")
        title, body = extract(r.text)
        (RAW / f"{slug(url)}.md").write_text(f"# {title}\nSource: {url}\n\n{body}\n", encoding="utf-8")
        print(f"saved {slug(url)} ({len(body.split())} words)")
        time.sleep(1)  # be polite to GOV.UK


if __name__ == "__main__":
    main()
