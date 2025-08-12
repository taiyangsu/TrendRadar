# coding: utf-8
"""
LLM 后处理：对本次抓取文本做结构化提炼
- 输入：latest output/<date>/txt/*.txt（取最新文件，截断）
- 模型：Qwen3-Coder-480B（ModelScope OpenAI 兼容）
- 输出：output/ai/summary_<date>.json（UTF-8，含要点、标签、实体、风险、来源统计）
- 并打印简要统计，供工作流日志查看
Env：QWEN_API_BASE、QWEN_API_KEY、QWEN_MODEL
"""
import os
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore

MAX_INPUT_CHARS = int(os.environ.get("NEWS_STRUCT_MAX_INPUT", "24000"))


def find_latest_txt() -> Optional[Path]:
    out = Path("output")
    if not out.exists():
        return None
    dates = sorted([p for p in out.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
    if not dates:
        return None
    txt_dir = dates[0] / "txt"
    if not txt_dir.exists():
        return None
    files = sorted([p for p in txt_dir.iterdir() if p.suffix == ".txt"], key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def read_clip(path: Path) -> str:
    text = path.read_text("utf-8", errors="ignore")
    return text[:MAX_INPUT_CHARS]


SYSTEM = (
    "你是信息抽取器。请严格基于给定文本，返回 JSON，不要产生多余字段或注释。\n"
    "要求：\n"
    "- 不臆测，未知填 null 或空数组；\n"
    "- 中文输出；\n"
    "- schema: {summary:{highlights:[string], actions:[string]}, items:[{title:string|null, source:string|null, gist:string, tags:[string], entities:{org:[string], person:[string], ticker:[string]}, risk:string|null}], stats:{source_count:object}}\n"
)

USER_TMPL = (
    "原文片段（可能已截断）：\n{clip}\n\n"
    "请识别来源类别（微博/新闻/GitHub/社区等），每条 items.gist≤50字；actions 用动词开头。"
)


def call_llm(clip: str) -> Optional[dict]:
    if not OpenAI:
        return None
    api_base = os.environ.get("QWEN_API_BASE", "https://api-inference.modelscope.cn/v1").strip()
    api_key = os.environ.get("QWEN_API_KEY", "").strip()
    model = os.environ.get("QWEN_MODEL", "Qwen/Qwen3-Coder-480B-A35B-Instruct").strip()
    if not api_key:
        return None
    client = OpenAI(base_url=api_base, api_key=api_key)
    user = USER_TMPL.format(clip=clip)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
        max_tokens=1000,
        temperature=0.3,
    )
    content = resp.choices[0].message.content if resp and resp.choices else None
    if not content:
        return None
    # 尝试解析 JSON（容错去除围绕性的 markdown 包裹）
    s = content.strip()
    if s.startswith("```"):
        s = s.strip('`')
        # 可能形如 json\n{...}
        idx = s.find("{")
        s = s[idx:] if idx >= 0 else s
    try:
        return json.loads(s)
    except Exception:
        return None


def save_json(data: dict) -> Path:
    ai_dir = Path("output/ai")
    ai_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = ai_dir / f"summary_{ts}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    return path


def main() -> None:
    latest = find_latest_txt()
    if not latest:
        print("no txt")
        return
    clip = read_clip(latest)
    data = call_llm(clip)
    if not data:
        print("llm failed")
        return
    out = save_json(data)
    items = data.get("items") or []
    print(f"saved {out} with {len(items)} items")


if __name__ == "__main__":
    main()
