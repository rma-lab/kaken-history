#!/usr/bin/env python3
"""KAKEN「研究者をさがす」(nrid.nii.ac.jp) の JSON エクスポートを読み込む。

このJSONは研究者(人)単位で、各研究者の中に生涯の全課題(work:project)が入る。
機関検索XMLのように他機関時代の課題が欠けることがなく、KAKEN OpenSearch API
（appid必須）で研究者ごとに全件取得し直す必要をなくす。実データで検証済み:
既存のAPI方式ロスターを完全に被覆し、所要年数の集計も一致する。

返すデータ構造は XML 版（kaken_gantt.parse / kaken_stepup.pi_projects）と互換:
    {"erad", "name", "yomi", "projects": [{category, start, end,
                                            award_number, status, project_type}]}
projects は PI（研究代表者）の課題のみ・declined 除外・開始年順。

エクスポート手順（appid不要）:
    KAKEN「研究者をさがす」で研究機関=自機関を検索 → Select All → Export in JSON。
    ※1回のエクスポート上限は1万件。研究者数がそれを超える巨大機関は分割が必要。
"""
import json

from kaken_gantt import EXCLUDE_STATUS, PI_ROLE, normalize_category

# JSON のロールコード。XML の member@role と同じ語彙。
AREA_ORGANIZER_ROLE = "area_organizer"   # 領域代表（XMLの projectType="organizer" 相当）


def _text(arr, lang="ja"):
    """humanReadableValue 等の配列から指定言語の text を拾う（無ければ先頭）。"""
    fallback = ""
    for hv in arr or []:
        if hv.get("lang") == lang:
            return hv.get("text") or ""
        if not fallback:
            fallback = hv.get("text") or ""
    return fallback


def _year(node):
    """since / until / projectStatus の fiscal:year/commonEra:year を int で返す。"""
    if not node:
        return None
    y = (node.get("fiscal:year") or {}).get("commonEra:year")
    return int(y) if y else None


def _pi_projects(researcher):
    """1研究者JSONから PI 課題を (開始年順で) 返す。pi_projects(XML) と同じ形。"""
    projects = []
    for p in researcher.get("work:project") or []:
        status = (p.get("projectStatus") or {}).get("statusCode") or ""
        if status in EXCLUDE_STATUS:                 # declined（不採択/辞退）は除外
            continue
        roles = {r.get("code:roleInProject:kakenhi") for r in (p.get("role") or [])}
        if PI_ROLE not in roles:                     # PI（研究代表者）の課題のみ
            continue
        start = _year(p.get("since"))
        if not start:
            continue
        cats = p.get("category") or []
        cat = normalize_category(_text(cats[0].get("humanReadableValue")) if cats else "")
        num = (p.get("recordSource") or {}).get("id:project:kakenhi")
        if isinstance(num, list):
            num = num[0] if num else ""
        projects.append({
            "category": cat,
            "start": start,
            "end": _year(p.get("until")) or start,
            "award_number": num or "",
            "status": status,
            # 領域代表なら "organizer"（XML版 is_large の project_type 判定に合わせる）
            "project_type": "organizer" if AREA_ORGANIZER_ROLE in roles else "",
        })
    projects.sort(key=lambda p: p["start"])
    return projects


def load(json_path):
    """研究者JSONを読み、研究者dictのリストを返す（XML版と互換の構造）。"""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    researchers = []
    for r in data.get("researchers", []):
        erad = (r.get("id:person:erad") or [None])[0]
        if not erad:                                 # 研究者番号の無い記録は対象外
            continue
        name_hv = (r.get("name") or {}).get("humanReadableValue")
        researchers.append({
            "erad": str(erad),
            "name": _text(name_hv, "ja"),
            "yomi": _text(name_hv, "ja-Kana"),
            "projects": _pi_projects(r),
        })
    return researchers
