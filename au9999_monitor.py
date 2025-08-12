# coding: utf-8
"""
AU9999 实时价格监控脚本（最小依赖）
- 优先支持第三方API（提供 env: UNIAPI_URL, UNIAPI_APPKEY）
- 兜底爬取展示页（env: AU9999_PROVIDER=scrape_hjjj 使用 http://www.huangjinjiage.cn/guojijinjia.html）
- 推送到企业微信（env: WEWORK_WEBHOOK_URL）
"""
import os
import re
import json
import time
from datetime import datetime
import requests

TIMEOUT = 15
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TrendRadar/2.0; +https://github.com/Colton-wq/TrendRadar)"}


def get_beijing_time_str():
    return datetime.utcnow().timestamp()


def fetch_from_uniapi():
    url = os.environ.get("UNIAPI_URL", "").strip()
    appkey = os.environ.get("UNIAPI_APPKEY", "").strip()
    if not url or not appkey:
        return None, "UNIAPI 配置缺失"

    try:
        resp = requests.post(url, headers={**HEADERS, "X-APPKEY": appkey}, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None, f"UNIAPI HTTP {resp.status_code}"
        data = resp.json()
        price = None
        if isinstance(data, dict):
            for k in ("AU9999", "au9999", "price", "last", "latest"):
                v = data.get(k)
                if isinstance(v, (int, float)):
                    price = float(v)
                    break
            if price is None:
                items = data.get("data") or data.get("result") or data.get("list")
                if isinstance(items, list):
                    for item in items:
                        code = str(item.get("code") or item.get("symbol") or "").lower()
                        if "au9999" in code:
                            for f in ("price", "last", "latest", "close", "sell", "buy"):
                                if f in item and isinstance(item[f], (int, float)):
                                    price = float(item[f])
                                    break
                            if price is not None:
                                break
        if price is None:
            return None, "UNIAPI 返回无法解析 AU9999 价格"
        return {"price": price, "source": url}, None
    except Exception as e:
        return None, f"UNIAPI 异常: {e}"


def _clean_html_text(text: str) -> str:
    # 统一空白和不可见字符
    if not isinstance(text, str):
        return ""
    text = text.replace("\xa0", " ")  # nbsp
    text = re.sub(r"[\u2000-\u200F]", " ", text)  # 其他零宽空白
    text = re.sub(r"\s+", " ", text)
    return text


def fetch_from_hjjj():
    url = "http://www.huangjinjiage.cn/guojijinjia.html"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None, f"HJJJ HTTP {resp.status_code}"
        text = _clean_html_text(resp.text)
        # 更宽松的匹配：在 AU9999 后 0~120 个字符内提取第一个数值（含小数）
        patterns = [
            r"上海\s*AU\s*9999[^0-9]{0,40}([0-9]+(?:\.[0-9]+)?)",
            r"AU\s*9999[^0-9]{0,40}([0-9]+(?:\.[0-9]+)?)",
            r"AU\s*9999[\s\S]{0,120}?([0-9]{3,4}(?:\.[0-9]{1,2})?)",
        ]
        price = None
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                try:
                    price = float(m.group(1))
                    break
                except Exception:
                    continue
        if price is None:
            return None, "未找到 AU9999 字段"
        return {"price": price, "source": url}, None
    except Exception as e:
        return None, f"HJJJ 异常: {e}"


def post_wework_markdown(content: str) -> bool:
    webhook = os.environ.get("WEWORK_WEBHOOK_URL", "").strip()
    if not webhook:
        print("WEWORK_WEBHOOK_URL 未配置，跳过推送")
        return False
    payload = {"msgtype": "markdown", "markdown": {"content": content}}
    try:
        r = requests.post(webhook, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=TIMEOUT)
        if r.status_code == 200:
            try:
                j = r.json()
                if j.get("errcode") == 0:
                    return True
                print("企业微信返回非0:", j)
            except Exception:
                print("企业微信返回非JSON:", r.text[:200])
        else:
            print("企业微信HTTP错误:", r.status_code, r.text[:200])
    except Exception as e:
        print("企业微信推送异常:", e)
    return False


def main():
    provider = os.environ.get("AU9999_PROVIDER", "scrape_hjjj").lower().strip()
    data = None
    err = None

    if provider == "uniapi":
        data, err = fetch_from_uniapi()
        if data is None:
            print("UNIAPI 失败:", err)
            data, err = fetch_from_hjjj()
    else:
        data, err = fetch_from_hjjj()
        if data is None:
            print("HJJJ 失败:", err)
            data, _ = fetch_from_uniapi()

    if data is None:
        print("未获取到 AU9999 价格，退出")
        return

    price = data["price"]
    source = data["source"]
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    md = (
        f"**AU9999 实时价格**\n\n"
        f"- **价格(元/克)**: {price:.2f}\n"
        f"- **时间**: {ts} (北京)\n"
        f"- **来源**: {source}\n"
    )

    ok = post_wework_markdown(md)
    print("推送结果:", ok)


if __name__ == "__main__":
    main()
