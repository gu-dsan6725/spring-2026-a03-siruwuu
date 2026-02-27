# src/part1_router.py

def classify_query(q: str) -> str:
    q = q.lower()

    if "dependenc" in q or "requirements" in q or "pyproject" in q:
        return "q1"

    if "entry point" in q or ("main" in q and "file" in q):
        return "q2"

    if "programming language" in q or "file type" in q or "file types" in q:
        return "q3"

    if "authentication flow" in q or ("authentication" in q and "authorization" in q) or "token validation" in q:
        return "q4"

    if "api endpoints" in q or "endpoints" in q or "scopes" in q:
        return "q5"

    if "oauth provider" in q or "okta" in q or ("oauth" in q and "provider" in q):
        return "q6"

    return "unknown"