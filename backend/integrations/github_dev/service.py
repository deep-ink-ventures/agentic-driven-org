"""
GitHub integration service.

Provides functions for interacting with GitHub repos, issues, PRs,
projects, and workflow dispatch. All functions are stateless — pass
the token as a parameter.
"""

import base64
import hashlib
import hmac
import logging

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://api.github.com"


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def list_repos(token: str) -> list[dict]:
    resp = requests.get(f"{BASE_URL}/user/repos", headers=_headers(token), params={"per_page": 100}, timeout=30)
    resp.raise_for_status()
    return [{"full_name": r["full_name"], "private": r["private"], "url": r["html_url"]} for r in resp.json()]


def create_issue(token: str, repo: str, title: str, body: str, labels: list[str] | None = None) -> dict:
    data = {"title": title, "body": body}
    if labels:
        data["labels"] = labels
    resp = requests.post(f"{BASE_URL}/repos/{repo}/issues", headers=_headers(token), json=data, timeout=30)
    resp.raise_for_status()
    r = resp.json()
    return {"number": r["number"], "url": r["html_url"], "id": r["id"]}


def create_pull_request(token: str, repo: str, title: str, body: str, head: str, base: str = "main") -> dict:
    data = {"title": title, "body": body, "head": head, "base": base}
    resp = requests.post(f"{BASE_URL}/repos/{repo}/pulls", headers=_headers(token), json=data, timeout=30)
    resp.raise_for_status()
    r = resp.json()
    return {"number": r["number"], "url": r["html_url"], "id": r["id"]}


def dispatch_workflow(token: str, repo: str, workflow_file: str, ref: str = "main", inputs: dict | None = None) -> dict:
    data = {"ref": ref}
    if inputs:
        data["inputs"] = inputs
    resp = requests.post(
        f"{BASE_URL}/repos/{repo}/actions/workflows/{workflow_file}/dispatches",
        headers=_headers(token),
        json=data,
        timeout=30,
    )
    resp.raise_for_status()
    return {"dispatched": True}


def get_workflow_run(token: str, repo: str, run_id: int) -> dict:
    resp = requests.get(f"{BASE_URL}/repos/{repo}/actions/runs/{run_id}", headers=_headers(token), timeout=30)
    resp.raise_for_status()
    r = resp.json()
    return {"id": r["id"], "status": r["status"], "conclusion": r.get("conclusion"), "url": r["html_url"]}


def get_workflow_logs(token: str, repo: str, run_id: int) -> str:
    resp = requests.get(
        f"{BASE_URL}/repos/{repo}/actions/runs/{run_id}/logs",
        headers=_headers(token),
        allow_redirects=True,
        timeout=30,
    )
    if resp.status_code == 200:
        return resp.text[:50000]
    return f"[Failed to fetch logs: {resp.status_code}]"


def list_workflow_runs(token: str, repo: str, workflow_file: str, per_page: int = 5) -> list[dict]:
    resp = requests.get(
        f"{BASE_URL}/repos/{repo}/actions/workflows/{workflow_file}/runs",
        headers=_headers(token),
        params={"per_page": per_page},
        timeout=30,
    )
    resp.raise_for_status()
    return [
        {
            "id": r["id"],
            "status": r["status"],
            "conclusion": r.get("conclusion"),
            "url": r["html_url"],
            "created_at": r["created_at"],
        }
        for r in resp.json()["workflow_runs"]
    ]


def create_or_update_file(token: str, repo: str, path: str, content: str, message: str) -> dict:
    # Check if file already exists to get its sha
    get_resp = requests.get(f"{BASE_URL}/repos/{repo}/contents/{path}", headers=_headers(token), timeout=30)
    data = {
        "message": message,
        "content": base64.b64encode(content.encode()).decode(),
    }
    if get_resp.status_code == 200:
        data["sha"] = get_resp.json()["sha"]
    resp = requests.put(f"{BASE_URL}/repos/{repo}/contents/{path}", headers=_headers(token), json=data, timeout=30)
    resp.raise_for_status()
    return {"sha": resp.json()["content"]["sha"]}


def get_pr(token: str, repo: str, pr_number: int) -> dict:
    resp = requests.get(f"{BASE_URL}/repos/{repo}/pulls/{pr_number}", headers=_headers(token), timeout=30)
    resp.raise_for_status()
    r = resp.json()
    return {"number": r["number"], "state": r["state"], "merged": r.get("merged", False), "url": r["html_url"]}


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    if not signature or not signature.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
