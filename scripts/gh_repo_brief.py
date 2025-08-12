# coding: utf-8
"""
GitHub 仓库用途简述（Qwen 强提示）
- 输入：GitHub 仓库 URL 列表（环境变量 GH_REPOS）
- 行为：GitHub API 获取 description/topics/README 片段；Qwen 输出中文“一句话用途”（≤20字）
- 输出：markdown 列表文本
Env:
  GITHUB_TOKEN, QWEN_API_BASE, QWEN_API_KEY, QWEN_MODEL
"""
import os
import base64
from typing import List, Tuple
import requests

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore

API = "https://api.github.com"


def gh_get(owner: str, repo: str, path: str) -> requests.Response:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    return requests.get(f"{API}/repos/{owner}/{repo}{path}", headers=headers, timeout=15)


def fetch_repo_brief(owner: str, repo: str) -> Tuple[str, str, str]:
    full = f"{owner}/{repo}"
    link = f"https://github.com/{full}"
    desc = ""
    topics = []
    r = gh_get(owner, repo, "")
    if r.status_code == 200:
        j = r.json()
        desc = (j.get("description") or "").strip()
        topics = j.get("topics") or []
    r2 = gh_get(owner, repo, "/readme")
    readme = ""
    if r2.status_code == 200:
        try:
            j2 = r2.json()
            content_b64 = j2.get("content") or ""
            readme = base64.b64decode(content_b64).decode("utf-8", errors="ignore")[:2000]
        except Exception:
            pass
    material = f"描述:{desc}\nTopics:{', '.join(topics)}\nREADME片段:\n{readme}"
    return full, material, link

PRO_SYSTEM_PROMPT = (
    "你是开源项目解说员。根据提供的项目简介/Topics/README片段，为每个仓库生成‘中文一句话用途’，"
    "严格要求：\n- ≤20字；\n- 避免空泛词；\n- 无表情符号；\n- 信息不足时写‘信息不足’；\n- 不臆测。\n"
    "输出 Markdown 列表，每行格式：\n- owner/repo：用途简述\n"
)


def call_qwen(materials: List[Tuple[str, str, str]]) -> str:
    if not OpenAI:
        return ""
    api_base = os.environ.get("QWEN_API_BASE", "https://api-inference.modelscope.cn/v1").strip()
    api_key = os.environ.get("QWEN_API_KEY", "").strip()
    model = os.environ.get("QWEN_MODEL", "Qwen/Qwen3-Coder-480B-A35B-Instruct").strip()
    if not api_key:
        return ""
    client = OpenAI(base_url=api_base, api_key=api_key)
    text = "\n\n".join([f"[{full}] {link}\n{mat}" for full, mat, link in materials])
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": PRO_SYSTEM_PROMPT}, {"role": "user", "content": text}],
        max_tokens=800,
        temperature=0.3,
    )
    return resp.choices[0].message.content if resp and resp.choices else ""


def main() -> None:
    urls = [u.strip() for u in (os.environ.get("GH_REPOS", "").split(",")) if u.strip()]
    pairs: List[Tuple[str, str, str]] = []
    for u in urls[:8]:
        try:
            parts = u.rstrip("/").split("/")
            owner, repo = parts[-2], parts[-1]
            pairs.append(fetch_repo_brief(owner, repo))
        except Exception:
            continue
    if not pairs:
        print("no repos")
        return
    md = call_qwen(pairs)
    print(md)


if __name__ == "__main__":
    main()
