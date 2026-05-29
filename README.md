# kaken-summary

科研費データベース（[KAKEN](https://kaken.nii.ac.jp/)）からダウンロードした XML を読み込み、
**研究代表者ごとの科研費取得履歴をガントチャート風にまとめた PDF** を生成するツールです。

- 1課題 = 1本の横棒、横軸 = 年度
- 研究者ごとにブロックを積み、黒い横線で区切り
- A4 縦・複数ページ（1人のブロックはページを跨がない）
- 種目（基盤研究(C)、挑戦的萌芽研究 など）で色分け

## 出力イメージ

各研究者について、こういった履歴が縦に並びます（年度軸はページ上下の2箇所、縦の格子線で揃う）：

```
氏名 / 研究者番号 |■ 若手研究(B) ■■■
                 |        ■ 基盤研究(C) ■■■■■
─────────────────────────────────────────────
2011 2012 2013 2014 2015 ... 2027
```

## 必要環境

- Python 3.10+
- [matplotlib](https://matplotlib.org/)
- 日本語フォント（macOS の `Hiragino Sans` などを自動利用）

## セットアップ

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## 使い方

KAKEN からダウンロードした XML をこのディレクトリに置き、スクリプト先頭の
`XML_DEFAULT` をそのファイル名に合わせるか、引数で XML パスを渡します。

```bash
# 全研究者を1つのPDF(output/kaken_gantt.pdf)に
.venv/bin/python kaken_gantt.py

# 研究者番号(eRad) または 氏名(部分一致) で絞り込み
.venv/bin/python kaken_gantt.py 00343187
.venv/bin/python kaken_gantt.py 鵜木

# 入力XMLを明示
.venv/bin/python kaken_gantt.py path/to/kaken.xml
```

出力は `output/kaken_gantt.pdf`。

## レイアウト調整

`kaken_gantt.py` 冒頭付近の定数で調整できます。

| 定数 | 意味 |
|------|------|
| `ROW_INCH` | 1課題あたりの行の高さ（バーの太さ） |
| `BAR_H` | 行内でバーが占める割合（1.0 で隙間ゼロ） |
| `GAP_ROWS` | 研究者ブロック間の空き（行数） |
| `LABEL_W` | 左の氏名・研究者番号欄の幅 |
| `MARGIN` | ページ余白 |
| `AXIS_MIN` / `AXIS_MAX` | 横軸の年度範囲（`None` でデータから自動。既定は最小開始年 〜 最大開始年+1） |

## 仕様・データの扱いに関するメモ

KAKEN 公開 XML の構造に基づき、以下のように処理しています。

- **研究者の同定は `summary/member@eradCode`（eRad 研究者番号）** で行う。
  `memberList/member` の `id="MEMBER-xxxxx"` は課題ごとのメンバー記録IDで人物単位ではないため使わない。
- 対象は研究代表者（`@role="principal_investigator"`）のみ。研究者番号の無い記録（特別研究員奨励費など）は除外。
- 研究期間は `periodOfAward` の `searchStartFiscalYear` / `searchEndFiscalYear`。
- `projectStatus@statusCode="declined"`（不採択・辞退）は獲得実績でないため除外。
- 種目名の全角ゆれ（`基盤研究(Ｃ)` など）は正規化。

公式仕様・マスタ:
- XML/JSON 定義書: <https://bitbucket.org/niijp/kaken_definition>
- マスタ（種目・審査区分などのコード一覧）: <https://bitbucket.org/niijp/grants_masterxml_kaken>

## データについて

入力の科研費 XML（`*.xml`）は研究者の氏名・研究者番号を含むため、本リポジトリには含めていません
（`.gitignore` で除外）。各自 KAKEN からダウンロードして配置してください。
