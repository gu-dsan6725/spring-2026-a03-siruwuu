# src/part1_router.py

def classify_query(q: str) -> str:
    q = q.lower()

    if "depend" in q:
        return "dependencies"
    if "entry" in q or "main" in q:
        return "entrypoint"
    if "language" in q or "file type" in q:
        return "repo_structure"
    if "auth" in q:
        return "auth_flow"
    if "endpoint" in q:
        return "api_endpoints"
    if "oauth" in q or "provider" in q:
        return "oauth_extension"

    return "general"