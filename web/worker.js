// KAKEN 大型科研費までの道のり Web版 — Pyodide を動かす Web Worker。
// すべてブラウザ内で完結し、アップロードされた JSON は外部に送信されない。

const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v314.0.3/full/pyodide.js";

// リポジトリ直下の分析コード（Colab/ローカルと共通のもの）
const PY_FILES = [
  "kaken_inst.py",
  "kaken_data.py",
  "kaken_json.py",
  "kaken_gantt.py",
  "kaken_stepup.py",
  "kaken_report.py",
  "kaken_stepup_gantt.py",
  "kaken_nolarge_gantt.py",
];

let pyodidePromise = null;

const log = (msg) => postMessage({ type: "log", msg });
const status = (msg) => postMessage({ type: "status", msg });

async function fetchBytes(path, base) {
  const res = await fetch(new URL(path, base));
  if (!res.ok) throw new Error(`${path} の取得に失敗しました (HTTP ${res.status})`);
  return new Uint8Array(await res.arrayBuffer());
}

async function init(base) {
  status("Python 実行環境を読み込み中…（初回のみ約30MB、2回目以降はキャッシュ）");
  importScripts(PYODIDE_URL);
  const py = await loadPyodide({
    stdout: (s) => log(s),
    stderr: (s) => log(s),
  });
  status("グラフ描画ライブラリ（matplotlib）を読み込み中…");
  await py.loadPackage("matplotlib");

  status("分析コードと日本語フォントを取得中…");
  for (const f of PY_FILES) {
    py.FS.writeFile("/home/pyodide/" + f, await fetchBytes(f, base));
  }
  py.FS.writeFile("/home/pyodide/web_runner.py", await fetchBytes("web/runner.py", base));
  py.FS.mkdirTree("/fonts");
  py.FS.writeFile("/fonts/ipag.ttf", await fetchBytes("web/fonts/ipag.ttf", base));
  return py;
}

onmessage = async (e) => {
  const d = e.data;
  try {
    if (d.type === "init") {
      pyodidePromise = init(d.base);
      await pyodidePromise;
      postMessage({ type: "ready" });
    } else if (d.type === "run") {
      const py = await pyodidePromise;
      status("データを配置中…");
      py.FS.mkdirTree("/home/pyodide/data/target");
      py.FS.writeFile(
        "/home/pyodide/data/target/researchers.json",
        new Uint8Array(d.buffer)
      );
      status("集計と PDF 生成を実行中…（1〜2分かかることがあります）");
      py.globals.set("_label", d.label || "");
      const result = await py.runPythonAsync(
        "import web_runner\nweb_runner.run(_label)"
      );
      const paths = result.toJs();
      result.destroy();
      const pdfs = paths.map((path) => {
        const bytes = py.FS.readFile("/home/pyodide/" + path);
        return { name: path.split("/").pop(), buffer: bytes.buffer };
      });
      postMessage({ type: "done", pdfs }, pdfs.map((p) => p.buffer));
    }
  } catch (err) {
    postMessage({ type: "error", msg: String((err && err.message) || err) });
  }
};
