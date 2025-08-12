# coding: utf-8
"""
AI 新闻摘要（中文）
- 读取最新 output/<date>/txt/*.txt 的内容（取最新一个），限制最大字符数
- 使用 Qwen3-Coder-480B（ModelScope OpenAI 兼容）生成中文摘要：
  - 3-6 条关键主题（带来源类型：微博/新闻/GitHub等）
  - 5 条可执行关注点（使用动词开头）
  - 若包含 GitHub 仓库链接，生成“仓库要点”简述（1 句/仓库）
- 将结果以企业微信/PushPlus 推送

Env（通过 GitHub Secrets 配置）:
  QWEN_API_BASE, QWEN_API_KEY, QWEN_MODEL
  WEWORK_WEBHOOK_URL, PUSHPLUS_TOKEN
"""
import os
import re
from pathlib import Path
from typing import Optional, List
import requests

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore

MAX_INPUT_CHARS = int(os.environ.get("NEWS_MAX_INPUT_CHARS", "25000"))
LLM_MAX_TOKENS = int(os.environ.get("NEWS_LLM_MAX_TOKENS", "900"))


def find_latest_txt() -> Optional[Path]:
    out = Path("output")
    if not out.exists():
        return None
    ds = sorted([p for p in out.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
    if not ds:
        return None
    txt_dir = ds[0] / "txt"
    if not txt_dir.exists():
        return None
    files = sorted([p for p in txt_dir.iterdir() if p.suffix == ".txt"], key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def read_clip(path: Path) -> str:
    text = path.read_text("utf-8", errors="ignore")
    return text[:MAX_INPUT_CHARS]


def collect_repo_links(text: str) -> List[str]:
    pat = re.compile(r"https?://github\.com/[\w.-]+/[\w.-]+")
    return list(dict.fromkeys(pat.findall(text)))[:12]


def call_qwen(system: str, user: str) -> Optional[str]:
    if not OpenAI:
        return None
    api_base = os.environ.get("QWEN_API_BASE", "https://api-inference.modelscope.cn/v1").strip()
    api_key = os.environ.get("QWEN_API_KEY", "").strip()
    model = os.environ.get("QWEN_MODEL", "Qwen/Qwen3-Coder-480B-A35B-Instruct").strip()
    if not api_key:
        return None
    client = OpenAI(base_url=api_base, api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=LLM_MAX_TOKENS,
        temperature=0.5,
    )
    return resp.choices[0].message.content if resp and resp.choices else None


def push_wework(md: str) -> bool:
    url = os.environ.get("WEWORK_WEBHOOK_URL", "").strip()
    if not url:
        return False
    payload = {"msgtype": "markdown", "markdown": {"content": md}}
    r = requests.post(url, json=payload, timeout=15)
    try:
        j = r.json()
    except Exception:
        j = {}
    return r.status_code == 200 and j.get("errcode") == 0


def push_plus(title: str, md: str) -> bool:
    token = os.environ.get("PUSHPLUS_TOKEN", "").strip()
    if not token:
        return False
    body = {"token": token, "title": title, "content": md, "template": "markdown"}
    r = requests.post("https://www.pushplus.plus/send", json=body, timeout=15)
    try:
        j = r.json()
        return str(j.get("code")) == "200"
    except Exception:
        return r.status_code == 200


def main() -> None:
    f = find_latest_txt()
    if not f:
        print("no latest txt")
        return
    clip = read_clip(f)
    repos = collect_repo_links(clip)

    system = (
        "你是新闻情报分析助手。请基于给定原文片段（可能包含微博/资讯/GitHub链接），"
        "输出结构化中文摘要，要求：\n"
        "1) 关键主题：3-6条，每条<=30字；\n"
        "2) 可执行关注点：3-5条，以动词开头；\n"
        "3) 若含GitHub链接，为这些仓库给出1句话用途释义（中文，简洁）。\n"
        "保持谨慎，不要臆测与虚构。"
    )
    user = f"原文片段(可能已截断):\n{clip}\n\nGitHub链接: {', '.join(repos)}"
    content = call_qwen(system, user)
    if not content:
        print("llm none; skip push")
        return

    md = f"**中文AI摘要**\n\n{content}"
    ok1 = push_wework(md)
    ok2 = push_plus("中文AI摘要", md)
    print("pushed:", ok1 or ok2)


if __name__ == "__main__":
    main()
