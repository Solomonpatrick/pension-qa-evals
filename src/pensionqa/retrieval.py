"""BM25 keyword retrieval with alias normalisation: python -m pensionqa.retrieval "question" """
import re
import sys

from rank_bm25 import BM25Okapi

from pensionqa.corpus import load_chunks

# Different words people use for the same thing ("entity resolution" at small scale).
ALIASES = {
    "final salary": "defined benefit",
    "career average": "defined benefit",
    "money purchase": "defined contribution",
    "db": "defined benefit",
    "dc": "defined contribution",
    "auto-enrolment": "automatic enrolment",
    "auto enrolment": "automatic enrolment",
    "workplace scheme": "workplace pension",
    "ni": "national insurance",
}
STOPWORDS = set("a an and are as at be by can do does for from how i if in is it my of on or the to what when which who will with you your".split())


def normalise(text: str) -> str:
    text = text.lower()
    for alias, canonical in ALIASES.items():
        text = re.sub(rf"\b{re.escape(alias)}\b", canonical, text)
    return text


def tokenize(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9£%]+", normalise(text)) if w not in STOPWORDS]


class Retriever:
    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        self.bm25 = BM25Okapi([tokenize(f"{c['title']} {c['section']} {c['text']}") for c in chunks])

    def search(self, query: str, k: int = 5) -> list[dict]:
        scores = self.bm25.get_scores(tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [{**self.chunks[i], "score": round(float(scores[i]), 3)} for i in ranked if scores[i] > 0]


def load_retriever() -> Retriever:
    return Retriever(load_chunks())


if __name__ == "__main__":
    for hit in load_retriever().search(" ".join(sys.argv[1:]), k=3):
        print(f"{hit['score']:>7}  {hit['chunk_id']}  ({hit['section']})")
