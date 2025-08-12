# coding: utf-8
"""
GitHub 指定仓库更新监控（增量摘要）
- 输入：环境变量 GH_WATCH_REPOS（逗号分隔的仓库URL），GH_WATCH_SINCE_HOURS（回溯小时，默认6）
- 数据：使用 GitHub API 查询近N小时内的 commits / releases / issues(PR含在内)
- 输出：中文Markdown摘要，推送企业微信/PushPlus
"""
import os
import datetime as dt
from typing import List, Dict
import requests

HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
PUSH_URL = "https://www.pushplus.plus/send"


def gh_headers() -> Dict[str, str]:
    h = dict(HEADERS)
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def iso_since(hours: int) -> str:
    t = dt.datetime.utcnow() - dt.timedelta(hours=hours)
    return t.replace(microsecond=0).isoformat() + "Z"


def parse_repo(u: str) -> (str, str):
    p = u.rstrip("/").split("/")
    return p[-2], p[-1]


def fetch_commits(owner: str, repo: str, since_iso: str) -> List[Dict]:
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?since={since_iso}&per_page=100"
    r = requests.get(url, headers=gh_headers(), timeout=20)
    return r.json() if r.status_code == 200 else []


def fetch_releases(owner: str, repo: str, since_iso: str) -> List[Dict]:
    url = f"https://api.github.com/repos/{owner}/{repo}/releases?per_page=10"
    r = requests.get(url, headers=gh_headers(), timeout=20)
    if r.status_code != 200:
        return []
    data = r.json() or []
    return [x for x in data if (x.get("created_at") or x.get("published_at") or "") >= since_iso]


def fetch_issues(owner: str, repo: str, since_iso: str) -> List[Dict]:
    # 包含PR
    url = f"https://api.github.com/repos/{owner}/{repo}/issues?since={since_iso}&state=open&per_page=100"
    r = requests.get(url, headers=gh_headers(), timeout=20)
    return r.json() if r.status_code == 200 else []


def push_wework(md: str) -> bool:
    url = os.environ.get("WEWORK_WEBHOOK_URL", "").strip()
    if not url:
        return False
    try:
        r = requests.post(url, json={"msgtype": "markdown", "markdown": {"content": md}}, timeout=15)
        j = r.json()
        return r.status_code == 200 and j.get("errcode") == 0
    except Exception:
        return False


def push_plus(title: str, md: str) -> bool:
    token = os.environ.get("PUSHPLUS_TOKEN", "").strip()
    if not token:
        return False
    try:
        r = requests.post(PUSH_URL, json={"token": token, "title": title, "content": md, "template": "markdown"}, timeout=15)
        j = r.json()
        return str(j.get("code")) == "200"
    except Exception:
        return False


def main() -> None:
    repos_env = os.environ.get("GH_WATCH_REPOS", "").strip()
    hours = int(os.environ.get("GH_WATCH_SINCE_HOURS", "6"))
    if not repos_env:
        print("no GH_WATCH_REPOS")
        return
    since_iso = iso_since(hours)
    lines = [f"**GitHub 指定仓库近{hours}小时更新**", ""]
    any_change = False
    for u in [x.strip() for x in repos_env.split(",") if x.strip()]:
        owner, repo = parse_repo(u)
        commits = fetch_commits(owner, repo, since_iso)
        releases = fetch_releases(owner, repo, since_iso)
        issues = fetch_issues(owner, repo, since_iso)
        if not (commits or releases or issues):
            continue
        any_change = True
        lines.append(f"- [{owner}/{repo}]({u})")
        if releases:
            for rel in releases:
                tag = rel.get("tag_name") or rel.get("name") or "release"
                link = rel.get("html_url") or u + "/releases"
                lines.append(f"  - 发布: {tag} → {link}")
        if commits:
            lines.append(f"  - 提交: {len(commits)} 条（近{hours}小时）")
        if issues:
            opened = [i for i in issues if i.get("created_at", "") >= since_iso]
            if opened:
                lines.append(f"  - 新议题/PR: {len(opened)} 条")
    if not any_change:
        print("no changes")
        return
    md = "\n".join(lines)
    ok = push_wework(md) or push_plus("GitHub 指定仓库更新", md)
    print("pushed:", ok)


if __name__ == "__main__":
    main()
