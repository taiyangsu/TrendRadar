# coding: utf-8
"""
并行监控多来源黄金价格并推送（企业微信 + PushPlus）：
- COMEX 期货（美元/盎司）：TradingEconomics（TE_API_CLIENT/TE_API_SECRET；未配用 guest:guest）
- 现货 XAU/USD（美元/盎司）：多源优先与降级
  1) MetalpriceAPI（METALPRICEAPI_KEY）
  2) Metals-API（METALS_API_KEY）
  3) Gold-API（GOLDAPI_URL [+ GOLDAPI_TOKEN]）
  4) FreeGoldPrice（FREEGOLDPRICE_URL [+ FREEGOLDPRICE_TOKEN]）
- 国内黄金 ETF：工银(518800)、华安(518880)、易方达(159934)、博时(159937) via Eastmoney push2

环境变量（Secrets）：
  WEWORK_WEBHOOK_URL  企业微信机器人（必填其一：企业微信或 PushPlus）
  PUSHPLUS_TOKEN      PushPlus 开放平台 Token（可选）
  TE_API_CLIENT / TE_API_SECRET        可选
  METALPRICEAPI_KEY                     可选（推荐，文档: https://metalpriceapi.com/gold）
  METALS_API_KEY                        可选
  GOLDAPI_URL, GOLDAPI_TOKEN            可选（主页: https://gold-api.com/）
  FREEGOLDPRICE_URL, FREEGOLDPRICE_TOKEN 可选（主页: https://www.freegoldprice.org）
  ETF_CODES                             可选，默认：1.518880,1.518800,0.159934,0.159937
"""
import os
import re
import json
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import requests

TIMEOUT = 15
HEADERS = {"User-Agent": "Mozilla/5.0 (TrendRadar/2.0; +https://github.com/Colton-wq/TrendRadar)"}


def beijing_now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# --- 推送通道 ---

def push_wework_md(content: str) -> bool:
    url = os.environ.get("WEWORK_WEBHOOK_URL", "").strip()
    if not url:
        return False
    payload = {"msgtype": "markdown", "markdown": {"content": content}}
    try:
        r = requests.post(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=TIMEOUT)
        if r.status_code != 200:
            print("WeWork HTTP", r.status_code, r.text[:200])
            return False
        j = r.json()
        ok = (j.get("errcode") == 0)
        if not ok:
            print("WeWork 返回:", j)
        return ok
    except Exception as e:
        print("WeWork 异常", e)
        return False


def push_pushplus_md(title: str, content: str) -> bool:
    token = os.environ.get("PUSHPLUS_TOKEN", "").strip()
    if not token:
        return False
    try:
        payload = {
            "token": token,
            "title": title,
            "content": content,
            "template": "markdown",
        }
        r = requests.post("https://www.pushplus.plus/send", json=payload, timeout=TIMEOUT)
        if r.status_code != 200:
            print("PushPlus HTTP", r.status_code, r.text[:200])
            return False
        j = r.json()
        # 文档: code==200 为成功
        ok = (j.get("code") == 200)
        if not ok:
            print("PushPlus 返回:", j)
        return ok
    except Exception as e:
        print("PushPlus 异常", e)
        return False


# --- 数据源：COMEX 期货 ---

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
            if price is None:
                return {}, "TE 缺少价格字段"
            return {"price": float(price), "unit": "USD/oz", "source": url}, ""
        return {}, "TE 无数据"
    except Exception as e:
        return {}, f"TE 异常 {e}"


# --- 数据源：XAU 现货（多源优先与降级） ---

def get_metalpriceapi_spot_xau() -> Tuple[Dict[str, Any], str]:
    key = os.environ.get("METALPRICEAPI_KEY", "").strip()
    if not key:
        return {}, "未配置 METALPRICEAPI_KEY"
    url = f"https://api.metalpriceapi.com/v1/latest?access_key={key}&base=USD&symbols=XAU"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return {}, f"MetalpriceAPI HTTP {r.status_code}"
        j = r.json()
        if not j.get("success", True):
            return {}, f"MetalpriceAPI 错误 {j.get('error')}"
        rates = j.get("rates", {})
        xau = rates.get("XAU")
        if xau is None:
            return {}, "MetalpriceAPI 无 XAU"
        val = float(xau)
        price = (1.0 / val) if 0 < val < 1 else val  # 统一为 USD/oz
        return {"price": float(price), "unit": "USD/oz", "source": url}, ""
    except Exception as e:
        return {}, f"MetalpriceAPI 异常 {e}"


def get_metalsapi_spot_xau() -> Tuple[Dict[str, Any], str]:
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
        if xau is None:
            return {}, "Metals 无 XAU"
        val = float(xau)
        price = (1.0 / val) if 0 < val < 1 else val  # 统一为 USD/oz
        return {"price": float(price), "unit": "USD/oz", "source": url}, ""
    except Exception as e:
        return {}, f"Metals 异常 {e}"


def _fetch_json_generic(url: str, token: Optional[str] = None) -> Tuple[Optional[dict], str]:
    if not url:
        return None, "未配置 URL"
    headers = dict(HEADERS)
    if token:
        # 通用令牌头：优先 Authorization: Bearer；不确定时也可作为 X-API-Key
        headers["Authorization"] = f"Bearer {token}"
        headers.setdefault("X-API-Key", token)
    try:
        r = requests.get(url, headers=headers, timeout=TIMEOUT)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}"
        return r.json(), ""
    except Exception as e:
        return None, f"异常 {e}"


def get_goldapi_spot_xau() -> Tuple[Dict[str, Any], str]:
    url = os.environ.get("GOLDAPI_URL", "").strip()
    token = os.environ.get("GOLDAPI_TOKEN", "").strip() or None
    if not url:
        return {}, "未配置 GOLDAPI_URL"
    j, err = _fetch_json_generic(url, token)
    if err:
        return {}, f"Gold-API {err}"
    # 尽量通用字段解析
    for k in ["price", "usd", "per_oz", "xauusd", "value"]:
        v = j.get(k)
        if isinstance(v, (int, float)):
            return {"price": float(v), "unit": "USD/oz", "source": url}, ""
    # 嵌套结构尝试
    for k in ["data", "result", "rates"]:
        if isinstance(j.get(k), dict):
            sub = j[k]
            for kk in ["price", "USD", "XAUUSD", "per_oz", "value"]:
                v2 = sub.get(kk)
                if isinstance(v2, (int, float)):
                    return {"price": float(v2), "unit": "USD/oz", "source": url}, ""
    return {}, "Gold-API 未识别价格字段"


def get_freegoldprice_spot_xau() -> Tuple[Dict[str, Any], str]:
    url = os.environ.get("FREEGOLDPRICE_URL", "").strip()
    token = os.environ.get("FREEGOLDPRICE_TOKEN", "").strip() or None
    if not url:
        return {}, "未配置 FREEGOLDPRICE_URL"
    j, err = _fetch_json_generic(url, token)
    if err:
        return {}, f"FreeGoldPrice {err}"
    # 常见字段尝试
    for k in ["price", "usd", "xauusd", "per_oz", "value"]:
        v = j.get(k)
        if isinstance(v, (int, float)):
            return {"price": float(v), "unit": "USD/oz", "source": url}, ""
    # 嵌套
    for k in ["data", "result", "rates"]:
        if isinstance(j.get(k), dict):
            sub = j[k]
            for kk in ["price", "USD", "XAUUSD", "per_oz", "value"]:
                v2 = sub.get(kk)
                if isinstance(v2, (int, float)):
                    return {"price": float(v2), "unit": "USD/oz", "source": url}, ""
    return {}, "FreeGoldPrice 未识别价格字段"


# --- 数据源：国内 ETF ---

def _fmt_code(c: str) -> Tuple[str, str]:
    # 输入如 "1.518880" -> ("1","518880")；若无点，以 5 开头默认为上交所 1，否则深交所 0
    if "." in c:
        p = c.split(".")
        return p[0], p[1]
    return ("1" if c.startswith("5") else "0"), c


def get_etf_from_eastmoney(codes: List[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
    out, errs = [], []
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
            price = float(last)/100 if isinstance(last, (int, float)) and last > 10000 else float(last)
            out.append({"name": name, "code": pure, "price": price, "unit": unit, "source": url})
        except Exception as e:
            errs.append(f"{pure} 异常 {e}")
    return out, errs


# --- 统一渲染 ---

def build_markdown(te: Dict[str, Any], spot: Dict[str, Any], etfs: List[Dict[str, Any]]) -> str:
    lines = ["**黄金多源监控**", "", f"- 时间: {beijing_now()} (北京)"]
    if te:
        lines.append(f"- **COMEX 期货**: {te['price']:.2f} {te['unit']}")
    if spot:
        lines.append(f"- **伦敦现货 (XAU/USD)**: {spot['price']:.2f} {spot['unit']}")
    if etfs:
        lines.append("")
        lines.append("**国内黄金ETF**")
        for e in etfs:
            lines.append(f"  - {e['name']}({e['code']}): {e['price']:.4f} {e['unit']}")
    lines.append("")
    srcs = []
    if te: srcs.append(f"[TE]({te['source']})")
    if spot: srcs.append(f"[Spot]({spot['source']})")
    if etfs: srcs.append("Eastmoney push2")
    if srcs:
        lines.append("数据源: " + ", ".join(srcs))
    return "\n".join(lines)


def main():
    # 1) COMEX 期货
    te, te_err = get_te_comex_gold()
    if te_err: print("TE:", te_err)

    # 2) 现货 XAU/USD（多源优先与降级）
    spot: Dict[str, Any] = {}
    spot_errs: List[str] = []
    for getter in (
        get_metalpriceapi_spot_xau,
        get_metalsapi_spot_xau,
        get_goldapi_spot_xau,
        get_freegoldprice_spot_xau,
    ):
        data, err = getter()
        if data:
            spot = data
            break
        if err:
            spot_errs.append(err)
    for e in spot_errs:
        print("SPOT:", e)

    # 3) ETF
    default_codes = "1.518880,1.518800,0.159934,0.159937"
    codes_env = os.environ.get("ETF_CODES", default_codes)
    codes = [c.strip() for c in codes_env.split(",") if c.strip()]
    etfs, etf_errs = get_etf_from_eastmoney(codes)
    for e in etf_errs:
        print("ETF:", e)

    md = build_markdown(te, spot, etfs)

    # 并行推送，任一成功即认为成功
    ok_wework = push_wework_md(md)
    ok_pp = push_pushplus_md("黄金多源监控", md)
    ok = ok_wework or ok_pp
    print("推送结果:", ok, "+WeWork" if ok_wework else "", "+PushPlus" if ok_pp else "")


if __name__ == "__main__":
    main()
