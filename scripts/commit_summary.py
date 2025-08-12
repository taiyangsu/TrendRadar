# coding: utf-8
"""
Commit Chinese Summary Generator
- Trigger: GitHub Actions push event
- Input: list of commits + git diff (truncated)
- LLM: Qwen3-Coder-480B via ModelScope (OpenAI-compatible)
- Output:
  1) Comment on each commit (Markdown, Chinese)
  2) Optional push to WeWork / PushPlus if tokens provided

Env Vars (Secrets recommended):
  GITHUB_TOKEN          # auto-injected by Actions
  GITHUB_EVENT_PATH     # auto-injected by Actions
  QWEN_API_BASE         # e.g. https://api-inference.modelscope.cn/v1
  QWEN_API_KEY          # your ModelScope token
  QWEN_MODEL            # default: Qwen/Qwen3-Coder-480B-A35B-Instruct
  WEWORK_WEBHOOK_URL    # optional
  PUSHPLUS_TOKEN        # optional

Note: We do NOT store secrets in repo. Configure them via GitHub Secrets.
"""
import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

# OpenAI-python >= 1.0
try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore

MAX_COMMITS = int(os.environ.get("MAX_COMMITS", "3"))
MAX_DIFF_CHARS = int(os.environ.get("MAX_DIFF_CHARS", "120000"))  # ~120k chars cap
MAX_PER_COMMIT_CHARS = int(os.environ.get("MAX_PER_COMMIT_CHARS", "40000"))
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "800"))
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.7"))


def run(cmd: List[str], cwd: Optional[str] = None) -> str:
    cp = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    return cp.stdout.strip()


def read_push_event() -> Dict:
    path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not path or not Path(path).exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def collect_commits(evt: Dict) -> List[Dict]:
    commits = evt.get("commits", []) or []
    # newest last; we prefer latest first
    commits = commits[-MAX_COMMITS:]
    commits.reverse()
    return commits


def git_diff_for_commit(sha: str) -> str:
    # unified=0 keeps line precise, but can be verbose; we still cap
    cmd = [
        "git",
        "show",
        "--no-color",
        "--unified=0",
        "--no-ext-diff",
        "--minimal",
        sha,
    ]
    out = run(cmd)
    if len(out) > MAX_PER_COMMIT_CHARS:
        out = out[:MAX_PER_COMMIT_CHARS] + "\n...<truncated>\n"
    return out


def build_prompt(commit: Dict, diff_text: str) -> List[Dict[str, str]]:
    message = commit.get("message", "")
    author = (commit.get("author") or {}).get("name", "")
    files_added = commit.get("added", [])
    files_removed = commit.get("removed", [])
    files_modified = commit.get("modified", [])

    file_brief = []
    if files_added:
        file_brief.append(f"新增: {len(files_added)}")
    if files_removed:
        file_brief.append(f"删除: {len(files_removed)}")
    if files_modified:
        file_brief.append(f"修改: {len(files_modified)}")
    file_line = "，".join(file_brief) if file_brief else "无文件清单（仅提交信息）"

    system = (
        "你是代码审阅助理。请基于提供的英文代码/注释与diff，输出严格中文摘要，"
        "包含：1句话标题；3-6条要点（变更动机/核心改动/受影响模块或接口/潜在风险或破坏性变更/是否补充测试）；"
        "如无足够上下文请诚实说明并给出安全摘要；禁止臆测实现细节。"
    )

    user = (
        f"提交作者: {author}\n"
        f"提交信息: {message}\n"
        f"文件变更: {file_line}\n\n"
        f"=== DIFF (可能已截断) ===\n{diff_text}\n"
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    return messages


def call_llm(messages: List[Dict[str, str]]) -> Optional[str]:
    api_base = os.environ.get("QWEN_API_BASE", "https://api-inference.modelscope.cn/v1").strip()
    api_key = os.environ.get("QWEN_API_KEY", "").strip()
    model = os.environ.get("QWEN_MODEL", "Qwen/Qwen3-Coder-480B-A35B-Instruct").strip()

    if not OpenAI:
        return None
    if not api_key:
        return None

    try:
        client = OpenAI(base_url=api_base, api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=LLM_MAX_TOKENS,
            temperature=LLM_TEMPERATURE,
        )
        content = resp.choices[0].message.content if resp and resp.choices else None
        return content
    except Exception as e:
        print(f"LLM 调用失败: {e}")
        return None


def comment_on_commit(owner: str, repo: str, sha: str, body: str, token: str) -> bool:
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {"body": body}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        ok = r.status_code in (200, 201)
        if not ok:
            print("提交评论失败:", r.status_code, r.text)
        return ok
    except Exception as e:
        print("提交评论异常:", e)
        return False


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
        if r.status_code == 200:
            try:
                j = r.json()
                return str(j.get("code")) == "200"
            except Exception:
                return True
        return False
    except Exception:
        return False


def make_markdown_summary(title: str, content: str, sha: str) -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    link = f"https://github.com/{repo}/commit/{sha}" if repo else ""
    head = f"### {title}\n\n" if title else ""
    tail = f"\n\n[查看提交]({link})" if link else ""
    return head + content + tail


def main() -> None:
    evt = read_push_event()
    if not evt:
        print("未读取到 push 事件")
        return

    repo_full = os.environ.get("GITHUB_REPOSITORY", "")
    owner, name = repo_full.split("/", 1) if "/" in repo_full else ("", "")
    gh_token = os.environ.get("GITHUB_TOKEN", "").strip()

    commits = collect_commits(evt)
    if not commits:
        print("无提交，结束")
        return

    total_chars = 0
    for c in commits:
        sha = c.get("id") or ""
        if not sha:
            continue
        diff = git_diff_for_commit(sha)
        # 全局上限控制
        budget_left = MAX_DIFF_CHARS - total_chars
        if budget_left <= 0:
            diff = "<diff budget reached, skip details>"
        elif len(diff) > budget_left:
            diff = diff[:budget_left] + "\n...<truncated>\n"
            total_chars = MAX_DIFF_CHARS
        else:
            total_chars += len(diff)

        messages = build_prompt(c, diff)
        content = call_llm(messages)
        if not content:
            # 兜底模板
            msg = c.get("message", "")
            files = c.get("added", []) + c.get("removed", []) + c.get("modified", [])
            content = (
                "本次提交的中文摘要生成失败，以下为兜底信息：\n\n"
                f"- 原始提交信息：{msg}\n"
                f"- 涉及文件数：{len(files)}\n"
                "- 建议查看提交链接了解详细改动。"
            )
        title_line = "中文提交摘要"
        md = make_markdown_summary(title_line, content, sha)

        # 1) 评论到提交（若有 token 且 repo 信息齐全）
        if owner and name and gh_token:
            comment_on_commit(owner, name, sha, md, gh_token)
        # 2) 企业微信 / PushPlus 并行（可选）
        push_wework_md(md)
        push_pushplus(title_line, md)


if __name__ == "__main__":
    main()
