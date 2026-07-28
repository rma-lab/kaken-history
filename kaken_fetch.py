#!/usr/bin/env python3
"""KAKEN OpenSearch API から研究者ごとの全課題XMLを取得する。

機関単位の検索結果は研究者の生涯フル実績を含まない。そこで研究者番号(eRad)
ごとに KAKEN を検索し直し、全課題（代表・分担など全ロール）を
data/<機関キー>/researchers/<erad>.xml に保存する。

API仕様: https://bitbucket.org/niijp/kaken_definition
  - エンドポイント: https://kaken.nii.ac.jp/opensearch/
  - qm=研究者番号 / rw=1ページ件数(最大500) / st=開始番号(1始まり) / format=xml
  - appid が必須（CiNii API利用登録: https://support.nii.ac.jp/ja/cinii/api/developer）

使い方:
    # appid は .env の KAKEN_APP_ID から読む（環境変数でも可）
    # 機関キー指定: kaken_roster.py が作った erads.txt の全員を取得
    .venv/bin/python kaken_fetch.py jaist
    .venv/bin/python kaken_fetch.py fukushima
    # 研究者番号を指定して取得（番号の列挙 or 1行1番号のリストファイル）
    .venv/bin/python kaken_fetch.py jaist 00343187 12345678
    # 取得済みファイルも上書き
    .venv/bin/python kaken_fetch.py jaist --force
"""
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from kaken_inst import key_from_args, paths

API = "https://kaken.nii.ac.jp/opensearch/"
RW = 500                     # 1リクエストの最大件数
SLEEP = 1.0                  # リクエスト間隔（秒）。NIIに負荷をかけない


def fetch_page(appid, erad, st):
    """1ページぶん取得して (grantAward要素のリスト, 生バイト列) を返す。"""
    params = {"appid": appid, "format": "xml", "qm": erad, "rw": RW, "st": st}
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "kaken-history/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
    root = ET.fromstring(raw)
    if root.tag == "error":
        raise RuntimeError(f"APIエラー: {ET.tostring(root, encoding='unicode')}")
    # ルート直下でもネスト先でも grantAward を拾えるように iter で探す
    return list(root.iter("grantAward")), raw


def fetch_researcher(appid, erad):
    """研究者番号 erad の全課題を取得して grantAward 要素のリストを返す。"""
    awards, st = [], 1
    while True:
        page, _ = fetch_page(appid, erad, st)
        awards.extend(page)
        if len(page) < RW:      # 最終ページ（件数の事前取得に頼らずページング）
            return awards
        st += RW
        time.sleep(SLEEP)


def save(erad, awards, path):
    """grantAward のリストをエクスポートXMLと同じ <grantAwards> 形式で保存。"""
    root = ET.Element("grantAwards")
    root.extend(awards)
    ET.ElementTree(root).write(path, encoding="UTF-8", xml_declaration=True)


def load_appid():
    """appid を環境変数 KAKEN_APP_ID / KAKEN_APPID または .env から読む。"""
    for key in ("KAKEN_APP_ID", "KAKEN_APPID"):
        if os.environ.get(key):
            return os.environ[key]
    env = Path(__file__).parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            k, _, v = line.partition("=")
            if k.strip() in ("KAKEN_APP_ID", "KAKEN_APPID") and v.strip():
                return v.strip()
    return ""


def main():
    appid = load_appid()
    force = "--force" in sys.argv
    key, args = key_from_args([a for a in sys.argv[1:] if a != "--force"])
    if not appid:
        sys.exit(".env に KAKEN_APP_ID を設定してください"
                 "（取得: https://support.nii.ac.jp/ja/cinii/api/developer）")

    p = paths(key)
    erads = []
    for a in args:
        if re.fullmatch(r"\d+", a):
            erads.append(a)
        elif Path(a).is_file():               # 1行1番号のリストファイル
            erads.extend(x for x in Path(a).read_text().split()
                         if re.fullmatch(r"\d+", x))
    if not erads:                             # 既定: kaken_roster.py が作ったリスト
        if not p["erads"].is_file():
            sys.exit(f"{p['erads']} がありません。先に kaken_roster.py {key} を実行してください")
        erads = [x for x in p["erads"].read_text().split()
                 if re.fullmatch(r"\d+", x)]
    DATA_DIR = p["researchers"]
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    done = skipped = failed = 0
    for i, erad in enumerate(erads, 1):
        path = DATA_DIR / f"{erad}.xml"
        if path.exists() and not force:
            skipped += 1
            continue
        try:
            awards = fetch_researcher(appid, erad)
            save(erad, awards, path)
            done += 1
            print(f"[{i}/{len(erads)}] {erad}: {len(awards)}課題")
        except Exception as e:
            failed += 1
            print(f"[{i}/{len(erads)}] {erad}: 失敗 ({e})", file=sys.stderr)
        time.sleep(SLEEP)

    print(f"完了: 取得{done} / スキップ(取得済み){skipped} / 失敗{failed}")


if __name__ == "__main__":
    main()
