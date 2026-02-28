from pathlib import Path

UNSTRUCT_DIR = Path("data/unstructured")

def load_all_product_pages() -> list[dict]:
    docs = []
    for p in sorted(UNSTRUCT_DIR.glob("*_product_page.txt")):
        docs.append({"path": str(p), "text": p.read_text(encoding="utf-8", errors="ignore")})
    return docs

def simple_keyword_search(docs: list[dict], query: str, k: int = 3) -> list[dict]:
    q = query.lower()
    scored = []
    for d in docs:
        t = d["text"].lower()
        score = 0
        for w in q.split():
            if len(w) >= 3:
                score += t.count(w)
        score += 5 if any(tok in d["path"].lower() for tok in q.split()) else 0
        scored.append((score, d))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for s, d in scored[:k] if s > 0] or [scored[0][1]]

def extract_excerpt(text: str, query: str, window: int = 500) -> str:
    q = query.lower()
    low = text.lower()
    idx = low.find(q.split()[0]) if q.split() else -1
    if idx == -1:
        return text[:window]
    start = max(0, idx - window // 2)
    end = min(len(text), idx + window // 2)
    return text[start:end]