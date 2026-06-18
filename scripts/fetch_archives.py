#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOCS_DATA = ROOT / "docs" / "data"
FIN_SHEET_ID = "1jzdID-ZY39VhKgHdvpSIcGiJq0Gk_qsOj1k6hNi3jh8"
FIN_MARKET_GID = "1335393180"  # 시가총액 tab
NEWS_SHEET_ID = "1nA4GhaJA14_2tpHimX0-AsCpCE2G5YFySjGX79hzrCw"
NEWS_GID = "0"
USER_AGENT = "Mozilla/5.0 (compatible; NK-rbdautobot-dashboard-archive/1.0)"

COMPANY_ALIASES = {
    "알파벳": ["Alphabet", "Google", "GOOG", "구글"],
    "마이크로소프트": ["Microsoft", "MSFT", "Xbox", "Game Pass", "마이크로소프트"],
    "애플": ["Apple", "AAPL", "App Store", "애플"],
    "넥슨": ["Nexon", "넥슨", "MapleStory", "메이플", "Dungeon Fighter", "던전앤파이터", "마비노기"],
    "텐센트": ["Tencent", "0700", "텐센트", "Honor of Kings", "王者荣耀"],
    "넷이즈": ["NetEase", "Netease", "NTES", "넷이즈", "网易"],
    "닌텐도": ["Nintendo", "닌텐도", "Switch", "Mario", "Zelda", "Pokemon", "Pokémon"],
    "소니": ["Sony", "PlayStation", "PS5", "소니"],
    "로블록스": ["Roblox", "RBLX", "로블록스"],
    "일렉트로닉 아츠": ["Electronic Arts", "EA", "Battlefield", "Apex Legends", "FC 26"],
    "테이크투": ["Take-Two", "Take Two", "TTWO", "Rockstar", "GTA", "2K Games"],
    "유비소프트": ["Ubisoft", "UBI", "Assassin", "유비소프트"],
    "크래프톤": ["Krafton", "PUBG", "크래프톤", "배틀그라운드"],
    "엔씨소프트": ["NCSOFT", "NCSoft", "엔씨소프트", "Lineage", "리니지"],
    "넷마블": ["Netmarble", "넷마블"],
    "카카오게임즈": ["Kakao Games", "카카오게임즈"],
    "위메이드": ["Wemade", "위메이드", "WEMIX"],
    "펄어비스": ["Pearl Abyss", "펄어비스", "Black Desert", "검은사막"],
    "시프트업": ["Shift Up", "시프트업", "Stellar Blade", "NIKKE", "니케"],
    "캡콤": ["Capcom", "캡콤", "Monster Hunter", "Resident Evil"],
    "반다이남코": ["Bandai Namco", "반다이남코", "Elden Ring", "Tekken"],
    "스퀘어에닉스": ["Square Enix", "스퀘어에닉스", "Final Fantasy", "Dragon Quest"],
    "세가": ["Sega", "SEGA", "세가", "Sonic", "Persona"],
    "엠브레이서 그룹": ["Embracer", "EMBRAC", "엠브레이서"],
    "SEA": ["Sea Limited", "Garena", "Free Fire", "NYSE:SE"],
    "데브시스터즈": ["Devsisters", "데브시스터즈", "CookieRun", "쿠키런"],
    "네오위즈": ["Neowiz", "네오위즈", "Lies of P"],
    "감마니아": ["Gamania", "감마니아"],
    "라스타": ["Rastar", "라스타"],
    "세기화통": ["Century Huatong", "세기화통"],
    "킹넷": ["Kingnet", "킹넷"],
    "애스피어": ["Asphere", "AS.BK", "애스피어"],
}


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read().decode("utf-8-sig", errors="ignore")


def sheet_csv(sheet_id: str, gid: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}"


def parse_money(v: str) -> float | None:
    if not v:
        return None
    s = str(v).replace(",", "").replace("%", "").strip()
    if s in {"", "-"}:
        return None
    try:
        return float(s)
    except Exception:
        return None


def fetch_financial_archive() -> dict[str, Any]:
    text = fetch_text(sheet_csv(FIN_SHEET_ID, FIN_MARKET_GID))
    rows = list(csv.DictReader(io.StringIO(text)))
    items = []
    for r in rows:
        name = (r.get("기업명") or "").strip()
        if not name:
            continue
        item = {
            "company": name,
            "ticker": r.get("티커", ""),
            "source_link": r.get("링크", ""),
            "q1_revenue_local": parse_money(r.get("2026 Q1 매출", "")),
            "q1_operating_profit_local": parse_money(r.get("2026 Q1 영업이익", "")),
            "q1_revenue_krw_label": r.get("2026 Q1 매출 (원)", ""),
            "q1_operating_profit_krw_label": r.get("2026 Q1 영업이익 (원)", ""),
            "market_cap_label_from_sheet": r.get("시가총액", ""),
        }
        if item["q1_revenue_krw_label"] or item["q1_operating_profit_krw_label"]:
            items.append(item)
    return {
        "source": "Google Sheets financial archive / 시가총액 tab",
        "sheet_url": f"https://docs.google.com/spreadsheets/d/{FIN_SHEET_ID}/edit?gid={FIN_MARKET_GID}#gid={FIN_MARKET_GID}",
        "count": len(items),
        "rows": items,
    }


def parse_date_key(s: str) -> str:
    s = (s or "").strip()
    # Preserve original but make lexical sort work for YYYY-MM-DD formats.
    m = re.search(r"(20\d{2})[-./](\d{1,2})[-./](\d{1,2})(?:\s+(\d{1,2}:\d{2}(?::\d{2})?))?", s)
    if m:
        y, mo, d, t = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d} {t or '00:00:00'}"
    return s


def fetch_news_archive(limit_per_company: int = 5, max_total: int = 120) -> dict[str, Any]:
    text = fetch_text(sheet_csv(NEWS_SHEET_ID, NEWS_GID))
    reader = csv.DictReader(io.StringIO(text))
    buckets: dict[str, list[dict[str, Any]]] = {k: [] for k in COMPANY_ALIASES}
    for r in reader:
        hay = " ".join([r.get("키워드", ""), r.get("제목", ""), r.get("기사 내용", ""), r.get("기사 분석", ""), r.get("제목 번역(3점 이상)", ""), r.get("3줄 요약(4, 5점)", "")]).lower()
        for company, aliases in COMPANY_ALIASES.items():
            if any(a.lower() in hay for a in aliases):
                title = r.get("제목 번역(3점 이상)") or r.get("제목") or ""
                summary = r.get("3줄 요약(4, 5점)") or r.get("기사 분석") or r.get("기사 내용", "")[:220]
                buckets[company].append({
                    "company": company,
                    "keyword": r.get("키워드", ""),
                    "title": title[:240],
                    "original_title": r.get("제목", "")[:240],
                    "url": r.get("링크", ""),
                    "published_at": r.get("업로드 시간", ""),
                    "published_key": parse_date_key(r.get("업로드 시간", "")),
                    "score": r.get("점수", ""),
                    "evaluation": r.get("평가", ""),
                    "summary": summary[:500],
                })
    out = []
    for company, rows in buckets.items():
        rows.sort(key=lambda x: x.get("published_key", ""), reverse=True)
        # Deduplicate by URL/title.
        seen = set(); selected = []
        for x in rows:
            key = x.get("url") or x.get("title")
            if key in seen:
                continue
            seen.add(key); selected.append(x)
            if len(selected) >= limit_per_company:
                break
        out.extend(selected)
    out.sort(key=lambda x: x.get("published_key", ""), reverse=True)
    out = out[:max_total]
    return {
        "source": "Google Sheets article archive",
        "sheet_url": f"https://docs.google.com/spreadsheets/d/{NEWS_SHEET_ID}/edit?gid={NEWS_GID}#gid={NEWS_GID}",
        "count": len(out),
        "rows": out,
    }


def main() -> int:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    payload = {
        "generated_at_utc": now,
        "financial_archive": fetch_financial_archive(),
        "news_archive": fetch_news_archive(),
    }
    DOCS_DATA.mkdir(parents=True, exist_ok=True)
    (DOCS_DATA / "archives.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(f"wrote archives financial={payload['financial_archive']['count']} news={payload['news_archive']['count']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
