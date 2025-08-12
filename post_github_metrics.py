# coding: utf-8
"""
Post-processing script: extract GitHub repo links from latest TXT output and push
Stars/Watchers/Forks metrics to WeWork (and optional PushPlus).

Env:
  - WEWORK_WEBHOOK_URL (required for WeWork push)
  - PUSHPLUS_TOKEN (optional)
  - GITHUB_TOKEN (optional, increases GitHub API rate limits)
"""
import os
import re
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict, Optional

import requests

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "TrendRadar-GitHub-Metrics",
}


def beijing_now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def find_latest_txt_file() -> Optional[Path]:
    out_dir = Path("output")
    if not out_dir.exists():
        return None
    # find latest date folder by mtime
    date_dirs = [p for p in out_dir.iterdir() if p.is_dir()]
    if not date_dirs:
        return None
    date_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    txt_dir = date_dirs[0] / "txt"
    if not txt_dir.exists():
        return None
    txt_files = [p for p in txt_dir.iterdir() if p.suffix == ".txt"]
    if not txt_files:
        return None
    txt_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return txt_files[0]


def parse_github_repos_from_txt(file_path: Path) -> List[Tuple[str, str, str]]:
    """Return list of (owner, repo, url)."""
    pattern = re.compile(r"https?://github\.com/([^/]+)/([^/\]#?\s]+)")
    repos: List[Tuple[str, str, str]] = []
    seen: set = set()
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            for m in pattern.finditer(line):
                owner = m.group(1)
                repo = m.group(2)
                # trim trailing tokens like ) or ] if any residue
                repo = repo.rstrip(').,;]')
                if repo.endswith('.git'):
                    repo = repo[:-4]
                key = (owner, repo)
                if key in seen:
                    continue
                seen.add(key)
                repos.append((owner, repo, f"https://github.com/{owner}/{repo}"))
    return repos


def abbr(n: Optional[int]) -> str:
    if n is None:
        return "-"
    try:
        if n < 1000:
            return str(n)
        if n < 1_000_000:
            v = round(n / 1000.0, 1)
            s = ("%s" % v).rstrip("0").rstrip(".")
            return s + "k"
        v = round(n / 1_000_000.0, 1)
        s = ("%s" % v).rstrip("0").rstrip(".")
        return s + "M"
    except Exception:
        return str(n)


def fetch_repo_stats(owner: str, repo: str, token: str = "") -> Optional[Dict[str, int]]:
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = dict(HEADERS)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        return {
            "stars": data.get("stargazers_count"),
            "watchers": data.get("subscribers_count"),
            "forks": data.get("forks_count"),
        }
    except Exception:
        return None


def build_markdown(repos: List[Tuple[str, str, str]], token: str) -> Optional[str]:
    if not repos:
        return None
    lines = ["📦 GitHub 仓库指标（Stars/Watchers/Forks）", ""]
    # Cap to 20 to avoid rate limit
    for owner, repo, url in repos[:20]:
        stats = fetch_repo_stats(owner, repo, token)
        if not stats:
            line = f"- [{owner}/{repo}]({url}) — 获取失败"
        else:
            line = (
                f"- [{owner}/{repo}]({url}) — ⭐ {abbr(stats['stars'])} | 👀 {abbr(stats['watchers'])} | 🍴 {abbr(stats['forks'])}"
            )
        lines.append(line)
    lines.append("")
    lines.append(f"> 更新时间：{beijing_now_str()}")
    return "\n".join(lines)


def push_wework_md(content: str) -> bool:
    url = os.environ.get("WEWORK_WEBHOOK_URL", "").strip()
    if not url:
        return False
    payload = {"msgtype": "markdown", "markdown": {"content": content}}
    try:
        r = requests.post(url, json=payload, timeout=15)
        return r.status_code == 200 and r.json().get("errcode") == 0
    except Exception:
        return False


def push_pushplus(title: str, content: str) -> bool:
    token = os.environ.get("PUSHPLUS_TOKEN", "").strip()
    if not token:
        return False
    api = "https://www.pushplus.plus/send"
    body = {"token": token, "title": title, "content": content, "template": "markdown"}
    try:
        r = requests.post(api, json=body, timeout=15)
        # PushPlus returns code==200 for success
        ok = False
        if r.status_code == 200:
            try:
                j = r.json()
                ok = str(j.get("code")) == "200"
            except Exception:
                ok = True
        return ok
    except Exception:
        return False


def main():
    latest = find_latest_txt_file()
    if not latest:
        print("No latest TXT found. Skip metrics push.")
        return
    repos = parse_github_repos_from_txt(latest)
    if not repos:
        print("No GitHub repos detected in latest TXT. Skip metrics push.")
        return
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    md = build_markdown(repos, token)
    if not md:
        print("No content to push.")
        return
    sent_wx = push_wework_md(md)
    sent_pp = push_pushplus("GitHub 仓库指标", md)
    print(f"WeWork pushed: {sent_wx}, PushPlus pushed: {sent_pp}")


if __name__ == "__main__":
    main()
