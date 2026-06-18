#!/usr/bin/env python3
"""Fetch global stock quote data and write dashboard JSON/CSV artifacts.

Primary quote source: Yahoo Finance public chart endpoint for current price/volume.
Shares outstanding: yfinance fast_info when available, cached locally so market cap can be
computed as price * shares. This keeps API keys out of the public GitHub Pages dashboard.
"""
from __future__ import annotations

import csv
import json
import math
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DOCS_DATA = ROOT / "docs" / "data"
COMPANIES_CSV = DATA_DIR / "companies.csv"
RATES_CSV = DATA_DIR / "exchange_rates.csv"
SHARES_CACHE = DATA_DIR / "shares_outstanding_cache.json"
QUOTES_JSON = DOCS_DATA / "market_quotes.json"
QUOTES_CSV = DOCS_DATA / "market_quotes.csv"
HISTORY_CSV = DOCS_DATA / "market_history.csv"
USER_AGENT = "Mozilla/5.0 (compatible; NK-rbdautobot-market-dashboard/1.0)"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_rates() -> dict[str, float]:
    rows = read_csv(RATES_CSV)
    return {r["currency"]: float(r["krw_rate"].replace(",", "")) for r in rows}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def fetch_chart(symbol: str) -> dict[str, Any]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    err = payload.get("chart", {}).get("error")
    if err:
        raise RuntimeError(str(err))
    result = payload.get("chart", {}).get("result") or []
    if not result:
        raise RuntimeError("empty chart result")
    return result[0].get("meta", {})


def get_shares_from_yfinance(symbol: str) -> float | None:
    try:
        import yfinance as yf  # type: ignore
        ticker = yf.Ticker(symbol)
        fast = ticker.fast_info
        shares = fast.get("shares") if hasattr(fast, "get") else None
        if shares and float(shares) > 0:
            return float(shares)
    except Exception:
        return None
    return None


def finite_num(v: Any) -> float | None:
    try:
        x = float(v)
        if math.isfinite(x):
            return x
    except Exception:
        return None
    return None


def main() -> int:
    companies = read_csv(COMPANIES_CSV)
    rates = read_rates()
    shares_cache: dict[str, Any] = load_json(SHARES_CACHE, {})
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    rows: list[dict[str, Any]] = []

    for i, c in enumerate(companies, 1):
        symbol = c["yahoo_symbol"]
        row: dict[str, Any] = {**c}
        row.update({
            "as_of_utc": now,
            "price": None,
            "previous_close": None,
            "change": None,
            "change_percent": None,
            "day_high": None,
            "day_low": None,
            "volume": None,
            "market_time": None,
            "shares_outstanding": None,
            "market_cap_local": None,
            "market_cap_krw": None,
            "krw_rate": rates.get(c["currency"]),
            "source": "Yahoo Finance chart + yfinance shares cache",
            "data_status": "pending",
            "error": "",
        })
        try:
            meta = fetch_chart(symbol)
            price = finite_num(meta.get("regularMarketPrice"))
            prev = finite_num(meta.get("chartPreviousClose"))
            if price is None:
                raise RuntimeError("missing regularMarketPrice")
            chart_currency = meta.get("currency") or c["currency"]
            row["currency"] = chart_currency
            row["price"] = price
            row["previous_close"] = prev
            row["change"] = None if prev in (None, 0) else price - prev
            row["change_percent"] = None if prev in (None, 0) else ((price / prev) - 1) * 100
            row["day_high"] = finite_num(meta.get("regularMarketDayHigh"))
            row["day_low"] = finite_num(meta.get("regularMarketDayLow"))
            row["volume"] = finite_num(meta.get("regularMarketVolume"))
            mt = meta.get("regularMarketTime")
            if isinstance(mt, (int, float)):
                row["market_time"] = datetime.fromtimestamp(mt, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

            shares = finite_num(shares_cache.get(symbol, {}).get("shares"))
            if not shares:
                shares = get_shares_from_yfinance(symbol)
                if shares:
                    shares_cache[symbol] = {"shares": shares, "updated_at": now}
            row["shares_outstanding"] = shares
            rate = rates.get(chart_currency) or rates.get(c["currency"])
            row["krw_rate"] = rate
            if shares and rate:
                cap_local = price * shares
                row["market_cap_local"] = cap_local
                row["market_cap_krw"] = cap_local * rate
                row["data_status"] = "ok"
            else:
                row["data_status"] = "price_only"
                row["error"] = "shares_outstanding_or_fx_missing"
        except Exception as e:
            row["data_status"] = "error"
            row["error"] = str(e)[:300]
        rows.append(row)
        # Conservative pacing for public endpoints.
        time.sleep(0.25 if i < len(companies) else 0)

    ok_rows = [r for r in rows if r.get("data_status") == "ok"]
    payload = {
        "generated_at_utc": now,
        "company_count": len(rows),
        "ok_count": len(ok_rows),
        "price_available_count": sum(1 for r in rows if r.get("price") is not None),
        "total_market_cap_krw": sum(float(r.get("market_cap_krw") or 0) for r in rows),
        "exchange_rates_krw": rates,
        "disclaimer_ko": "무료/지연 시세 기반 참고용 데이터입니다. 투자 판단용 실시간 호가가 아닙니다. 시가총액 KRW 환산은 사용자가 지정한 고정 환율을 적용합니다.",
        "rows": rows,
    }
    save_json(SHARES_CACHE, shares_cache)
    save_json(QUOTES_JSON, payload)

    QUOTES_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with QUOTES_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader(); writer.writerows(rows)

    history_fields = ["as_of_utc", "company_ko", "company_en", "yahoo_symbol", "currency", "price", "change_percent", "market_cap_local", "market_cap_krw", "data_status"]
    write_header = not HISTORY_CSV.exists()
    with HISTORY_CSV.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=history_fields)
        if write_header:
            writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k) for k in history_fields})

    print(f"wrote {QUOTES_JSON} rows={len(rows)} ok={len(ok_rows)} price={payload['price_available_count']}")
    if len(ok_rows) < max(1, len(rows) // 2):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
