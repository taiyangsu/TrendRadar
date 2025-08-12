# coding: utf-8
"""
并行监控多来源黄金价格并推送企业微信（统一Markdown）：
- 纽约商品交易所（COMEX）黄金期货（美元/盎司）：TradingEconomics API（guest:guest 可用，或设置 TE_API_CLIENT/TE_API_SECRET）
- 伦敦现货黄金（美元/盎司）：Metals-API（设置 METALS_API_KEY），无KEY则跳过
- 国内黄金ETF：工银黄金ETF(518800)、华安黄金ETF(518880)、易方达黄金ETF(159934)、博时黄金ETF(159937) —— Eastmoney push2 接口
环境变量：
  WEWORK_WEBHOOK_URL 必填
  TE_API_CLIENT / TE_API_SECRET 可选（未配则使用 guest:guest）
  METALS_API_KEY 可选
  ETF_CODES 可选（逗号分隔，默认：1.518880;1.518800;0.159934;0.159937） 1=上交所 0=深交所
"""
import os
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Tuple
import requests

TIMEOUT = 15
HEADERS = {"User-Agent": "Mozilla/5.0 (TrendRadar/2.0; +https://github.com/Colton-wq/TrendRadar)"}


def beijing_now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# --- 推送 ---

def push_wework_md(content: str) -> bool:
    url = os.environ.get("WEWORK_WEBHOOK_URL", "").strip()
    if not url:
        print("WEWORK_WEBHOOK_URL 未配置，跳过推送")
        return False
    payload = {"msgtype": "markdown", "markdown": {"content": content}}
    r = requests.post(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=TIMEOUT)
    if r.status_code != 200:
        print("WeWork HTTP", r.status_code, r.text[:200])
        return False
    try:
        j = r.json()
        ok = (j.get("errcode") == 0)
        if not ok:
            print("WeWork 返回:", j)
        return ok
    except Exception:
        print("WeWork 非JSON", r.text[:200])
        return False


# --- 数据源 ---

def get_te_comex_gold() -> Tuple[Dict[str, Any], str]:
    client = os.environ.get("TE_API_CLIENT", "guest").strip() or "guest"
    secret = os.environ.get("TE_API_SECRET", "guest").strip() or "guest"
    url = f"https://api.tradingeconomics.com/commodities/gold?c={client}:{secret}&format=json"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return {}, f"TE HTTP {r.status_code}"
        arr = r.json() if r.text else []
        if isinstance(arr, list) and arr:
            item = arr[0]
            price = item.get("Last") or item.get("Price")
            return {"price": float(price), "unit": "USD/oz", "source": url}, ""
        return {}, "TE 无数据"
    except Exception as e:
        return {}, f"TE 异常 {e}"


def get_metals_spot_xau() -> Tuple[Dict[str, Any], str]:
    key = os.environ.get("METALS_API_KEY", "").strip()
    if not key:
        return {}, "未配置 METALS_API_KEY"
    url = f"https://metals-api.com/api/latest?access_key={key}&base=USD&symbols=XAU"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return {}, f"Metals HTTP {r.status_code}"
        j = r.json()
        if not j.get("success", True) and "error" in j:
            return {}, f"Metals 错误 {j.get('error')}"
        rates = j.get("rates", {})
        xau = rates.get("XAU")
        if xau:
            # rates: 1 USD -> XAU? 或 1 XAU -> USD? Metals-API 文档一般为 base->symbols 汇率；这里取 USD->XAU 反转
            # 如果值<1，视为 1 USD = x XAU => XAUUSD = 1/x
            val = float(xau)
            price = (1.0/val) if val and val < 1 else val
            return {"price": float(price), "unit": "USD/oz", "source": url}, ""
        return {}, "Metals 无 XAU"
    except Exception as e:
        return {}, f"Metals 异常 {e}"


def _fmt_code(c: str) -> Tuple[str, str]:
    # 输入如 "1.518880" -> ("1","518880")
    if "." in c:
        p = c.split(".")
        return p[0], p[1]
    return ("1" if c.startswith("5") else "0"), c


def get_etf_from_eastmoney(codes: List[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
    out = []
    errs = []
    fields = "f43,f44,f45,f46,f57,f58,f60"  # 最新、最高、最低、开盘、代码、名称、昨收
    for code in codes:
        mark, pure = _fmt_code(code)
        url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={mark}.{pure}&fields={fields}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code != 200:
                errs.append(f"{pure} HTTP {r.status_code}")
                continue
            j = r.json()
            d = j.get("data") or {}
            name = d.get("f58") or pure
            last = d.get("f43")
            if last is None:
                errs.append(f"{pure} 无价格")
                continue
            unit = "CNY"
            out.append({
                "name": name,
                "code": pure,
                "price": float(last)/100 if last > 10000 else float(last),
                "unit": unit,
                "source": url,
            })
        except Exception as e:
            errs.append(f"{pure} 异常 {e}")
    return out, errs


def build_markdown(te: Dict[str, Any], metals: Dict[str, Any], etfs: List[Dict[str, Any]]) -> str:
    lines = ["**黄金多源监控**", "", f"- 时间: {beijing_now()} (北京)"]
    if te:
        lines.append(f"- **COMEX 期货**: {te['price']:.2f} {te['unit']}")
    if metals:
        lines.append(f"- **伦敦现货(XAU/USD)**: {metals['price']:.2f} {metals['unit']}")
    if etfs:
        lines.append("")
        lines.append("**国内黄金ETF**")
        for e in etfs:
            lines.append(f"  - {e['name']}({e['code']}): {e['price']:.4f} {e['unit']}")
    lines.append("")
    # 简要来源
    srcs = []
    if te: srcs.append(f"[TE]({te['source']})")
    if metals: srcs.append(f"[Metals]({metals['source']})")
    if etfs: srcs.append("Eastmoney push2")
    if srcs:
        lines.append("数据源: " + ", ".join(srcs))
    return "\n".join(lines)


def main():
    # 1) COMEX
    te, te_err = get_te_comex_gold()
    if te_err: print("TE:", te_err)
    # 2) London Spot
    metals, m_err = get_metals_spot_xau()
    if m_err: print("Metals:", m_err)
    # 3) ETFs
    default_codes = "1.518880,1.518800,0.159934,0.159937"
    codes_env = os.environ.get("ETF_CODES", default_codes)
    codes = [c.strip() for c in codes_env.split(",") if c.strip()]
    etfs, etf_errs = get_etf_from_eastmoney(codes)
    for e in etf_errs: print("ETF:", e)

    md = build_markdown(te, metals, etfs)
    ok = push_wework_md(md)
    print("推送结果:", ok)


if __name__ == "__main__":
    main()
