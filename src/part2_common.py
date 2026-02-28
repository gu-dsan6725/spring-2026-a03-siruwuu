# src/part2_common.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple
import re

import pandas as pd


STRUCTURED_CSV_REL = "structured/daily_sales.csv"
UNSTRUCTURED_DIR_REL = "unstructured"


@dataclass
class TextDoc:
    path: Path
    product_id: str
    text: str


def data_root(data_dir: str) -> Path:
    root = Path(data_dir)
    if not root.exists():
        raise FileNotFoundError(f"Data dir not found: {root}")
    return root


def load_sales_df(data_dir: str) -> Tuple[pd.DataFrame, Path]:
    root = data_root(data_dir)
    csv_path = root / STRUCTURED_CSV_REL
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    if "date" not in df.columns:
        raise ValueError("CSV missing required column: date")
    df["date"] = pd.to_datetime(df["date"])
    return df, csv_path


def extract_product_id_from_filename(path: Path) -> str:
    # Example: ELEC001_product_page.txt -> ELEC001
    m = re.search(r"([A-Z]{4}\d{3})", path.name)
    return m.group(1) if m else path.stem


def load_text_docs(data_dir: str) -> Tuple[List[TextDoc], List[Path]]:
    root = data_root(data_dir)
    udir = root / UNSTRUCTURED_DIR_REL
    if not udir.exists():
        raise FileNotFoundError(f"Unstructured dir not found: {udir}")

    files = sorted(udir.glob("*_product_page.txt"))
    if not files:
        raise FileNotFoundError(f"No product_page txt files found under: {udir}")

    docs: List[TextDoc] = []
    for p in files:
        txt = p.read_text(encoding="utf-8", errors="ignore")
        docs.append(TextDoc(path=p, product_id=extract_product_id_from_filename(p), text=txt))

    return docs, files


def safe_float(x) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


def safe_int(x) -> int:
    try:
        return int(x)
    except Exception:
        return 0


def month_filter(df: pd.DataFrame, year: int, month: int) -> pd.Series:
    return (df["date"].dt.year == year) & (df["date"].dt.month == month)


def keyword_score(text: str, query: str) -> int:
    t = text.lower()
    q = query.lower()
    score = 0
    for w in re.findall(r"[a-z0-9]+", q):
        if len(w) >= 3:
            score += t.count(w)
    return score


def find_best_docs(docs: List[TextDoc], query: str, k: int = 3) -> List[TextDoc]:
    scored = [(keyword_score(d.text, query), d) for d in docs]
    scored.sort(key=lambda x: x[0], reverse=True)
    best = [d for s, d in scored[:k] if s > 0]
    return best if best else [scored[0][1]]


def extract_excerpt(text: str, query: str, max_chars: int = 900) -> str:
    low = text.lower()
    q_tokens = [t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) >= 3]
    idx = -1
    for tok in q_tokens:
        idx = low.find(tok)
        if idx != -1:
            break

    if idx == -1:
        return text[:max_chars].strip()

    half = max_chars // 2
    start = max(0, idx - half)
    end = min(len(text), idx + half)
    return text[start:end].strip()


def simple_review_sentiment(text: str) -> int:
    """
    Very lightweight heuristic sentiment scoring.
    Counts positive words minus negative words.
    """
    t = text.lower()
    positives = [
        "love", "great", "excellent", "amazing", "awesome", "fantastic", "perfect",
        "easy", "comfortable", "recommend", "good", "well", "durable"
    ]
    negatives = [
        "bad", "poor", "terrible", "broken", "broke", "hard", "difficult",
        "hate", "disappoint", "issue", "problem", "return", "refund"
    ]
    score = 0
    for w in positives:
        score += t.count(w)
    for w in negatives:
        score -= t.count(w)
    return score


def summarize_sales_for_product(df: pd.DataFrame, product_id: str, region: str | None = None) -> Dict[str, float]:
    sub = df[df["product_id"] == product_id]
    if region:
        sub = sub[sub["region"] == region]
    return {
        "units_sold": safe_int(sub["units_sold"].sum()) if "units_sold" in sub.columns else 0,
        "total_revenue": safe_float(sub["total_revenue"].sum()) if "total_revenue" in sub.columns else float("nan"),
    }