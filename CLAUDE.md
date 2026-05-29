# CLAUDE.md

このリポジトリで作業する際のガイド（人間にも Claude にも向けたメモ）。

## コンセプト

科研費データベース（[KAKEN](https://kaken.nii.ac.jp/)）からダウンロードした XML を読み込み、
**研究代表者ごとの科研費取得履歴を「1課題＝1本の横棒」のガントチャートにまとめた A4縦 PDF** を生成する。

- 横軸＝年度（全研究者で共通スケール）、縦に研究者ブロックを積む
- 研究者ごとに黒い横線で区切り、年度軸はページ上下の2箇所のみ
- 種目（基盤研究(C) など）で色分け
- 1人のブロックはページを跨がない（行数で見積もってから配置）

成果物は `output/kaken_gantt.pdf` の1ファイル。

## 開発環境

- Python 仮想環境（`.venv`）を必ず使う。パッケージは `.venv/bin/pip` で入れる。
  ```bash
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt   # matplotlib
  ```
- 実行：
  ```bash
  .venv/bin/python kaken_gantt.py            # 全員 → output/kaken_gantt.pdf
  .venv/bin/python kaken_gantt.py 00343187   # 研究者番号(eRad)で絞り込み
  .venv/bin/python kaken_gantt.py 鵜木        # 氏名(部分一致)で絞り込み
  ```

## 出力（PDF）の確認方法

PDF は中身を直接目視できないので、確認時は PNG に変換してから見る（変換物は `/tmp` に置き、リポジトリには残さない）。

```bash
# 1ページPDF
sips -s format png output/kaken_gantt.pdf --out /tmp/check.png
# 複数ページPDFの特定ページ（poppler / brew install poppler）
pdftoppm -png -r 80 -f 1 -l 1 output/kaken_gantt.pdf /tmp/page
```
変換時の「font type mismatch」警告は無害。

## レイアウト調整

`kaken_gantt.py` 冒頭付近の定数で変える：
`ROW_INCH`（行高＝バー太さ）/ `BAR_H`（行内のバー割合、1.0で隙間ゼロ）/ `GAP_ROWS`（研究者間の空き行）/
`LABEL_W`（左の氏名欄幅）/ `MARGIN` / `AXIS_MIN`・`AXIS_MAX`（横軸範囲、None で自動）。

## KAKEN XML の扱い（重要な落とし穴）

実データ（655課題）と公式仕様で確認済みの要点。変更時はここを壊さないこと。

- **研究者の同定は `summary/member@eradCode`（eRad 研究者番号）で行う。**
  `memberList/member` の `id="MEMBER-xxxxx"` は課題ごとのメンバー記録IDで、同一人物でも課題ごとに別IDになるため名寄せに使えない。
- 対象は研究代表者（`@role="principal_investigator"`）のみ。研究者番号の無い記録（特別研究員奨励費など）は除外。
- 研究期間は `periodOfAward` の `searchStartFiscalYear` / `searchEndFiscalYear`（ja優先）。
- `projectStatus@statusCode`：project_closed / granted / adopted / discontinued / **declined**。
  **`declined`（不採択・辞退）は獲得実績でないため除外する。**
- 種目名の全角ゆれ（`基盤研究(Ｃ)`、全角カッコ）は `normalize_category()` で正規化。
- 横軸の既定：最小＝全課題の最小開始年、最大＝最大開始年+1。終了がそれを超える課題は右端で切れる（仕様）。

公式仕様・マスタ：
- XML/JSON 定義書: <https://bitbucket.org/niijp/kaken_definition>
- マスタ（種目・審査区分など）: <https://bitbucket.org/niijp/grants_masterxml_kaken>

## データと公開の注意点

- 入力 XML（`*.xml`）は**研究者の氏名・研究者番号を含む**ため、リポジトリに含めない（`.gitignore` で `*.xml` と `output/` を除外）。
- このリポジトリは Public。**コードのみ公開し、氏名入りの生成物（PDF/PNG）は公開しない**方針。
- 可視化の性質上、研究者ごとに並べると「採択が少ない／代表経験がない（図に登場しない）」といった**評価的な含意が一目で見えてしまう**点に配慮する。
  - 表示しているのは獲得済み課題のみ（不採択は出さない）だが、**少なさ・空白は“不在”として明確に伝わる**。
  - 用途は自己分析・所属機関内の把握を想定。個人比較・評価目的での再配布は想定しない。
  - 必要なら匿名化（氏名/番号を伏せる）や集計ビュー（人を特定しない）への切り替えを検討する。
