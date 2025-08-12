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
        # 通用 POST；实际字段以服务商文档为准，允许返回结构差异
        resp = requests.post(url, headers={**HEADERS, "X-APPKEY": appkey}, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None, f"UNIAPI HTTP {resp.status_code}"
        data = resp.json()
        # 尝试从常见字段提取 AU9999 价格
        # 兼容多种返回：{"code":"AU9999","price":xxx} 或 列表/映射
        price = None
        if isinstance(data, dict):
            # 直接字段
            for k in ("AU9999", "au9999", "price", "last", "latest"):
                v = data.get(k)
                if isinstance(v, (int, float)):
                    price = float(v)
                    break
            # 列表项
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


def fetch_from_hjjj():
    # 非官方页面，仅做兜底展示用。结构如："上海AU9999黄金价格 | 771.89"
    url = "http://www.huangjinjiage.cn/guojijinjia.html"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None, f"HJJJ HTTP {resp.status_code}"
        m = re.search(r"上海AU9999黄金价格\s*\|\s*([0-9]+(?:\.[0-9]+)?)", resp.text)
        if not m:
            return None, "未找到 AU9999 字段"
        price = float(m.group(1))
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
            # 回退兜底
            data, err = fetch_from_hjjj()
    else:
        data, err = fetch_from_hjjj()
        if data is None:
            print("HJJJ 失败:", err)
            # 回退尝试 UNIAPI（若配置了）
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
