import json

def md(*lines):
    return {"cell_type": "markdown", "metadata": {}, "source": list(lines)}

def code(*lines):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": list(lines)}

cells = []

# =====================================================================
# タイトル
# =====================================================================
cells.append(md(
"# qchem_colab_app v0.1.1 — 量子化学計算プロトタイプ (HF / 3-21G)\n",
"\n",
"Google Colab上で構造最適化・振動数計算を行うプロトタイプです。\n",
"ColabReaction ( https://github.com/BILAB/ColabReaction ) と同様、\n",
"**上から順にセルを実行**していく構成になっています。\n",
"\n",
"- **I. Setup Section** — 環境構築(このプロトタイプのコードとライブラリの準備)\n",
"- **II. Execution Section** — 実際の計算画面(GUI)\n",
"\n",
"初めてJupyter/Colabを使う方へ: 各コードセルの左側にマウスを合わせると再生ボタン(▶)が\n",
"表示されます。それをクリックするか、セルを選択して `Shift+Enter` を押すと、そのセルが実行されます。\n",
"**必ず上のセルから順番に**実行してください(途中を飛ばすとエラーになります)。"
))

# =====================================================================
# I. Setup Section
# =====================================================================
cells.append(md(
"## I. Setup Section\n",
"\n",
"### 0. (推奨) Colabのランタイムバージョンを固定する\n",
"\n",
"上部メニューの **「ランタイム」→「ランタイムのタイプを変更」** を開き、\n",
"**Runtime version** のプルダウンから特定のバージョン(例: `2026.07`)を選択してください。\n",
"これにより、Googleが将来Colabの基盤(Python本体やnumpy等)を更新しても、\n",
"このノートブックの動作が変わらないようにできます\n",
"(公式情報: https://research.google.com/colaboratory/runtime-version-faq.html )。\n",
"\n",
"未設定のまま進めても動作はしますが、「今日動いたのに来月動かなくなった」を防ぐため、\n",
"公開版として配布する際は設定を強く推奨します。"
))

cells.append(code(
"# 現在のPython/OS環境を確認しておきます(トラブルシューティング時の記録用)\n",
"!python --version\n",
"!lsb_release -d 2>/dev/null || cat /etc/os-release | head -1"
))

cells.append(md(
"### 1. コード本体の取得(GitHubから)\n",
"\n",
"このプロトタイプのコードは https://github.com/orgchem610/qchem_colab_app で管理しています。\n",
"以後、コードの変更は**すべてこのGitHubリポジトリ経由**で反映します。\n",
"下のセルは、まだクローンしていなければ `git clone` を、既にクローン済みなら\n",
"最新版を取得する `git pull` を自動で行います。"
))

cells.append(code(
"import os\n",
"\n",
"GITHUB_USER = \"orgchem610\"\n",
"GITHUB_REPO = \"qchem_colab_app\"\n",
"PROJECT_DIR = f\"/content/{GITHUB_REPO}\"\n",
"\n",
"if not os.path.exists(PROJECT_DIR):\n",
"    print(f\"{GITHUB_REPO} をクローンします...\")\n",
"    !git clone https://github.com/{GITHUB_USER}/{GITHUB_REPO}.git {PROJECT_DIR}\n",
"else:\n",
"    print(f\"{PROJECT_DIR} は既に存在するため、最新版を取得します(git pull)...\")\n",
"    !cd {PROJECT_DIR} && git pull\n",
"\n",
"# 特定のバージョン(タグ)を明示的に使いたい場合は、上のセル実行後に\n",
"# 以下のようなセルを追加して実行してください(例: v0.1.0固定)。\n",
"# !cd $PROJECT_DIR && git checkout v0.1.0"
))

cells.append(code(
"import sys\n",
"if PROJECT_DIR not in sys.path:\n",
"    sys.path.append(PROJECT_DIR)\n",
"print(\"sys.pathに追加しました:\", PROJECT_DIR)"
))

cells.append(md(
"### 2. 依存ライブラリのインストール\n",
"\n",
"「バージョンを固定して将来にわたり動作を変えない」という方針に沿い、\n",
"`requirements-lock.txt` が既にあればそちらを、なければ `requirements.txt` を使って\n",
"インストールします。**初回実行後、`requirements-lock.txt` が自動生成されます。**\n",
"それをGit管理下に置いてコミットしておくと、以後は全く同じ組み合わせを再現できます\n",
"(詳細は `README.md` / `CHANGELOG.md` 参照)。\n",
"\n",
"パッケージを1つずつインストールし、途中で失敗したものがあれば\n",
"**どのパッケージが・どんなエラーで失敗したか**が分かるように表示します\n",
"(1本の `pip install -r ...` だけだと、どれが原因か分かりにくいためです)。"
))

cells.append(code(
"import os\n",
"import subprocess\n",
"\n",
"req_lock = os.path.join(PROJECT_DIR, \"requirements-lock.txt\")\n",
"req_plain = os.path.join(PROJECT_DIR, \"requirements.txt\")\n",
"req_file = req_lock if os.path.exists(req_lock) else req_plain\n",
"print(f\"インストールに使用するファイル: {req_file}\")\n",
"\n",
"with open(req_file) as f:\n",
"    lines = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith(\"#\")]\n",
"\n",
"failed = []\n",
"for pkg in lines:\n",
"    print(f\"--- installing: {pkg} ---\")\n",
"    result = subprocess.run(\n",
"        [\"pip\", \"install\", \"-q\", pkg], capture_output=True, text=True)\n",
"    if result.returncode != 0:\n",
"        failed.append(pkg)\n",
"        print(f\"❌ {pkg} のインストールに失敗しました。エラー末尾:\")\n",
"        print(\"\\n\".join(result.stderr.strip().splitlines()[-15:]))\n",
"    else:\n",
"        print(f\"OK: {pkg}\")\n",
"\n",
"if failed:\n",
"    print(\"\\n=== 以下のパッケージのインストールに失敗しました ===\")\n",
"    for pkg in failed:\n",
"        print(\" -\", pkg)\n",
"    print(\n",
"        \"\\n上のエラー内容(特に最後の数行)を確認してください。\\n\"\n",
"        \"よくある原因は「そのパッケージがこのPythonバージョン用のビルド済み\\n\"\n",
"        \"パッケージ(wheel)を提供しておらず、ソースからのビルドに失敗している」\\n\"\n",
"        \"ことです。README.md のトラブルシューティング、または表示された\\n\"\n",
"        \"パッケージ名とエラー内容をそのままご連絡ください。\"\n",
"    )\n",
"else:\n",
"    print(\"\\n全てのパッケージのインストールに成功しました。\")"
))

cells.append(code(
"# ---- GPU4PySCFの導入を試みる(ベストエフォート) ----\n",
"# 失敗しても後続処理には影響しません(qcapp/engine.pyが自動的にCPU実行へフォールバックします)。\n",
"import subprocess\n",
"\n",
"try:\n",
"    # CPUのみのランタイムでは nvidia-smi コマンド自体が存在せず、\n",
"    # (存在すればreturncodeで判定できるはずが)FileNotFoundErrorが送出されるため、\n",
"    # 明示的に捕捉してGPUなし判定にフォールバックする。\n",
"    gpu_available = subprocess.run([\"nvidia-smi\"], capture_output=True).returncode == 0\n",
"except FileNotFoundError:\n",
"    gpu_available = False\n",
"if gpu_available:\n",
"    print(\"GPUランタイムが検出されました。GPU4PySCFのインストールを試みます...\")\n",
"    # CUDA12系ランタイムを想定した既定のパッケージ名です。\n",
"    # 導入に失敗する場合は、Colabの「ランタイム」→「ランタイムのタイプを変更」で\n",
"    # 表示されているCUDAバージョンを確認し、gpu4pyscf-cuda11x 等に読み替えてください。\n",
"    ret = subprocess.run([\"pip\", \"install\", \"-q\", \"gpu4pyscf-cuda12x\"], capture_output=True)\n",
"    if ret.returncode == 0:\n",
"        print(\"GPU4PySCFのインストールに成功しました。\")\n",
"    else:\n",
"        print(\"GPU4PySCFのインストールに失敗しました。CPUで計算を続行します。\")\n",
"        print(ret.stderr.decode()[-800:])\n",
"else:\n",
"    print(\"GPUランタイムが検出されませんでした(ランタイムのタイプがCPUのままか、GPU割り当てがありません)。\")\n",
"    print(\"CPUで計算を実行します。GPUを使いたい場合は「ランタイム」→「ランタイムのタイプを変更」から\")\n",
"    print(\"ハードウェアアクセラレータをGPU(T4等)に変更し、このSetup Sectionを最初から再実行してください。\")"
))

cells.append(code(
"# 今回、実際にインストールされたバージョン一式を requirements-lock.txt として\n",
"# 記録します。Colabの pip freeze はプリインストール済みの大量のパッケージ\n",
"# (700個以上)も含めてしまい、それをそのまま使うと次回以降のインストールが\n",
"# 非常に遅くなるため、requirements.txt に明示的に書かれているパッケージと\n",
"# GPU4PySCF関連パッケージだけに絞って書き出す(理由の詳細はREADME.md\n",
"# 「requirements-lock.txtを軽量に保つ理由」参照)。\n",
"import re\n",
"import subprocess\n",
"\n",
"freeze_result = subprocess.run([\"pip\", \"freeze\"], capture_output=True, text=True)\n",
"all_lines = freeze_result.stdout.splitlines()\n",
"\n",
"with open(os.path.join(PROJECT_DIR, \"requirements.txt\")) as f:\n",
"    wanted_names = set()\n",
"    for line in f:\n",
"        line = line.strip()\n",
"        if line and not line.startswith(\"#\"):\n",
"            name = re.split(r\"[<>=!~\\[]\", line)[0].strip().lower()\n",
"            wanted_names.add(name)\n",
"\n",
"def _pkg_name(line):\n",
"    return re.split(r\"[<>=!~\\[ @]\", line)[0].strip().lower()\n",
"\n",
"filtered_lines = [\n",
"    line for line in all_lines\n",
"    if _pkg_name(line) in wanted_names or _pkg_name(line).startswith(\"gpu4pyscf\")\n",
"]\n",
"\n",
"lock_path = os.path.join(PROJECT_DIR, \"requirements-lock.txt\")\n",
"with open(lock_path, \"w\") as f:\n",
"    f.write(\"\\n\".join(sorted(filtered_lines)) + \"\\n\")\n",
"\n",
"print(f\"requirements-lock.txt を書き出しました({len(filtered_lines)}パッケージ分)。\")\n",
"print(\"ダウンロードしてGitにコミットすることを推奨します。\")\n",
"for line in sorted(filtered_lines):\n",
"    print(\" -\", line)\n",
"\n",
"import importlib\n",
"pyscf = importlib.import_module(\"pyscf\")\n",
"print(\"\\nインストールされた pyscf のバージョン:\", pyscf.__version__)"
))

cells.append(md(
"### 3. 動作確認用サンプル構造の準備(任意)\n",
"\n",
"初めて実行する方は、いきなりご自身の分子(70原子級など)を試す前に、\n",
"下のセルで作成される小さなサンプル(エタノール, 9原子, C・H・Oのみ)で\n",
"一度パイプライン全体(構造最適化→振動数計算)が正常に動くことを確認することを強く推奨します。"
))

cells.append(code(
"sample_xyz = \"\"\"9\n",
"Ethanol (CH3CH2OH) - rough starting geometry for connectivity testing\n",
"C   0.000000   0.000000   0.000000\n",
"C   1.510000   0.000000   0.000000\n",
"O   1.970000   1.340000   0.000000\n",
"H  -0.363000   0.000000   1.028000\n",
"H  -0.363000  -0.890000  -0.514000\n",
"H  -0.363000   0.890000  -0.514000\n",
"H   2.020000  -0.360000   0.890000\n",
"H   2.020000  -0.360000  -0.890000\n",
"H   1.445000   2.144000   0.000000\n",
"\"\"\"\n",
"with open(\"/content/sample_ethanol.xyz\", \"w\") as f:\n",
"    f.write(sample_xyz)\n",
"print(\"/content/sample_ethanol.xyz を作成しました。\")\n",
"print(\"下の実行画面のアップロード欄でこのファイルを選択して、まず動作確認することをお勧めします。\")\n",
"print(\"(Colab左側のフォルダアイコンから /content 内のファイルとして参照できます)\")"
))

# =====================================================================
# II. Execution Section
# =====================================================================
cells.append(md(
"## II. Execution Section\n",
"\n",
"以下のセルを実行すると操作画面が表示されます。\n",
"\n",
"1. 「① 構造ファイルと計算条件」で `.xyz` ファイルをアップロードし、条件を設定\n",
"2. 「② 実行」の **「計算を実行する」** ボタンを押す\n",
"3. ログに構造最適化・振動数計算それぞれの所要時間と、合計時間が表示されます\n",
"4. 「③ 可視化」でエネルギー推移・軌跡・振動アニメーション・分子軌道・電荷密度を確認\n",
"5. 「④ ダウンロード」から最終構造(ColabReactionにそのまま渡せる.xyz)・\n",
"   トラジェクトリ・moldenファイルを取得\n",
"\n",
"**条件を変えて再実行したい場合は、このセルをもう一度実行し直してください\n",
"(GUI部品が再生成され、状態がリセットされます)。**"
))

cells.append(code(
"import gui\n",
"from IPython.display import display\n",
"\n",
"app = gui.build_app()\n",
"display(app)"
))

nb = {
    "cells": cells,
    "metadata": {
        "colab": {"name": "ColabApp.ipynb", "provenance": []},
        "kernelspec": {"display_name": "Python 3", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

out_path = "/home/claude/qchem_colab_app/ColabApp.ipynb"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("wrote", out_path)
