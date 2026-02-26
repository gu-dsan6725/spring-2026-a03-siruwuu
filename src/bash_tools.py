import subprocess
from pathlib import Path
from typing import Optional, List


def run(cmd: str, cwd: str) -> str:
    """
    Execute a bash command inside repo and return stdout.
    """
    p = subprocess.run(cmd, shell=True, cwd=cwd, text=True, capture_output=True)
    if p.returncode != 0:
        return (p.stdout or "") + (p.stderr or "")
    return p.stdout


# ---------- basic file tools ----------
def list_tree(repo_dir: str, depth: int = 2) -> str:
    return run(f"tree -L {depth}", repo_dir)


def find_files(pattern: str, repo_dir: str) -> str:
    return run(f"find . -name '{pattern}'", repo_dir)


def read_file(path: str, repo_dir: str) -> str:
    return run(f"cat {path}", repo_dir)


# ---------- search tools ----------
def search_code(pattern: str, repo_dir: str, file_glob: Optional[str] = None) -> str:
    """
    rg search across repo.
    """
    if file_glob:
        cmd = f"rg -n -g '{file_glob}' \"{pattern}\" ."
    else:
        cmd = f"rg -n \"{pattern}\" ."
    return run(cmd, repo_dir)


def search_auth(repo_dir: str) -> str:
    """
    Common auth-related search bundle
    """
    patterns = [
        "OAuth",
        "token",
        "jwt",
        "Security(",
        "Depends(",
        "scope",
        "role",
        "permission",
    ]
    out = []
    for p in patterns:
        out.append(search_code(p, repo_dir))
    return "\n".join(out)


def search_endpoints(repo_dir: str) -> str:
    """
    Extract FastAPI endpoints
    """
    return search_code(r"@router\.(get|post|put|delete|patch)", repo_dir, "*.py")