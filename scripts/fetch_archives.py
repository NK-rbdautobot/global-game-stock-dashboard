#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOCS_DATA = ROOT / "docs" / "data"
FIN_SHEET_ID = "1jzdID-ZY39VhKgHdvpSIcGiJq0Gk_qsOj1k6hNi3jh8"
NEWS_SHEET_ID = "1nA4GhaJA14_2tpHimX0-AsCpCE2G5YFySjGX79hzrCw"
MAIL_ARCHIVE_GID = "1688880659"
USER_AGENT = "Mozilla/5.0 (compatible; NK-rbdautobot-dashboard-archive/2.0)"

# Financial sheet company tabs. Nexon is intentionally excluded until its archive is cleaned.
COMPANY_TABS = {
    "알파벳": ("Alphabet (Google)", "0"),
    "마이크로소프트": ("Microsoft", "1298599699"),
    "애플": ("Apple", "1147092033"),
    "로블록스": ("Roblox", "94035846"),
    "일렉트로닉 아츠": ("Electronic Arts (EA)", "1913968735"),
    "닌텐도": ("Nintendo", "1312067933"),
    "유비소프트": ("Ubisoft", "1191027531"),
    "소니": ("Sony", "1689372210"),
    "텐센트": ("Tencent", "375664834"),
    "넷이즈": ("Netease", "1328432992"),
    "테이크투": ("Take-Two Interactive", "2108981340"),
    "엠브레이서 그룹": ("Embracer Group", "2108376821"),
    "SEA": ("SEA", "1925126558"),
    "애스피어": ("Asphere", "1981168879"),
    "크래프톤": ("크래프톤", "544177224"),
    "시프트업": ("시프트업", "1400609698"),
    "엔씨소프트": ("엔씨소프트", "522595849"),
    "넷마블": ("넷마블", "1813311314"),
    "카카오게임즈": ("카카오게임즈", "985687296"),
    "위메이드": ("위메이드", "1451002197"),
    "펄어비스": ("펄어비스", "816961723"),
    "데브시스터즈": ("데브시스터즈", "1585421687"),
    "네오위즈": ("네오위즈", "1458261925"),
    "감마니아": ("감마니아", "1033573233"),
    "라스타": ("라스타", "741525754"),
    "세기화통": ("세기화통", "1944270779"),
    "킹넷": ("킹넷", "864197942"),
    "캡콤": ("캡콤", "2030738864"),
    "반다이남코": ("반다이남코", "119289304"),
    "스퀘어에닉스": ("스퀘어에닉스", "403700134"),
    "세가": ("세가", "1291025307"),
}

COMPANY_ALIASES = {
    "알파벳": ["Alphabet", "Google", "GOOG", "구글"],
    "마이크로소프트": ["Microsoft", "MSFT", "Xbox", "Game Pass", "마이크로소프트"],
    "애플": ["Apple", "AAPL", "App Store", "애플"],
    "텐센트": ["Tencent", "0700", "텐센트", "Honor of Kings", "王者荣耀", "발로란트"],
    "넷이즈": ["NetEase", "Netease", "NTES", "넷이즈", "网易", "연운"],
    "닌텐도": ["Nintendo", "닌텐도", "Switch", "Mario", "Zelda", "Pokemon", "Pokémon", "포켓몬"],
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
    "반다이남코": ["Bandai Namco", "반다이남코", "Elden Ring", "Tekken", "건담"],
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


def parse_num(v: str) -> float | None:
    s = str(v or "").replace(",", "").replace("%", "").strip()
    if not s or s == "-":
        return None
    try:
        return float(s)
    except Exception:
        return None


def parse_company_financial(company_ko: str, tab_name: str, gid: str) -> dict[str, Any]:
    text = fetch_text(sheet_csv(FIN_SHEET_ID, gid))
    rows = list(csv.reader(io.StringIO(text)))
    while len(rows) < 9:
        rows.append([])
    max_cols = max((len(r) for r in rows), default=0)
    for r in rows:
        r.extend([""] * (max_cols - len(r)))

    q_unit = rows[1][0] if rows and rows[1] else "매출"
    op_unit = rows[2][0] if len(rows) > 2 else "영업이익"
    quarters = []
    for idx, val in enumerate(rows[4][1:], start=1):
        rev = parse_num(val)
        op = parse_num(rows[5][idx] if len(rows) > 5 and idx < len(rows[5]) else "")
        if rev is None and op is None:
            continue
        label = ""
        # Period labels in these tabs are sparse; scan nearby header cells above the value.
        for rr in [3, 0]:
            if rr < len(rows) and idx < len(rows[rr]) and rows[rr][idx].strip():
                label = rows[rr][idx].strip()
                break
        if not label:
            label = f"Q{len(quarters)+1}"
        quarters.append({"period": label, "revenue": rev, "operating_profit": op})

    years = []
    if len(rows) >= 3:
        for idx in range(11, max_cols):
            year = rows[0][idx].strip() if idx < len(rows[0]) else ""
            if not re.fullmatch(r"20\d{2}", year or ""):
                continue
            rev = parse_num(rows[1][idx] if idx < len(rows[1]) else "")
            op = parse_num(rows[2][idx] if idx < len(rows[2]) else "")
            if rev is not None or op is not None:
                years.append({"year": year, "revenue": rev, "operating_profit": op})

    links = []
    for r in rows:
        for cell in r:
            c = (cell or "").strip()
            if c.startswith("http") and c not in links:
                links.append(c)
    latest_q = quarters[-1] if quarters else {}
    latest_y = years[-1] if years else {}
    return {
        "company_ko": company_ko,
        "tab_name": tab_name,
        "gid": gid,
        "sheet_url": f"https://docs.google.com/spreadsheets/d/{FIN_SHEET_ID}/edit?gid={gid}#gid={gid}",
        "revenue_unit": q_unit,
        "operating_profit_unit": op_unit,
        "quarters": quarters[-16:],
        "years": years,
        "latest_quarter": latest_q,
        "latest_year": latest_y,
        "source_links": links[:12],
    }


def parse_date_key(s: str) -> str:
    s = (s or "").strip()
    m = re.search(r"(20\d{2})[-./]\s*(\d{1,2})[-./]\s*(\d{1,2})(?:\s+(\d{1,2}:\d{2}(?::\d{2})?))?", s)
    if m:
        y, mo, d, t = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d} {t or '00:00:00'}"
    return s


def fetch_mail_archive(limit_per_company: int = 24) -> dict[str, Any]:
    text = fetch_text(sheet_csv(NEWS_SHEET_ID, MAIL_ARCHIVE_GID))
    reader = csv.DictReader(io.StringIO(text))
    buckets: dict[str, list[dict[str, Any]]] = {k: [] for k in COMPANY_TABS}
    for r in reader:
        title_ko = (r.get("한글 제목") or "").strip()
        summary_ko = (r.get("요약") or "").strip()
        if not title_ko or not summary_ko:
            continue
        # Match only curated/visible fields, not full raw article body, to reduce false positives.
        hay = " ".join([r.get("제목", ""), title_ko, summary_ko, r.get("키워드", "")]).lower()
        for company, aliases in COMPANY_ALIASES.items():
            if company not in buckets:
                continue
            if any(a.lower() in hay for a in aliases):
                buckets[company].append({
                    "company_ko": company,
                    "title_ko": title_ko[:240],
                    "summary_ko": summary_ko[:700],
                    "original_title": (r.get("제목") or "")[:240],
                    "url": r.get("링크", ""),
                    "published_at": r.get("업로드 시간", ""),
                    "published_key": parse_date_key(r.get("업로드 시간", "")),
                    "score": r.get("종합 점수", ""),
                    "keyword": r.get("키워드", ""),
                    "integrated_note": (r.get("통합") or "")[:500],
                })
    out = []
    for company, rows in buckets.items():
        seen = set(); selected = []
        rows.sort(key=lambda x: x.get("published_key", ""), reverse=True)
        for x in rows:
            key = x.get("url") or x.get("title_ko")
            if key in seen:
                continue
            seen.add(key); selected.append(x)
            if len(selected) >= limit_per_company:
                break
        out.extend(selected)
    out.sort(key=lambda x: x.get("published_key", ""), reverse=True)
    return {
        "source": "Google Sheets Mail_Archive tab / Korean translated fields only",
        "sheet_url": f"https://docs.google.com/spreadsheets/d/{NEWS_SHEET_ID}/edit?gid={MAIL_ARCHIVE_GID}#gid={MAIL_ARCHIVE_GID}",
        "count": len(out),
        "rows": out,
    }


def main() -> int:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    companies = []
    for company_ko, (tab_name, gid) in COMPANY_TABS.items():
        try:
            companies.append(parse_company_financial(company_ko, tab_name, gid))
        except Exception as e:
            companies.append({"company_ko": company_ko, "tab_name": tab_name, "gid": gid, "error": str(e)[:300], "quarters": [], "years": [], "source_links": []})
    payload = {
        "generated_at_utc": now,
        "financial_archive": {
            "source": "Google Sheets per-company tabs; Nexon excluded until cleaned",
            "sheet_url": f"https://docs.google.com/spreadsheets/d/{FIN_SHEET_ID}/edit",
            "count": len([c for c in companies if not c.get("error")]),
            "rows": companies,
        },
        "news_archive": fetch_mail_archive(),
    }
    DOCS_DATA.mkdir(parents=True, exist_ok=True)
    (DOCS_DATA / "archives.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(f"wrote archives financial={payload['financial_archive']['count']} news={payload['news_archive']['count']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
