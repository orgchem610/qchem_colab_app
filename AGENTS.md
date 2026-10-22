# AGENTS.md

このリポジトリの開発・保守のための管理文書。コードを読む・書く人(AIエージェントを含む)向けに、
作業のルール、設計の方針、今後の予定、バージョン管理・ブランチ運用、ディレクトリ構成、
各モジュール・関数の仕様(末尾の「仕様書」)を、このファイル1つにまとめている。

**このファイルには、現在の状態と、今後行うべきことだけを書く。過去の経緯(変更の履歴、検討して見送った案とその比較、
不具合の原因調査の記録、旧名称との対応)は書かない。** 変更の履歴は、Gitのコミット・マージコミット・タグ・GitHubのReleasesに残る。
内容を変えるときは、古い記述を残さず、現在の状態に書き換える。

**`main`ブランチではGit管理の対象外、`develop`・`feature/*`ブランチではGit管理の対象**にしている
(運用は、「`AGENTS.md`のGit管理」の節を参照)。`main`には存在しないため、`README.md`・`tests/`・
ソースコードからは、このファイルを参照しない(参照すると、`main`でテストが失敗する)。
`develop`・`feature/*`はGitHubにpushされるため、GitHubが公開リポジトリの場合、そのブランチ上のこのファイルは
第三者にも読める。パスワード・トークン・個人情報は、書かない。

## 作業のルール

- ソースコードを変更するときは、同時に、このファイル末尾の「仕様書」(各モジュールと関数の仕様[引数・戻り値・目的・呼出先・呼出元]・
  テストの対象)、上の「ディレクトリ構成」、`README.md`も更新する(`README.md`は利用者向けの内容だけ。
  実装に関するメモは、このファイルに書く)。仕様書の書き方は、「仕様(モジュールと関数)」の冒頭を参照する。
- **修正が必要なテストを探すときは、変更した項目の「関連テスト」を見る**(`python3.12 tests/spec_analysis.py --fix`で、最新にしてから)。
  このリポジトリで定義しているクラス(`Structure`・`FrequencyResult`・`OptimizationResult`など)の代用品には、`SimpleNamespace`ではなく、
  実物のクラスを使う(属性だけを真似る代用品は、属性名の変更や削除が、関連テストから見つからず、テストが古いまま残るため)。
  `gui`・`common_backend`のテストでは、エンジンのパッケージをimportしないため、共通の親クラス(`common_backend.optimization.OptimizationResult`等)を使う。
  外部ライブラリのオブジェクト(PySCFのMole・SCF、ASEのAtoms、py3Dmol、ipywidgetsのFileUpload、torchなど)も、実物を使う
  (外部ライブラリの版が上がって、属性名や戻り値の形が変わったときに、代用品だと、テストが通ったまま、実機で初めて壊れるため。
  実際に、実物のPySCFで確認して、虚振動が検出されない誤りが見つかった)。小さな分子・SCFの結果は、`tests/real_molecules.py`を使う
  (どれも1秒未満)。ライブラリが入っていない環境では、`@unittest.skipUnless(real_molecules.HAS_...)`で、そのテストだけをスキップする。
  代用品を使ってよいのは、実物では作れないときだけ(今のライブラリが作らない形の値、実際には起こらない値、Hugging Faceへの接続・
  モデルのダウンロード・GPUが必要なもの)。使うときは、テストファイルの冒頭の説明に、理由を書く。
- パッケージの依存の向きは、`gui` → `pyscf_backend`・`uma_backend` → `common_backend`(一方向)。`pyscf_backend/`と
  `uma_backend/`は、お互いをimportしない。バックエンド(`common_backend`・`pyscf_backend`・`uma_backend`)は、`gui`・
  `ipywidgets`・`IPython`をimportしない。`gui`の共通部品(`parts`など)は、`pyscf_backend`・`uma_backend`をimportしない。
  すべて`tests/test_package_layering.py`で検査する。新しいパッケージを足すときは、このテストの`LAYERS`に、許す依存先を書く。
  新しい画面モジュールを足すときは、`GUI_SCREENS`に、その画面が呼んでよい計算エンジンを書く。
- 再エクスポート(他のモジュールの名前を、別のパッケージの名前としても公開すること)はしない。他のモジュールの名前は、定義元から直接importする
  (`load_yaml`は`common_backend.config_loader`から、`__version__`は`common_backend.version`から)。各パッケージの`__init__.py`は、説明だけを書き、
  何もimportしない(`tests/test_package_layering.py`が検査する)。
- このファイルでは、最上位パッケージ名`qchem_colab_app`を省略して、`gui.parts`・`pyscf_backend.pipeline`のように書く
  (実際の`import`は、`from qchem_colab_app.gui import parts`の形)。
- 命名: 最上位パッケージは、プロジェクト固有の名前`qchem_colab_app`を1つだけ置く(`gui`・`common`のような一般的な名前は、
  他のライブラリと衝突しうるため、最上位に置かない)。計算エンジンのパッケージは`<エンジン>_backend`、画面のモジュールは
  `gui/<エンジン>_screen.py`、config/のYAMLを読む共通モジュールは`common_backend/config_loader.py`とする。
  モジュール名は短い名詞(役割を表す)にし、動作を表す動詞句は関数名にする。
- PySCF版とUMA版で似たコードがあっても、将来それぞれ独立に変えていく可能性があるものは、無理に共通化しない。
  - 共通化しているもの: 電荷・スピン多重度の入力欄、構造の読み込みと検証、最適化の標準出力2ファイルとダウンロード項目、
    ダウンロード名の既定値、設定の読み込み(`common_backend.config_loader.load_yaml`)と`__version__`(`common_backend.version`)、
    エネルギーの単位換算(`common_backend.energy`)、cubeファイルの読み取り(`common_backend.cube`)、
    振動数解析の数値計算と結果の入れ物(`common_backend.vibration`。数値計算を使うのは現在UMA版だけ。`FrequencyResult`は両方が使い、
    PySCF版は子クラスで熱力学量の項目を足す)、
    最適化の結果の入れ物(`common_backend.optimization`。`OptimizationResult`は両方が使い、PySCF版・UMA版は子クラスでエンジン固有の項目を足す)、元素のデータ(`common_backend.elements`)、GPUの判定(`common_backend.runtime`)、
    ASEのAtomsへの変換(`common_backend.ase_bridge`)、原子電荷の描画(`gui.plot_common`)。
    1か所からしか呼ばれていなくても、特定のエンジンに依存しない部品は、共通のパッケージに置く方針である。
  - 独立のまま残しているもの: エラー表示の`except`の連鎖、進捗・ログの文面、計算の流れの結果クラス(`CalculationResult`)、
    設定ファイル(`defaults.yaml`・`uma_defaults.yaml`)、扱える元素の範囲、ノートブックの「1-a〜1-c」セル(リポジトリ取得前に動くため)。
- `AGENTS.md`は、`develop`・`feature/*`では追跡し、`main`では追跡しない。Claudeが`main`へのマージの手順を案内するときは、
  必ず「`AGENTS.md`のGit管理」と「`main`ブランチへのリリース(マージ)の手順」の4(`--no-ff --no-commit`でマージ →
  `git rm --cached --ignore-unmatch AGENTS.md` → 確認 → コミット)を含める。
- 新しいタグを打つ前に、単体テストを通し、Colab実機で動作を確認する(単体テストでは、PySCF・fairchem・
  Colab上のJavaScript連携は確認できない)。Colab実機では、`import qchem_colab_app`が、リポジトリ直下の`qchem_colab_app/`から
  読まれることも確認する(ノートブックが、リポジトリのフォルダを`sys.path`に追加するため)。
- GitHubのリポジトリは`orgchem610/qchem_colab_app`のみを対象にする。履歴を消す操作(強制プッシュ等)はしない。

## 開発・動作確認の進め方

コードの作成と単体テストは、利用者のMacの仮想環境(下の「ローカルの開発環境」)と、Claudeのサンドボックス(PyPIからライブラリを
入れられる)で行う。PySCF・ASE・py3Dmol・geomeTRIC・ipywidgetsは、実物を使って確認できる。UMAのモデルの実際の読み込みと推論
(Hugging Faceのトークンが必要)、GPU(GPU4PySCF・CUDA)、Google Colab実機でのJavaScript連携(ドラッグ&ドロップ・グラフのクリック)は、
単体テストでは確認できないため、リリース前にColab実機で確認してから、タグを打つ。単体テストで確認できる範囲は`tests/`にある。

### ローカルの開発環境(利用者のMac)

- OS・CPU: macOS(Darwin)、Apple silicon(arm64)。NVIDIAのGPUはないため、GPU4PySCFは入れていない
- Python: 3.12.15。実行コマンドは`python3.12`(`python3`ではない)
- 仮想環境: プロジェクトルート直下の`.venv/`(Gitの管理外)。有効にするコマンドは`source .venv/bin/activate`
  (有効にすると、プロンプトの先頭に`(.venv)`が付く)
- 主なライブラリの版(2026-10-22に確認): ase 3.29.0、fairchem-core 2.23.0、geometric 1.1.1、ipython 9.17.1、ipywidgets 8.1.9、
  numpy 2.4.6、py3Dmol 2.5.5、pyscf 2.14.0、PyYAML 6.0.3、scipy 1.18.1、torch 2.13.0。版が変わったら、ここを更新する
  (確認のコマンド: `python3.12 -m pip list`)
- 単体テストの実行: `python3.12 -m unittest discover -s tests -p "test_*.py"`(1分以内)。仕様書の更新: `python3.12 tests/spec_analysis.py --fix`
- このファイルは、GitHubにも送られるため、ユーザー名を含むフォルダの絶対パス・トークン等は書かない

## ディレクトリ構成(各ファイルの役割)

```
qchem_colab_app/
├── ColabApp.ipynb              # PySCF版ノートブック(Setup Section / Execution Section)
├── ColabApp_UMA.ipynb           # UMA版ノートブック(ランタイム 2026.07・T4 GPUが記録済み)
├── README.md                     # 利用者向けの説明
├── AGENTS.md                       # 開発・保守の管理文書(作業のルール・設計の方針・仕様書)。develop・feature/*だけで追跡し、mainでは追跡しない
├── THIRD_PARTY_NOTICES.md         # UMA版が利用する外部ソフトウェア・データのライセンスへのリンク
├── requirements.txt               # PySCF版の依存パッケージのバージョン指定(初回インストール用の目安)
├── requirements-uma.txt            # UMA版の依存パッケージ(PySCFは使わない)
├── requirements-lock.txt           # Colab実行時に自動生成される「動作確認済み」の正確な記録。mainブランチだけGit管理
├── requirements-uma-lock.txt        #   (同上。UMA版。他のブランチでは.gitignoreの対象で、存在しない)
├── .gitignore
├── .githooks/                  # mainにAGENTS.mdを入れないためのgitフック(全ブランチで追跡。使うには、クローンごとに設定が必要)
│   ├── check-agents.sh           # 検査の本体(main上でAGENTS.mdが追跡されていれば失敗)
│   ├── pre-commit                # コミット前に、check-agents.shを呼ぶ
│   ├── pre-merge-commit          # マージのコミット前に、check-agents.shを呼ぶ
│   └── pre-push                  # main・タグへのpushにAGENTS.mdが含まれていれば、pushを中止する
├── config/
│   ├── purposes.yaml         # 計算目的の選択肢(現在: 構造最適化のみ)
│   ├── functionals.yaml      # 計算手法の選択肢(HF, B3LYP)
│   ├── basis_sets.yaml       # 基底関数の選択肢(3-21G, 6-31G, 6-31G*, 6-31G**)
│   ├── defaults.yaml         # 電荷・多重度・収束条件などの既定値(PySCF版)
│   ├── uma_defaults.yaml     # UMA版の既定値(最適化の収束条件・振動数計算の刻み幅など)
│   └── uma_models.yaml       # UMA版で選べるモデルの一覧
├── qchem_colab_app/             # 最上位パッケージ(名前空間。下の4つのパッケージを入れる。ここ以外には、.pyファイルを置かない)
│   ├── __init__.py                 # パッケージの説明だけ(何もimportしない)
│   ├── common_backend/             # バックエンドの共通部品(画面にも計算エンジンにも依存しない。PySCF版・UMA版の両方が使う)
│   │   ├── __init__.py
│   │   ├── config_loader.py          # config/のYAMLの読み込み(pyscf_backend・uma_backendの両方が使う)
│   │   ├── cube.py                    # cubeファイルの値の読み取り(PySCFに依存しない)
│   │   ├── elements.py                # 元素のデータ(元素記号→原子番号。H〜Xe)
│   │   ├── runtime.py                  # GPUの判定(nvidia-smi・torch.cuda)
│   │   ├── ase_bridge.py               # 共通の構造→ASEのAtoms
│   │   ├── version.py                 # バージョン番号(__version__。リポジトリ全体で1か所だけ)
│   │   ├── io_reader.py             # 構造ファイルの読み込み・入力バリデーション
│   │   ├── writer_xyz.py             # xyz出力(単一構造・多フレーム・最適化の標準出力2ファイル)
│   │   ├── energy.py                  # エネルギーの単位換算(Hartree・eV・kcal/mol)・相対エネルギー(バックエンドと画面の両方が使う)
│   │   ├── optimization.py             # 構造最適化の結果の入れ物(OptimizationResult。PySCF版・UMA版の共通の親クラス。エンジンに依存しない)
│   │   └── vibration.py                # 振動数解析の数値計算(中心差分のHessian・並進回転を除いた調和解析・ZPE。純粋なnumpy)
│   ├── gui/                        # 画面の層(ipywidgets・ColabのJavaScript連携・3D表示・SVGグラフ)
│   │   ├── __init__.py               # 説明だけ(何もimportしない)
│   │   ├── colab_widgets.py            # ブラウザ側JavaScript ↔ Colabのコールバック(ドロップ領域・コールバック登録)
│   │   ├── energy_plot.py                # クリックできるエネルギー収束グラフ(SVG)と、目盛りの計算
│   │   ├── plot_common.py             # 構造・振動アニメーション・原子電荷の3D表示(py3Dmol)と、電荷の表
│   │   ├── inputs.py                  # 画面の入力まわりの関数(アップロードされたファイルの取り出し・読み込みと検証・電荷の表示と読み取り)
│   │   ├── outputs.py                 # 画面の出力まわりの関数(ダウンロード名・ダウンロード項目)
│   │   ├── parts.py                   # 共通の画面部品(ファイル入力・グラフ+構造表示・振動・ダウンロード・電荷入力・スピン多重度入力)
│   │   ├── pyscf_screen.py             # PySCF版の画面(ColabApp.ipynbから呼ぶ。pyscf_backendを呼び出す)
│   │   └── uma_screen.py               # UMA版の画面(ColabApp_UMA.ipynbから呼ぶ。uma_backendを呼び出す)
│   ├── pyscf_backend/                     # PySCFを計算エンジンとするab initio計算専用(uma_backendからは呼ばない)
│   │   ├── __init__.py               # パッケージの説明だけ(何もimportしない。別名・再エクスポートは置かない)
│   │   ├── analysis_pyscf.py          # 分子軌道の選択肢(HOMO/LUMO/SOMO)・Mulliken電荷など、SCF結果からの情報の取り出し
│   │   ├── engine.py                  # Mole構築・SCF実行(GPU4PySCF自動フォールバック含む)
│   │   ├── optimize.py                 # geomeTRICによる構造最適化
│   │   ├── pipeline.py                 # PySCF版の計算の流れ(最適化→CPU再計算→振動数→出力ファイル)。GUI・ファイル入力に依存しない
│   │   ├── freq.py                      # Hessian・振動数解析
│   │   ├── writer_molden.py              # moldenファイル出力
│   │   └── visualizer_pyscf.py            # 分子軌道の等値面(PySCFのMole・SCFに依存する可視化)
│   └── uma_backend/                   # UMA(機械学習ポテンシャル)専用(pyscf_backendには依存しない)
│       ├── __init__.py               # パッケージの説明だけ(何もimportしない。別名・再エクスポートは置かない)
│       ├── uma_hf.py                   # Hugging Faceのトークン・アクセス確認、UmaSetupError
│       ├── uma_engine.py              # モデルの読み込み、計算デバイスの判定、ASEのAtoms/Calculator
│       ├── uma_optimize.py             # ASE(LBFGS等)+UMAによる構造最適化
│       ├── uma_pipeline.py             # UMA版の計算の流れ(アクセス確認→モデル→最適化→振動数→出力ファイル)。GUI・ファイル入力に依存しない
│       ├── uma_freq.py                  # UMAの力から数値Hessianを作る振動数解析(数値計算の本体はcommon_backend/vibration.py)
│       ├── uma_notice.py                  # UMAのライセンス・引用の一次情報へのリンク
│       └── uma_report.py                   # 計算ログの組み立て
└── tests/
    ├── test_io_reader.py / test_config.py / test_visualizer.py   # 入力・設定・分子軌道の可視化(PySCF非依存部分)
    ├── test_cube.py                  # cubeファイルの値の読み取り(common_backend)
    ├── test_plot_common.py          # 原子電荷の色分け・数値ラベル・電荷表(gui。py3Dmolの代用品を使用)
    ├── test_optimization.py           # 最適化の結果の共通の親クラスと、PySCF版・UMA版の子クラス(common_backend)
    ├── test_vibration.py              # 振動数解析の数値計算・FrequencyResult(common_backend。バネのモデルの解析解・ASEとの照合)
    ├── test_elements.py / test_runtime.py / test_ase_bridge.py   # 元素表・GPU判定・ASEへの変換(common_backend。torch・ASEの代用品を使用)
    ├── test_freq.py                   # PySCF版の振動数解析の結果の組み立て(pyscf.hessian.thermoの代用品を使用)
    ├── test_agents_spec.py            # AGENTS.mdの仕様書が、ソース・テストと合っているか(spec_analysis.pyの解析を使用)
    ├── spec_analysis.py               # 開発用の道具(テストではない): 呼出先・呼出元・関連テストの解析と、AGENTS.mdの更新
    ├── test_analysis_pyscf.py       # 分子軌道の選択肢・Mulliken電荷(PySCFなしの代用オブジェクトで確認)
    ├── test_engine.py                # GPUランタイムの判定(PySCFなし)
    ├── test_pipeline.py              # PySCF版の計算の流れ(engine等を代用の関数に差し替えて確認)
    ├── test_writer_xyz.py            # xyz出力・最適化の標準出力2ファイル
    ├── test_colab_widgets.py       # ドロップ領域(JavaScriptを含むHTMLの生成)・識別子の安全確認
    ├── test_energy.py                 # エネルギーの単位換算・相対エネルギー(common_backend)
    ├── test_energy_plot.py           # クリックできるエネルギー収束グラフ(SVG)・目盛り(gui)
    ├── test_config_loader.py          # config/のYAMLの読み込み(backendが別名を公開していないこと)
    ├── test_gui_input.py             # ファイルの取り出し・構造の読み込みと検証・電荷の表示と読み取り
    ├── test_gui_output.py            # ダウンロード名・ダウンロード項目
    ├── test_gui_parts.py             # 共通の画面部品(電荷・スピン多重度の入力を含む。ipywidgets・Colabの代用品を使用)
    ├── test_notebooks_hidden_code.py  # 両ノートブックのコードセルが、既定でコード非表示になっているか
    ├── fake_gui_env.py                # test_gui_parts.py用の、ipywidgets・Colabの代用品
    ├── real_molecules.py                # 実物のライブラリの有無の判定と、小さな分子・SCFの結果(PySCF)。テストの代用品ではなく、実物を使うための補助
    ├── test_uma_*.py                   # UMA版(振動数の結果のまとめ・最適化・認証・計算の流れ・ログ・設定・ノートブックの構成など)
    ├── test_requirements.py             # requirements*.txtの方針(ipywidgetsを指定しない、など)
    ├── test_githooks.py                  # .githooksの動作(一時的なgitリポジトリで、mainでのAGENTS.mdの拒否・pushの中止を確認)
    ├── test_package_layering.py            # パッケージ構成と依存の向き(gui → *_backend → common_backend)・ノートブックのimportの検査
    └── test_version_sync.py / test_readme.py   # バージョン番号が1か所だけであること・README.mdとの整合
```

`references/`(`ColabReaction.ipynb`・利用者マニュアル・ライセンス)は、UI・操作設計の比較資料としてのみ保管する外部資料で、
アプリケーションから実行時に使わない。`.venv/`・`__pycache__/`・`.pytest_cache/`・`.ipynb_checkpoints/`・`.DS_Store`は
使い捨てのため、構成と仕様の対象外とする。

テストは、次のコマンドで実行できる(PySCF・ASE・py3Dmol・ipywidgets・torch・fairchemが入っていない環境では、それを使う
テストだけがスキップされる。詳しくは「ローカルの開発環境」)。

```
python3.12 -m unittest discover -s tests -p "test_*.py"
```

## パッケージ構成の目的

ノートブック → 画面(`gui`) → 計算エンジン(`pyscf_backend`・`uma_backend`) → 共通部品(`common_backend`)の向きに、
一方向に依存させるための構成である。

- `common_backend`: 画面にも計算エンジンにも依存しない共通部品(設定の読み込み・バージョン・構造の読み込み・xyz出力・
  エネルギーの換算・元素のデータ・GPUの判定・ASEへの変換・振動数解析の数値計算・最適化の結果の入れ物)。引数は、プレーンなPythonの値(元素記号・座標・エネルギーの数列等)で完結しており、PySCF版・UMA版の両方が使う。
- `pyscf_backend`: PySCF専用。PySCFのMole/SCFオブジェクトに直接依存しており、UMA版では使えない。
- `uma_backend`: UMA専用。`pyscf_backend`を一切importしない(PySCFがインストールされていない環境でも動くようにするため)。
- `gui`: 画面。共通の画面部品(`parts`・`inputs`・`outputs`・`colab_widgets`・`energy_plot`・`plot_common`)は、
  計算エンジンのパッケージをimportせず、エネルギー・座標・振動数などのプレーンな値だけを受け取る。エンジンごとに違う部分
  (構造表示の見出しに足す情報など)は、部品に関数を渡して差し替える。計算エンジンを呼び出すのは、各画面
  (`pyscf_screen`・`uma_screen`)だけ。将来のインプットファイル作成(ビルダー)も、画面(`gui/builder_screen.py`)とそのバックエンド
  (別パッケージ)として加え、「ビルド→計算」を1つのノートブックでできるようにする。
- ノートブックが読み込んでよいのは、(1)`gui`の画面と、(2)環境準備用の関数(`uma_backend.uma_hf`)だけ。(2)は、トークンを
  画面(ウィジェット)に置かない設計のため、ノートブックのセルが直接受け取る(画面の関心事ではない)。

## 設計の方針

### GUI部品(ドラッグ&ドロップ・グラフのクリック)

- ファイルの**ドラッグ&ドロップ**とエネルギーグラフの**点のクリック**は、`gui/colab_widgets.py`(ドロップ領域・コールバック登録)と
  `gui/energy_plot.py`(グラフ)にある「ブラウザ側のJavaScript → Colabのコールバック → Python」という、Colab公式の仕組み
  (`google.colab.output.register_callback`と`google.colab.kernel.invokeFunction`)で実現する。外部のライブラリ(Plotly.js等)には依存しない。
- ドロップ領域: ドロップされたファイルをJavaScriptが読み取り、Python側の関数に渡す(拡張子・5 MBの上限は、JavaScript側と
  Python側の両方で確認する)。枠をクリックしてファイルを選ぶこともできる(Colabでは、枠の下のファイル選択ボタンは置かない)。
- エネルギーグラフ: 素のSVGで描き、点をクリックすると、その点の番号がPython側に渡されて、対応する構造が表示される。選択中の点は
  赤い菱形で強調する。点そのものは静的なSVGなので、クリックの連携が動かない環境でも必ず表示され、スライダーで同じ操作ができる。
- Colab以外の環境: ドロップ領域は出さず、通常のファイル選択ボタンとスライダーだけで動作する。
- JavaScriptを含むHTMLは、`ipywidgets.HTML`ではなく、`Output`ウィジェットの中で`display(HTML(...))`して表示する
  (`ipywidgets.HTML`では`script`が実行されないため)。
- 共通の画面部品は`gui/parts.py`(`StructureFileInput`・`EnergyStructureViewer`・`VibrationViewer`・`DownloadPanel`・
  `ChargeInput`・`MultiplicityInput`)。ipywidgets 7.x・8.xのどちらでも動くように書き、`tests/test_gui_parts.py`で、
  ipywidgetsとColabの代用品を使って部品どうしのつなぎ方を検査する(見た目とJavaScriptの動作は、Colab実機で確認する)。

### ipywidgetsの版

Colabのランタイムには、ipywidgets 7.7.1が入っている。Colab標準のGUI表示の仕組みは7.x向けで、8.xが読み込まれると、
Colab公式の「カスタムウィジェットマネージャー」を有効にしない限り、操作画面が表示されない(「コードスニペット」のパネルが開くだけになる)。
そのため、`requirements.txt`・`requirements-uma.txt`では、ipywidgetsの版を指定しない(`tests/test_requirements.py`が検査する)。
別のライブラリが8.xに更新してしまった場合は、UMA版では、ノートブックの「II-0」のセルが`output.enable_custom_widget_manager()`を実行する。
PySCF版のノートブックには、同じセルを、まだ置いていない(「今後の予定」)。

### Hugging Faceのトークン(UMA版)

`uma_hf.login_from_environment()`が環境変数`HF_TOKEN`を読み取ってログインする。入力セルの作りを変えても、`uma_backend`や
`gui/uma_screen.py`を変更する必要はない(疎結合)。トークンの入力欄をGUI(ipywidgets)に置かないのは、入力値がウィジェットの状態として
保持され、保存されるノートブックに残りうるため。ノートブックのトークン入力セルでは、`#@param`(フォーム)を使わず、変数にトークンを残さない。

### 設定ファイルによる拡張(新しい手法・基底関数を追加する)

コードを変更せず、`config/`のYAMLに1エントリ足すだけで選択肢が増える(同じ計算パイプラインの中の、パラメータ違いであるため)。

例: PBE0を追加する場合、`config/functionals.yaml`に次を追記する。

```yaml
- label: "PBE0"
  key: "pbe0"
  engine: "dft"
  xc: "pbe0"
```

例: 6-31+G**を追加する場合、`config/basis_sets.yaml`の`main_group`に次を追記する。

```yaml
- label: "6-31+G**"
  key: "6-31+g**"
  pyscf_basis: "6-31+g**"
  ecp: null
```

### 新しい計算目的(TS最適化など)を追加するときの方針

計算目的は、「実行される処理そのもの」が異なるため、`config/purposes.yaml`に1行足すだけでは済まず、新しいコードが必要になる。
`purposes.yaml`の役割は、「バックエンドの機能一覧と、画面上の選択肢が食い違わないようにする」ことである。2つ目の計算目的を
追加するときに、次の方式で実装する(現在は、計算目的が構造最適化の1つだけのため、未導入)。

1. `config/purposes.yaml`に、`key`・`label`・`handler`(対応するPython側のハンドラ名)・`supports_frequency`を書く。
2. ハンドラ名 → 関数の対応表(例: `PURPOSE_HANDLERS = {"geometry_optimization": optimize.run_geometry_optimization, ...}`)を、1か所に持つ。
3. 起動時に、`purposes.yaml`の全ての計算目的にハンドラが登録されているかを検証する関数(例: `validate_purpose_handlers()`)を呼び、
   足りなければエラーにする。あわせて、`tests/`に、YAMLのキー集合と対応表のキー集合が一致することを確認するテストを足す。

### UMA版の振動数解析

数値Hessianと、並進・回転を除いた調和解析は、自前で実装している。数値計算の本体(力の中心差分のHessian・調和解析・ZPE)は、
ASEにもUMAにも依存しない純粋なnumpyの関数として`common_backend/vibration.py`にあり、`uma_backend/uma_freq.py`は、
UMAの計算器から力の関数を作って、それらを呼び出し、結果をPySCF版と同じ項目名の`FrequencyResult`にまとめる。
ASEの`Vibrations`は、並進・回転のモードを除かず(ゼロ付近のモードが混ざった3N個を返し、虚振動の数え方が紛らわしくなる)、
変位ごとのキャッシュ管理も必要になるため、使わない。PySCF版と同じく、3N-6個(直線分子は3N-5個)のモードが得られる。
信頼性は、独立した基準との照合で担保する: `tests/test_vibration.py`は、解析解(バネのモデル)・同位体効果・回転不変性と、
ASEの`VibrationsData.from_2d`との一致を、`tests/test_uma_freq.py`は、ASEの`Vibrations`(EMTのCu₂・Cu₃・Cu₄)との一致を確認する
(ASEが入っていない環境では、ASEとの照合だけスキップされる)。照合で確認できるのは、実装(単位換算・質量の重み・並進回転の除去)の
正しさであり、UMAという機械学習モデルの精度ではない(必要なら、Colab実機で、PySCF版との比較を手動で行う)。

### UMA版の収束条件・単位・モデル

- **収束条件**: 既定は力の最大値`fmax` ≤ 0.01 eV/Å(`config/uma_defaults.yaml`)。振動数計算で小さな虚振動が出にくいよう、ASEの既定(0.05)より
  厳しくしている。最大ステップ数に達しても収束しなかった場合は、例外にせず`converged=False`の結果を返し、途中経過を表示する。
- **単位**: エネルギーは、画面・出力では、PySCF版と同じくHartreeで扱い(`OptimizationResult.energies`)、eVは`energies_ev`とログに併記する。
  換算係数は`common_backend.energy.HARTREE_TO_EV`の1か所だけに定義する。
- **モデル**: 既定は`uma-s-1p2p1`。モデルカードでアーカイブ扱い(既知の不具合あり)の`uma-s-1`は、選択肢に載せていない。

### 依存ライブラリ

- `.com`/`.gjf`/`.pdb`の読み込みに`ase`を使う(`requirements.txt`に下限のみ指定)。`.mol`/`.sdf`は、`rdkit`の追加が必要になるため、未対応。
- UMA版は、`fairchem-core`・`huggingface_hub`(`requirements-uma.txt`)を使う。PySCF版には影響しない。
- `requirements.txt`では、`numpy`・`scipy`・`PyYAML`などColab標準のパッケージを`==`で固定しない(Colab既存の版と食い違い、ソースビルドが
  失敗するため)。他のパッケージも、`==`ではなく`>=`で最小版を指定する。ノートブックのインストールセルは、1パッケージずつ
  インストールして、失敗したパッケージを特定できるようにする。
- 外部ライブラリのライセンス・引用の表示: コードを改変せず、依存パッケージとして利用する範囲では、画面上の法的な表示義務はない。
  ただし、実際に計算を行うソフトウェアを明記するため、`README.md`に使用ライブラリ・ライセンスの表を載せる。UMA(学習済みモデル)の
  ライセンス・引用は、一次情報へのリンクを、`THIRD_PARTY_NOTICES.md`・ノートブック冒頭・`uma_backend/uma_notice.py`に載せる。

### lockファイルを軽量に保つ

`requirements-lock.txt`・`requirements-uma-lock.txt`は、`pip freeze`の全量(Colabのプリインストール分を含め、700個以上)ではなく、
`requirements*.txt`に明示したパッケージ(PySCF版では、`gpu4pyscf`関連も)だけを、ノートブックのセルが抜き出して生成する。
全量を書くと、インストールのセルが700回以上の`pip install`になり、非常に時間がかかるため。間接的な依存パッケージのバージョンは
固定されないが、Colabの「ランタイムバージョン」を固定していれば、基盤部分は変わらず、失敗時も1パッケージずつの
インストールで原因を特定できる。

## ノートブックのランタイム設定(メタデータの例)

```json
"metadata": {
  "accelerator": "GPU",
  "colab": {
    "gpuType": "T4",
    "runtime_attributes": { "runtime_version": "2026.07" }
  }
}
```

UMA版(`ColabApp_UMA.ipynb`)は、T4 GPU・ランタイム2026.07を記録する。PySCF版(`ColabApp.ipynb`)は、不特定多数の利用者の
GPU割り当てを消費しないよう、「ハードウェアアクセラレータ: なし(CPU)」のままにする(GPUランタイムなら、GPU4PySCFを自動で使う)。

## 今後の予定・検討中の事項

- **PySCF版のノートブックへの対応**: ipywidgetsが8.x系に更新された場合に備えて、UMA版の「II-0」のセルと同様のセルを
  `ColabApp.ipynb`にも追加することを検討する。
- **2つ目の計算目的を追加するとき**: 上記「新しい計算目的を追加するときの方針」の方式を導入する。
- **インプットファイル作成(ビルダー)**: `gui/builder_screen.py`と、そのバックエンド(別パッケージ)として加える。
- **UMA版のTS(遷移状態)探索**: `Sella`(外部パッケージ)またはASE組み込みのDimer法のどちらで実装するかは未定。
- **座標を固定した構造最適化(スキャン)**: 必要になった時点で、UMA版・PySCF版のそれぞれについて検討する。
- **UMAで最適化した構造への、PySCFによる一点計算**: UMA版の画面から、分子軌道・原子電荷を見られるようにする案。
- **PySCF版の振動数計算でのGPU利用**: Hessian計算だけ試験的にGPUを使い、失敗したらCPUにフォールバックする案(現在は、
  最終構造のCPU再計算と振動数計算を、常にCPUで行う)。
- **`io_reader._read_with_ase`の移動**: `ase_bridge`へ移すと、`io_reader`と`ase_bridge`が互いをimportする。`Structure`・`StructureError`を
  別のモジュールに分ければ移せるが、importする側が広く変わる。必要になった時点で検討する。

## バージョン管理・ブランチ運用

### ブランチ

`main`から枝分かれした作業用のブランチで、`main`に影響を与えずに開発する。完成したら合流(merge)する。
お一人での開発のため、Gitflowの縮小版を使う。

| ブランチ | 役割 | 存続期間 |
|---|---|---|
| `main` | 常に動く状態を保つ本流。ここに乗っている各コミットが1つのリリース。タグ(`v0.2.2`等)は、必ずこのブランチ上に打つ | 恒久的 |
| `develop` | 次のリリースに向けた作業をまとめる場所。featureブランチをここに集約してから、動作確認して`main`に合流させる | 恒久的 |
| `feature/<名前>` | 1つの機能・まとまった作業ごとに`develop`から切る作業用ブランチ(例: `feature/uma-preopt`)。完成したら`develop`に合流させ、削除する | 一時的 |

`release`ブランチ・`hotfix`ブランチは作らない(複数の未完成機能が同時に動く状況がないため。`develop`が、そのまま次のリリース候補を兼ねる)。
共同開発者が増えて複数の機能が同時進行するようになったら、導入を検討する。

- `main`・`develop`・`feature/*`は、同じ1つのGitHubリポジトリに共存する。`git push origin <ブランチ名>`したブランチだけが、GitHubにも現れる。
- エンドユーザー(高校生等)から見えるのは、常に`main`だけ。Colabの共有リンクは`.../blob/main/ColabApp.ipynb`のように`main`を指すため、
  `develop`・`feature/*`の作業は、`main`にマージしてpushするまでは、公開版に影響しない。

### 基本の流れ

1. 作業の開始: `git checkout develop` → `git pull origin develop` → `git checkout -b feature/名前`
2. `feature/名前`上で、コミットを重ねる(`git add -A` → `git commit -m "..."`)。バックアップのため、`git push origin feature/名前`してよい。
3. 動作確認(Colab実機を含む)が取れたら、`develop`に合流させて削除する(`--no-ff`で、合流専用のコミットを必ず1つ作る)。
   ```
   git checkout develop
   git merge --no-ff feature/名前
   git branch -d feature/名前
   ```
4. `develop`に十分な変更が溜まったら、`main`に合流させてタグを打つ(詳細は、後述の「`main`ブランチへのリリース(マージ)の手順」)。

### 変更履歴の記録

変更履歴は、`git merge --no-ff`で作られる合流コミットのメッセージと、リリース時のタグメッセージ(`git tag -a vX.Y.Z -m "変更点"`)に書く。
タグを打ったら、GitHubで、そのタグから「Create a new release」を選び、リリースノートに同じ内容を貼り付ける。`CHANGELOG.md`は使わない(二重管理になるため)。

### バージョン番号(`__version__`)の更新

`__version__`は、**リポジトリ全体のリリース番号(Gitタグ。先頭に`v`を付けた`vX.Y.Z`)と同じ値**にする。値は`common_backend/version.py`に
1か所だけ書く(画面のタイトル・UMA版の計算ログ・READMEとの整合検査が使うため、全ての層からimportできる`common_backend`に置く)。
新しい機能を`develop`から`main`へリリースする直前に、次をすべて行う。

1. `common_backend/version.py`の`__version__`を、新しい`X.Y.Z`に更新する(`__version__`を定義している場所は、ここだけ。
   `tests/test_version_sync.py`が、`pyscf_backend`・`uma_backend`に別の定義がないことを検査する)。
2. `README.md`冒頭の「現在のバージョン」を、`vX.Y.Z`に更新する(`tests/test_readme.py`が、`__version__`との一致、リンク、コードフェンス、
   記載ファイルの存在を検査する)。
3. このファイル末尾の「仕様書」と「ディレクトリ構成」を見直し、追加・変更したファイルと仕様を反映する。
4. テストが通ることを確認する(`python3.12 -m unittest discover -s tests -p "test_*.py"`)。
5. Colab実機で動作を確認したあと、`main`上で`git tag -a vX.Y.Z -m "変更内容"`を作成して、pushする。

### lockファイルの運用(`main`ブランチだけでGit管理する)

`requirements-lock.txt`(PySCF版)・`requirements-uma-lock.txt`(UMA版)は、**`main`ブランチにだけ**含める。
開発中のブランチ(`develop`・`feature/*`)には含めない。

- **仕組み**: `.gitignore`には、`AGENTS.md`・`requirements-lock.txt`・`requirements-uma-lock.txt`の3つを**全ブランチ共通で**書いておく
  (`AGENTS.md`は、lockファイルと逆に、`main`以外で追跡する。次の節を参照)。`.gitignore`が効くのは、まだ追跡していないファイルだけである。
  `main`でlockファイルを`git add -f`(強制追加)して一度コミットすれば、以後は追跡されるため、変更は普通の`git add -A`で記録される。
  `develop`・`feature/*`には、lockファイルが存在しないため、追跡されず、`.gitignore`のとおり無視される。
- **Colab上の挙動**: ノートブックのインストールのセルは、lockファイルがあればそれを、なければ`requirements*.txt`を使う。そのため、
  `main`で実行すると、常に動作確認済みの同じ組み合わせになり、開発中のブランチでは、`requirements*.txt`の指定どおりにインストールされる。
- **lockファイルを作る場所**: Colab上で、ノートブックが自動生成する(PySCF版は「2-c」、UMA版は「3-b」のセル)。生成先はColabの
  `/content/qchem_colab_app/`なので、リリースのときに、ダウンロードして、手元の`main`に置く。
- **`requirements*.txt`を変更したリリース**: 古いlockファイルには新しいパッケージが含まれず、lockを使うインストールで不足が出るため、
  Colabで確認する前に、`main`の古いlockを`git rm`で削除して、pushしておく(Colabの実行で、新しいlockが生成される)。
- **注意(守ること)**:
  - `main`を`develop`にマージしない(lockファイルが`develop`に入ってしまう)。マージは、常に`develop`→`main`の向き。
  - `develop`・`feature/*`では、lockファイルを`git add -f`しない。
  - `main`から`develop`へ切り替えると、lockファイルが作業フォルダから消える。`main`にだけ存在するためで、正常。
  - Colabのランタイムのバージョンが変わった場合は、lockの内容が合わなくなることがある。そのときは、lockを削除して、Colabで再生成する。

### `AGENTS.md`のGit管理(`main`では追跡しない、`develop`・`feature/*`では追跡する)

`AGENTS.md`は、開発者向けの文書であり、エンドユーザーが見る`main`には載せない。一方、`develop`・`feature/*`では、GitHubに履歴とバックアップを
残すため、追跡する。

- **仕組み**:
  - `.gitignore`の`AGENTS.md`の行は、全ブランチ共通で残す(ブランチごとに`.gitignore`を変えると、マージのたびに競合や上書きが起きるため)。
    `.gitignore`は、まだ追跡していないファイルにしか効かないので、追跡している`develop`・`feature/*`では、変更は普通の`git add -A`で記録される。
  - `develop`→`main`のマージでは、`AGENTS.md`が`main`に入ってしまう。そのため、マージの直後(コミットの前)に、
    `git rm --cached --ignore-unmatch AGENTS.md`で、`main`の追跡から外す(手順は、次の「リリースの手順」の4)。
  - 2回目以降のリリースでは、「`main`では削除済み」と「`develop`で変更」がぶつかり、`CONFLICT (modify/delete): AGENTS.md`と表示される。
    これは想定どおりで、同じ`git rm --cached`で解消できる。
- **手順の漏れを防ぐ仕組み(gitフック)**: `.githooks/`に、次のフックを置いている(全ブランチで追跡)。
  - `pre-commit`・`pre-merge-commit`: `main`上で`AGENTS.md`が追跡されている状態のコミットを、拒否する(検査の本体は`check-agents.sh`)。
  - `pre-push`: `main`・タグのpushに、`AGENTS.md`を含むコミットが入っていたら、pushを中止する。
  - フックは、クローンごとに、次の設定を1回だけ行わないと有効にならない(設定は`.git/config`に保存され、リポジトリには含まれない):
    `git config core.hooksPath .githooks`と`chmod +x .githooks/*`。
  - フックは、自動で直すのではなく、間違いを止めて、直し方を表示する。`--no-verify`を付けると、フックはスキップされる(付けないこと)。
  - `tests/test_githooks.py`が、フックの動作(拒否・許可)を、一時的なリポジトリで検査する。
- **注意(守ること・起こること)**:
  - `main`を`develop`にマージしない。`main`では`AGENTS.md`が追跡されていないため、`develop`の`AGENTS.md`まで削除されてしまう。
  - `AGENTS.md`を編集したら、ブランチを切り替える前に、コミットする(未コミットのまま切り替えると、gitが警告して拒否することがある)。
  - `main`に切り替えると、`AGENTS.md`が作業フォルダから消えることがある。`develop`に戻ると、再び現れる。どちらも正常。
  - `main`に`AGENTS.md`が入った状態でコミットしてしまった場合(フックが無効だった等)は、`git rm --cached AGENTS.md` → `git commit`で
    追跡から外す。履歴を消す操作(強制プッシュ等)は、しない。`push`済みの場合は、状況を相談する。

### `main`ブランチへのリリース(マージ)の手順(Claudeが、`main`へのマージのコマンドを案内するときは、必ず次をすべて含める)

利用者はgitに不慣れなため、**実行するコマンドと、実行するタイミングを、毎回、省略せずに書く**。
`vX.Y.Z`は新しいバージョン、`feature/名前`は作業ブランチ名に置き換える。

1. **事前確認**:
   - `git status` が `nothing to commit, working tree clean` であること。
   - `grep -n "lock\|AGENTS" .gitignore` で、`.gitignore`に`AGENTS.md`・`requirements-lock.txt`・`requirements-uma-lock.txt`の3行があること。
     足りなければ、`printf 'ファイル名\n' >> .gitignore`で追加する。
   - `git config core.hooksPath`が`.githooks`と表示されること。表示されなければ、`git config core.hooksPath .githooks`と
     `chmod +x .githooks/*`を実行する。
   - `git ls-files AGENTS.md`が、`develop`上で`AGENTS.md`と表示されること(追跡されていること)。
2. **バージョンの更新**(作業ブランチ上): `common_backend/version.py`・`README.md`冒頭を`X.Y.Z`に更新し、このファイル末尾の「仕様書」を見直し、
   テストを通して、コミットとpushをする(詳しくは「バージョン番号(`__version__`)の更新」)。
3. **`develop`への統合**: `git checkout develop` → `git pull origin develop` → `git merge --no-ff --no-edit feature/名前` →
   `git push origin develop`。
4. **`main`への統合**(`AGENTS.md`を`main`に入れない手順を含む。コミットの前に、必ず、止めて確認する):
   1. `git checkout main` → `git pull origin main`
   2. `git merge --no-ff --no-commit develop`(マージの内容を確認してからコミットするための指定。`CONFLICT (modify/delete): AGENTS.md`と出るのは、
      想定どおり。それ以外のファイルで`CONFLICT`と出たら、`git merge --abort`で中止して、状況を相談する)
   3. `git diff --name-only --diff-filter=U`(`AGENTS.md`だけが表示されるか、何も表示されないこと)
   4. `git rm --cached --ignore-unmatch AGENTS.md`
   5. `git diff --name-only --diff-filter=U`(何も表示されないこと)と、`git status`(`AGENTS.md`が出ないこと)
   6. `git commit -m "vX.Y.Z: developをmainに統合"` → `git push origin main`(フックが、`AGENTS.md`の混入を検査する)
5. **`requirements*.txt`を変更したリリースだけ**: `git rm requirements-lock.txt requirements-uma-lock.txt` →
   `git commit -m "古いlockファイルを削除(依存パッケージの変更のため)"` → `git push origin main`(`main`にlockファイルが、まだ無い場合は不要)。
6. **Colabでの確認とlockファイルの生成**: 両ノートブックを、「1-b」セルの`BRANCH`を`main`にして、上から実行する。PySCF版の「2-c」セルが
   `requirements-lock.txt`を、UMA版の「3-b」セルが`requirements-uma-lock.txt`を生成する。動作を確認できたら、Colab左のファイルパネルで、
   `qchem_colab_app`フォルダ内の両ファイルを、右クリックから「ダウンロード」し、手元のリポジトリ直下(`main`が選ばれている状態)に置く。
7. **lockファイルの記録**(`main`上): `git add -f requirements-lock.txt requirements-uma-lock.txt` →
   `git status`(`new file:`または`modified:`の2つが出ること。`AGENTS.md`が出ないこと) →
   `git commit -m "vX.Y.Z: 動作確認済みの依存バージョンを記録(lockファイル)"` → `git push origin main`。
8. **タグ**: `git tag -a vX.Y.Z -m "変更内容"` → `git push origin vX.Y.Z`(タグは、lockファイルの記録のあとに付ける。タグの時点のlockが、
   その版の依存バージョンになる)。続けて、GitHubで「Create a new release」を行う。
9. **後片付け**: `git branch -d feature/名前` → `git push origin --delete feature/名前` → `git checkout develop`
   (開発に戻る。lockファイルが作業フォルダから消え、`AGENTS.md`が現れるのは正常)。

### ロールバックの方法

- 最新版に不具合があった場合は、`git checkout v0.2.1`のようにタグを指定してチェックアウトするか、問題のコミットを`git revert <コミットID>`で打ち消す。
- `main`には、動作確認済みの依存バージョンを記録したlockファイルが含まれるため、タグを指定してチェックアウトすれば、その版の依存バージョンも再現できる。

## 開発メモ(実装上の注意)

- **PySCFの虚振動の表現**: `pyscf.hessian.thermo.harmonic_analysis`は、既定(`imaginary_freq=True`)では、虚振動を、実部が0の複素数
  (例: `0+2268j`)で返す。実部だけを取ると`0.0`になり、虚振動が検出されない(v0.2.2で、実物のPySCF 2.14.0で確認して直した)。
  `pyscf_backend/freq.py`の`_signed_wavenumber`が、虚部の大きさを負の値にして、`common_backend/vibration.py`と同じ
  「虚振動は負の値」にそろえる。PySCFの版が変わったときは、直線の水(鞍点)で虚振動が2個になることを、`tests/test_freq.py`が確認する。
- **構造最適化のエネルギー履歴がほぼ1点しかない場合**: `pyscf_backend/optimize.py`の`_make_callback()`内で、PySCFのgeomeTRIC連携が渡す
  コールバック引数のキー名(`energy`・`e_tot`・`mol`・`coords`等)が、使っているPySCFの版と一致していない可能性がある。
  `pyscf.geomopt.geometric_solver`のソースと照らし合わせて調整する。
- **GPU**: GPUを使うかどうかは、GPUランタイムかどうか(`common_backend.runtime.nvidia_gpu_detected`が、`nvidia-smi`が成功するかで判定する)で
  自動的に決める(GUIにチェックボックスは置かない)。UMA版は、torchがGPUを使えるか(`runtime.torch_cuda_available`)で決める。
  GPU4PySCFのインストールに失敗する場合は、ColabのCUDAバージョンと`gpu4pyscf-cuda12x`・`gpu4pyscf-cuda11x`の対応を確認し、
  `ColabApp.ipynb`のGPU4PySCFインストールセルのパッケージ名を読み替える。GPUが使えなくても、CPU実行として計算は継続する。
- **最終構造のCPU再計算・振動数計算をCPUで行う理由**: GPU4PySCFの解析的Hessian・分子軌道(cubegen)・Mulliken電荷計算の対応状況は、
  主にDFT向けに整備されており、HFでの対応状況やGPU上のSCFオブジェクトをそのまま渡せるかが確認できていない。また、Hessian計算は
  メモリを多く使い、Colab無料枠のT4(VRAM約15GB)ではメモリ不足になりやすい。確実に動くCPU版に、一度変換する。
- **SCFが収束しない場合**: `engine.run_scf()`が、レベルシフト付きで自動的に1回やり直す。それでも収束しなければ、画面に日本語の原因・対策を表示する。
- **moldenファイル**: MacMolPltが分子軌道の等値面表示に対応しているのはデカルト型のガウス関数だけのため、`mol.cart = True`(6D/10F)で出力する。
  実際にMacMolPltで開いての確認は、できていない。表示できない場合は、`.molden`の中身([Atoms]・[GTO]・[MO])から原因を調べる。
- **原子電荷の色付け**: Mulliken電荷を基準にする(青=正・緑=中性付近・赤=負)。ESP(静電ポテンシャル)基準にしないのは、`mol.cart = True`のとき、
  ESPの計算に使う補助分子(`fakemol_for_charges`。球面調和関数型に固定)と型が合わず、計算できないため。
- **開殻分子の分子軌道**: PySCFの開殻(UHF/UKS)では、`mo_occ`・`mo_energy`が2行、`mo_coeff`が3次元の配列になる。αスピンの軌道を基準に扱う
  (`analysis_pyscf._occupations`・`visualizer_pyscf._mo_coeff_for_cube`)。
- **UMA版のトラブルシューティング**(Hugging Faceのアクセス、`torch`の更新、GPUが使えない、など)は、
  利用者向けに、`README.md`の「トラブルシューティング」にまとめている。

# 仕様書(モジュールと関数の仕様)

この仕様書は、リポジトリに含まれるソース、設定、ノートブックおよびテストの公開的な仕様をまとめたものである。ファイルの構成は、
上の「ディレクトリ構成」を参照。`AGENTS.md`は、`develop`・`feature/*`にだけ存在し、`main`には存在しない(「`AGENTS.md`のGit管理」を参照)。

## 仕様(モジュールと関数)

各項目(関数・クラス・メソッド・プロパティ・公開定数)は、次の行に分けて書く。

- 引数: 受け取る値(ない場合は「なし」)
- 戻り値: 返す値
- 目的: 何のためにあるか
- 技術選定・例外: 技術・方式を選んだ理由、送出する例外(ある場合のみ)
- 呼出先: この項目が呼び出す、プロジェクト内の項目(ない場合は「なし」)
- 呼出元: この項目を呼び出す、プロジェクト内の項目(ない場合は「なし」)
- 関連テスト: この項目を参照しているテストファイル(ない場合は「なし」。呼出元には、テストを含めない)

呼出先・呼出元は、プロジェクト内のものだけを、テストを除いて書く。他のモジュールの項目は`gui.parts.ChargeInput`のようにパッケージ名からの名前で、同じモジュールの項目は短い名前で書く。名前の後ろの括弧は、呼出しの種類を表す(「定数」: 定数の参照、「コールバックとして登録」: 呼出しをイベントやコールバックに任せる登録、「例外の捕捉」: `except`での捕捉、「属性として参照」: プロパティの参照)。クラスの「呼出先」は、`__init__`の呼出先、「呼出元」は、そのクラスを生成する箇所である。モジュール内の項目は、ソースファイルの定義の順に並べる。

「呼出先」「呼出元」「関連テスト」の行は、**手で書かず**、`python3.12 tests/spec_analysis.py --fix`が、ソースとテストの構文解析から更新する。`tests/test_agents_spec.py`が、これらの行が最新か、ソースの定義すべてに項目があるか(逆も同じ)を検査する(`AGENTS.md`がない`main`ブランチでは、スキップする)。構文解析では分からない呼出し(型の分からない変数の属性の参照など)は、`tests/spec_analysis.py`の`MANUAL_EDGES`に足す。関連テストは、テストに、その名前があり、かつ、(名前がプロジェクト全体で1つだけ、またはテストがそのモジュールをimportしている)ときに挙げる(メソッド・プロパティは、モジュールのimportと、クラス名・メソッド名の両方が必要)。関数・クラス・メソッド・公開定数を追加・変更・削除したときは、項目の文章(引数・戻り値・目的など)を手で直してから、`--fix`を実行する。

- `ColabApp.ipynb`
  - 目的: PySCF 版の Colab 実行入口。実行環境の表示、GitHub からのブランチ／タグ選択取得、依存関係と任意 GPU4PySCF の導入、lock ファイルの生成、サンプル構造の作成、`gui.pyscf_screen.build_app()` の表示を順に行う。目的はブラウザだけで PySCF 計算を実行可能にすること。すべてのコードセルは、メタデータ `cellView: form` と先頭行の `#@title 題名` により、既定でコードを折りたたんで題名だけを表示する（ColabReaction と同じ方式。クリックすればコードを開ける）
  - 呼出先: `gui.pyscf_screen.build_app`
  - 呼出元: なし（利用者が Colab で開いて実行する入口）

- `ColabApp_UMA.ipynb`
  - 目的: UMA 版の Colab 実行入口。Hugging Face の利用案内とトークンの環境変数への設定、UMA 用依存関係の導入、GPU 確認、ウィジェット表示の準備、`gui.uma_screen.build_app()` の表示を行う。トークンをノートブックの保存状態や GUI 状態へ残さない設計を採る。すべてのコードセルは、メタデータ `cellView: form` と先頭行の `#@title 題名` により、既定でコードを折りたたんで題名だけを表示する（ColabReaction と同じ方式。クリックすればコードを開ける）
  - 呼出先: `uma_backend.uma_hf.login_from_environment`、`uma_backend.uma_hf.check_model_access`、`uma_backend.uma_hf.UmaSetupError`（例外の捕捉）、`gui.uma_screen.build_app`
  - 呼出元: なし（利用者が Colab で開いて実行する入口）

- `README.md`

  利用者向けの文書。利用目的、できること・できないこと、Colab 実行手順、UMA 版の使い方とライセンス・引用、PySCF 版・UMA 版のトラブルシューティング、使用ライブラリを説明する。冒頭の「現在のバージョン」は `common_backend.version.__version__` と一致させる。

- `THIRD_PARTY_NOTICES.md`

  PySCF 版・UMA 版で使用する第三者ソフトウェアのライセンスおよび通知情報を記録する。

- `requirements.txt` / `requirements-lock.txt`

  PySCF 版の依存関係を定義する。前者は導入時の許容範囲、後者は Colab またはローカルで確認した軽量な固定記録である。GPU4PySCF は Colab 側で条件付き導入する。

- `requirements-uma.txt` / `requirements-uma-lock.txt`

  UMA 版の依存関係を定義する。`fairchem-core`、ASE、Hugging Face クライアントを中心とし、Colab 標準の `ipywidgets` を維持する。

### qchem_colab_app

- `__init__.py`

  最上位パッケージ（名前空間）の識別用モジュール。公開関数は持たず、何も import しない。プロジェクト固有の名前のパッケージを1つだけ置き、その下に `gui`・`common_backend`・`pyscf_backend`・`uma_backend` を入れることで、他のライブラリの同名のモジュールとの衝突を避ける。

### common_backend

画面にも、PySCF・UMA のどちらの計算エンジンにも依存しない、バックエンドの共通部品。引数・戻り値を元素記号、座標、数値、辞書などのプレーンな値に寄せ、両アプリが同じ入出力部品を使えるようにする。プロジェクト内のどのパッケージも import しない。

- `__init__.py`

  共通部品パッケージの識別用モジュール。公開関数は持たない。

- `ase_bridge.py`

  共通の構造（`io_reader.Structure`）を ASE のオブジェクトに変換する。画面にも計算エンジンにも依存しない。電荷・スピン多重度の設定は、計算器ごとの約束のため、含まない。

  - `structure_to_atoms(structure) -> ase.Atoms`
    - 引数: 共通の構造（`symbols`・`coords`［Å］を持つ `Structure`）
    - 戻り値: 元素記号と座標だけを設定した ASE `Atoms`
    - 目的: 共通の構造を、ASE のオブジェクトに変換する。電荷・スピン多重度は、計算器ごとの約束のため、ここでは設定しない。ase は関数の中で import する
    - 呼出先: なし
    - 呼出元: `uma_backend.uma_engine.build_atoms`
    - 関連テスト: `tests/test_ase_bridge.py`、`tests/test_uma_engine.py`

- `config_loader.py`

  `config/` 配下の YAML 設定を読み込む共通関数。PySCF 版・UMA 版が同じ関数を使う。

  - `PROJECT_ROOT`
    - 目的: リポジトリのルートの場所を `pathlib.Path` で保持する。このファイルは `<リポジトリ>/qchem_colab_app/common_backend/` にあるため、3つ上をルートとする
    - 呼出先: なし
    - 呼出元: `CONFIG_DIR`（定数）
    - 関連テスト: `tests/test_config_loader.py`

  - `CONFIG_DIR`
    - 目的: `config/` の場所（`PROJECT_ROOT` の直下）を `pathlib.Path` で保持する
    - 呼出先: `PROJECT_ROOT`（定数）
    - 呼出元: `load_yaml`（定数）
    - 関連テスト: `tests/test_config_loader.py`

  - `load_yaml(filename: str) -> dict | list`
    - 引数: `config/` 内の YAML ファイル名
    - 戻り値: パース結果
    - 目的: 設定読込みを一元化し、ファイルが無いときは配置を確認する日本語メッセージの `FileNotFoundError` にする
    - 呼出先: `CONFIG_DIR`（定数）
    - 呼出元: `gui.pyscf_screen.build_app`、`gui.uma_screen.build_app`、`pyscf_backend.engine._load_basis`、`pyscf_backend.engine._load_functional`
    - 関連テスト: `tests/test_config.py`、`tests/test_config_loader.py`、`tests/test_pipeline.py`、`tests/test_uma_config.py`

- `cube.py`

  Gaussian cube 形式のファイルの読取り。標準ライブラリだけで動き、画面にも計算エンジンにも依存しない。

  - `max_abs_value(cube_path: str) -> float`
    - 引数: Gaussian cube 形式のファイルのパス
    - 戻り値: 格子点上の値の最大絶対値（値が 1 つもなければ 0.0）
    - 目的: cube ファイルのヘッダー（コメント 2 行・原子数行・軸 3 行・原子リスト）を読み飛ばして、値の本体だけから最大絶対値を求める。分子軌道の等値面の閾値を決めるための、cube の直接読取り
    - 技術選定: 標準ライブラリだけで読む。PySCF の `cubegen.orbital` が値の配列を返さない版でも、書き出した cube ファイルから閾値のもとを得られるようにするため
    - 呼出先: なし
    - 呼出元: `pyscf_backend.visualizer_pyscf.render_orbital`
    - 関連テスト: `tests/test_cube.py`、`tests/test_visualizer.py`

- `elements.py`

  元素に関するデータ（元素記号 → 原子番号の表。H〜Xe）。画面にも計算エンジンにも依存しない。扱える元素の範囲は、この表で決まる。特定のエンジンが扱えない元素の判定（例: PySCF 版の遷移金属）は、そのエンジンのパッケージにある。

  - `ATOMIC_NUMBERS`
    - 目的: 元素記号から原子番号への表（H〜Xe）。読み込める元素の範囲の判定、電荷・スピン多重度の検証で使う全電子数の計算、軌道の数え上げに使う。表はここだけに置く
    - 呼出先: なし
    - 呼出元: `common_backend.io_reader._read_with_ase`（定数）、`common_backend.io_reader.read_xyz`（定数）、`common_backend.io_reader.validate_charge_and_multiplicity`（定数）、`pyscf_backend.analysis_pyscf._core_and_valence_orbital_counts`（定数）
    - 関連テスト: `tests/test_elements.py`

- `energy.py`

  エネルギーの単位換算（Hartree・kcal/mol・eV）と相対エネルギー。画面にも計算エンジンにも依存しない純粋な値と関数で、バックエンド（`uma_backend`）と画面（`gui.parts`・`gui.energy_plot`）の両方が使う。

  - `HARTREE_TO_KCAL_MOL`
    - 目的: エネルギーの単位換算（1 Hartree = 627.5094740631 kcal/mol）を 1 か所で定義する
    - 呼出先: なし
    - 呼出元: `relative_energies_kcal`（定数）、`common_backend.vibration.FrequencyResult.zpe_kcal_per_mol`（定数）、`gui.parts.EnergyStructureViewer._show_structure_at_step`（定数）、`uma_backend.uma_report.build_log_text`（定数）
    - 関連テスト: `tests/test_energy.py`、`tests/test_energy_plot.py`、`tests/test_uma_freq.py`、`tests/test_vibration.py`

  - `HARTREE_TO_EV`
    - 目的: エネルギーの単位換算（1 Hartree = 27.211386245988 eV、CODATA 2018）を 1 か所で定義する。`uma_backend`・`pyscf_backend` は、Hartree と eV の換算に、この定数だけを使う
    - 呼出先: なし
    - 呼出元: `pyscf_backend.analysis_pyscf.orbital_choices`（定数）、`uma_backend.uma_freq.run_frequency_analysis`（定数）、`uma_backend.uma_optimize.run_geometry_optimization`（定数）
    - 関連テスト: `tests/test_analysis_pyscf.py`、`tests/test_energy.py`、`tests/test_uma_freq.py`、`tests/test_uma_optimize.py`

  - `relative_energies_kcal(energies_hartree) -> list[float]`
    - 引数: 各最適化点の全エネルギー[Hartree]
    - 戻り値: 最終点をゼロとする相対エネルギー[kcal/mol]
    - 目的: グラフと構造表示で同じエネルギー基準を使う
    - 呼出先: `HARTREE_TO_KCAL_MOL`（定数）
    - 呼出元: `gui.energy_plot.build_energy_plot_html`
    - 関連テスト: `tests/test_energy.py`、`tests/test_energy_plot.py`

- `io_reader.py`

  構造ファイルの読込みと、計算前の元素・座標・電荷・スピン検証を担当する。元素の表は `common_backend.elements` を使う。`.xyz` は自前のパーサー、`.com`・`.gjf`・`.pdb` は ASE 経由で読み込む。特定のエンジンが扱えない元素の判定は、そのエンジンのパッケージにある。

  - `SUPPORTED_EXTENSIONS`
    - 目的: `read_structure` が受け付ける拡張子（`.xyz`・`.com`・`.gjf`・`.pdb`）の集合。エラーメッセージで、対応形式を案内するために使う
    - 呼出先: なし
    - 呼出元: `read_structure`（定数）
    - 関連テスト: なし

  - `StructureError(ValueError)`
    - 目的: 利用者に表示可能な構造入力エラーを表す例外
    - 呼出先: なし
    - 呼出元: `_read_with_ase`、`read_structure`、`read_xyz`、`validate_charge_and_multiplicity`、`validate_structure`、`gui.inputs.extract_uploaded_file`、`gui.parts.StructureFileInput._update_preview`（例外の捕捉）、`gui.pyscf_screen.build_app`（例外の捕捉）、`gui.uma_screen.build_app`（例外の捕捉）、`pyscf_backend.pipeline.run_calculation`
    - 関連テスト: `tests/test_gui_input.py`、`tests/test_gui_parts.py`、`tests/test_io_reader.py`、`tests/test_pipeline.py`

  - `Structure(symbols: list[str], coords: list[list[float]], comment: str = "")`
    - 目的: 元素記号、Å 単位座標、注釈を保持するデータクラス。PySCF/UMA 共通入力形式
    - 呼出先: なし
    - 呼出元: `_read_with_ase`、`read_xyz`
    - 関連テスト: `tests/test_ase_bridge.py`、`tests/test_engine.py`、`tests/test_gui_input.py`、`tests/test_io_reader.py`、`tests/test_pipeline.py`、`tests/test_uma_engine.py`、`tests/test_uma_pipeline.py`

  - `read_xyz(filepath: str) -> Structure`
    - 引数: XYZ ファイルパス
    - 戻り値: `Structure`
    - 目的: 外部ライブラリなしで標準 XYZ を読む
    - 技術選定: 最小形式を自前実装し、基本入力の依存関係を減らす
    - 呼出先: `StructureError`、`common_backend.elements.ATOMIC_NUMBERS`（定数）、`Structure`
    - 呼出元: `read_structure`
    - 関連テスト: `tests/test_io_reader.py`

  - `_read_with_ase(filepath: str, ase_format: str) -> Structure`
    - 引数: ファイルのパス、ASE に渡す形式名
    - 戻り値: 読み込んだ構造
    - 目的: .com／.gjf／.pdb を ASE（`ase.io.read`）で読み込み、H〜Xe 以外の元素記号があればエラーにする。ASE が入っていない場合・読み込めない場合は、`StructureError` を送出する。内部補助関数
    - 呼出先: `StructureError`、`common_backend.elements.ATOMIC_NUMBERS`（定数）、`Structure`
    - 呼出元: `read_structure`
    - 関連テスト: なし

  - `read_structure(filepath: str) -> Structure`
    - 引数: 入力ファイルパス
    - 戻り値: `Structure`
    - 目的: `.xyz` は `read_xyz`、`.com`/`.gjf`/`.pdb` は ASE に振り分ける
    - 呼出先: `read_xyz`、`_read_with_ase`、`StructureError`、`SUPPORTED_EXTENSIONS`（定数）
    - 呼出元: `gui.inputs.read_uploaded_structure`
    - 関連テスト: `tests/test_gui_input.py`、`tests/test_io_reader.py`

  - `validate_structure(structure: Structure, min_distance: float = 0.4) -> None`
    - 引数: 構造、原子間最小距離[Å]
    - 戻り値: 正常時はなし、異常時は `StructureError`
    - 目的: 空構造、配列不整合、原子重なりを検出する
    - 呼出先: `StructureError`
    - 呼出元: `gui.inputs.load_uploaded_structure`
    - 関連テスト: `tests/test_gui_input.py`、`tests/test_io_reader.py`

  - `validate_charge_and_multiplicity(structure: Structure, charge: int, multiplicity: int) -> None`
    - 引数: 構造、総電荷、スピン多重度
    - 戻り値: 正常時はなし、矛盾時は `StructureError`
    - 目的: 電子数・多重度の化学的整合性を確認する
    - 呼出先: `StructureError`、`common_backend.elements.ATOMIC_NUMBERS`（定数）
    - 呼出元: `gui.inputs.load_uploaded_structure`
    - 関連テスト: `tests/test_gui_input.py`、`tests/test_io_reader.py`

- `optimization.py`

  構造最適化の結果の入れ物。PySCF にも ASE にも UMA にも依存しない。PySCF 版・UMA 版の共通の親クラス `OptimizationResult` を置き、それぞれの `OptimizationResult`（`pyscf_backend.optimize`・`uma_backend.uma_optimize`）は、この親クラスの子クラスとして、エンジン固有の項目を足す（振動数解析の `common_backend.vibration.FrequencyResult` と同じ構成）。画面（`gui.parts.EnergyStructureViewer`）と出力関数（`common_backend.writer_xyz.write_optimization_outputs`）は、共通の項目だけを使う。

  - `OptimizationResult()`
    - 引数: なし
    - 戻り値: `symbols`（元素記号のリスト）、`energies`（各ステップのエネルギー [Hartree]）、`coords_history`（各ステップの座標 [Å]。要素は `[[x, y, z], ...]`）、`converged`（収束したか）、`elapsed_seconds`（所要時間 [秒]）を持つ結果
    - 目的: 構造最適化の結果を入れる、PySCF 版・UMA 版の共通の親クラス
    - 呼出先: なし
    - 呼出元: なし
    - 関連テスト: `tests/test_gui_parts.py`、`tests/test_optimization.py`、`tests/test_writer_xyz.py`

- `runtime.py`

  計算を実行する環境（GPU の有無）の判定。画面にも計算エンジンにも依存しない。`nvidia_gpu_detected`（GPU ランタイムが割り当てられているか）と `torch_cuda_available`（PyTorch が CUDA を使えるか）は、答える問いが違う。PySCF 版は、GPU4PySCF を読み込む前に決めるため前者を、UMA 版は、推論が torch で動くため後者を使う。

  - `nvidia_gpu_detected() -> bool`
    - 引数: なし
    - 戻り値: GPU ランタイム（NVIDIA GPU）が割り当てられていれば `True`
    - 目的: Colab の実行環境で GPU4PySCF を試す可否を、`nvidia-smi` の成否で判定する。`nvidia-smi` が無い・失敗・タイムアウトのときは `False`
    - 技術選定: torch が入っていない環境（PySCF 版）でも動くよう、コマンドの成否で判定する
    - 呼出先: なし
    - 呼出元: `pyscf_backend.pipeline.run_calculation`
    - 関連テスト: `tests/test_pipeline.py`、`tests/test_runtime.py`

  - `torch_cuda_available() -> bool`
    - 引数: なし
    - 戻り値: PyTorch が CUDA（GPU）を使えれば `True`。torch が入っていなければ `False`
    - 目的: UMA の推論に使うデバイス（GPU か CPU）を決める。GPU ランタイムでも、CPU 版の torch が入っていれば `False` になる。torch は関数の中で import する
    - 呼出先: なし
    - 呼出元: `uma_backend.uma_pipeline.run_calculation`
    - 関連テスト: `tests/test_runtime.py`、`tests/test_uma_pipeline.py`

- `version.py`

  リポジトリ全体のリリース番号 `__version__`（Git タグと同じ値）を 1 か所だけで定義する。画面のタイトル（`gui.pyscf_screen`・`gui.uma_screen`）、`pyscf_backend.pipeline`・`uma_backend.uma_pipeline` の出力 xyz のコメント、UMA 版の計算ログ、README との整合検査が、この値を直接 import して使う（`pyscf_backend`・`uma_backend` には別名を置かない）。更新手順は「バージョン管理・ブランチ運用」の「バージョン番号（`__version__`）の更新」を参照する。

  - `__version__`
    - 目的: リポジトリ全体のリリース番号（Git タグと同じ値）を保持する
    - 呼出先: なし
    - 呼出元: `gui.pyscf_screen.build_app`（定数）、`gui.uma_screen.build_app`（定数）、`pyscf_backend.pipeline.run_calculation`（定数）、`uma_backend.uma_pipeline.run_calculation`（定数）
    - 関連テスト: `tests/test_pipeline.py`、`tests/test_readme.py`、`tests/test_uma_pipeline.py`、`tests/test_version_sync.py`

- `vibration.py`

  振動数解析の、計算エンジンに依存しない数値計算（中心差分による Hessian、並進・回転を除いた調和解析、ゼロ点エネルギー）。純粋な numpy で、ASE にも UMA にも PySCF にも依存しない。現在使うのは `uma_backend.uma_freq` だけで、PySCF 版は PySCF 自身の解析的 Hessian と `pyscf.hessian.thermo` を使う。結果の入れ物 `FrequencyResult` は、PySCF 版・UMA 版の共通の親で、PySCF 版は子クラスで熱力学量を足す。数値の検証は `tests/test_vibration.py` が行う。

  - `compute_hessian_fd(forces_fn, positions, delta: float = 0.01, progress = None) -> numpy.ndarray`
    - 引数: 座標（N,3）[Å] から力（N,3）[eV/Å] を返す関数、平衡座標、変位幅 [Å]、任意の進捗コールバック（完了した原子数, 全原子数）
    - 戻り値: Hessian（shape (3N, 3N)、単位 eV/Å²、対称化済み）
    - 目的: 各原子の各方向を ±δ だけ動かし、力の中心差分から Hessian を作る。進捗コールバックは、原子ごとに呼ぶ
    - 技術選定: UMA は解析的な Hessian を返さず力だけを返すため、数値微分を使う。ASE にも UMA にも依存しない純粋な numpy の関数なので、バネのモデルで厳密な値と照合できる
    - 呼出先: なし
    - 呼出元: `uma_backend.uma_freq.run_frequency_analysis`
    - 関連テスト: `tests/test_vibration.py`

  - `harmonic_analysis(masses, positions, hessian, rank_tol: float = 1e-8) -> tuple[numpy.ndarray, numpy.ndarray]`
    - 引数: 原子質量 [amu]、座標 [Å]、Hessian [eV/Å²]、並進・回転の次元を判定する特異値の閾値
    - 戻り値: 振動数 [cm⁻¹]（昇順、虚振動は負）と、基準振動モード（shape (モード数, 原子数, 3)、各モードの変位を長さ 1 に規格化）。原子が 1 個だけのときは、空の結果
    - 目的: 質量で重み付けし、並進 3 つ・回転 3 つ（直線分子は回転 2 つ）の方向を除いた空間で対角化して、振動モードだけ（3N-6 個。直線分子は 3N-5 個）を求める
    - 技術選定: 特異値でランクを判定し、直線分子でも正しい個数のモードを得る。ASE の `Vibrations` は並進・回転に由来するゼロ付近のモードが混ざり、虚振動の数え方が紛らわしくなるため使わない
    - 呼出先: なし
    - 呼出元: `uma_backend.uma_freq.run_frequency_analysis`
    - 関連テスト: `tests/test_freq.py`、`tests/test_vibration.py`

  - `zero_point_energy_ev(frequencies_cm1) -> float`
    - 引数: 調和振動数 [cm⁻¹] のリスト
    - 戻り値: ゼロ点エネルギー [eV]
    - 目的: ZPE = (1/2)Σhν を求める。虚振動（負の値）は含めない。Hartree・kcal/mol への換算は、呼出し側が `common_backend.energy` の係数で行う
    - 呼出先: なし
    - 呼出元: `uma_backend.uma_freq.run_frequency_analysis`
    - 関連テスト: `tests/test_vibration.py`

  - `FrequencyResult()`
    - 引数: なし
    - 戻り値: `frequencies_cm1`（振動数 [cm⁻¹]、虚振動は負）、`normal_modes`（shape (モード数, 原子数, 3)。なければ `None`）、`zpe_hartree`（ゼロ点エネルギー。なければ `None`）、`elapsed_seconds`、`warning_message` を持つ結果
    - 目的: 振動数解析の結果を入れる、PySCF 版・UMA 版の共通の親クラス。UMA 版はそのまま使い、PySCF 版は子クラスで熱力学量を足す。画面（`gui.parts.VibrationViewer`）は `frequencies_cm1` と `normal_modes` だけを使う
    - 呼出先: なし
    - 呼出元: `pyscf_backend.freq.FrequencyResult.__init__`、`uma_backend.uma_freq.run_frequency_analysis`
    - 関連テスト: `tests/test_freq.py`、`tests/test_gui_parts.py`、`tests/test_uma_freq.py`、`tests/test_uma_notice_report.py`、`tests/test_uma_pipeline.py`、`tests/test_vibration.py`
    - `n_imaginary`（プロパティ）
      - 戻り値: 虚振動（負の振動数）の数
      - 目的: `frequencies_cm1` から求めるため、振動数と食い違わない
      - 呼出先: なし
      - 呼出元: `pyscf_backend.freq.run_frequency_analysis`、`uma_backend.uma_freq.run_frequency_analysis`（属性として参照）、`uma_backend.uma_pipeline.run_calculation`
      - 関連テスト: `tests/test_freq.py`、`tests/test_uma_freq.py`、`tests/test_vibration.py`
    - `zpe_kcal_per_mol`（プロパティ）
      - 戻り値: ゼロ点エネルギー [kcal/mol]。`zpe_hartree` が `None` なら `None`
      - 目的: `zpe_hartree` を、`common_backend.energy.HARTREE_TO_KCAL_MOL` で換算する
      - 呼出先: `common_backend.energy.HARTREE_TO_KCAL_MOL`（定数）
      - 呼出元: `uma_backend.uma_report.build_log_text`
      - 関連テスト: `tests/test_freq.py`、`tests/test_uma_freq.py`、`tests/test_vibration.py`

- `writer_xyz.py`

  XYZ 形式の単一構造・複数構造を文字列またはファイルとして出力する。

  - `FINAL_STRUCTURE_FILENAME`
    - 目的: 最終構造の出力ファイル名（`final_structure_for_ColabReaction.xyz`）を PySCF 版・UMA 版で共通にする
    - 呼出先: なし
    - 呼出元: `write_optimization_outputs`（定数）
    - 関連テスト: なし

  - `TRAJECTORY_FILENAME`
    - 目的: 最適化トラジェクトリの出力ファイル名（`optimization_trajectory.xyz`）を PySCF 版・UMA 版で共通にする
    - 呼出先: なし
    - 呼出元: `write_optimization_outputs`（定数）
    - 関連テスト: なし

  - `_format_xyz_block(symbols, coords, comment: str = "") -> str`
    - 引数: 元素記号のリスト、座標のリスト、コメント
    - 戻り値: 1 フレーム分の XYZ 形式の文字列（末尾に改行なし）
    - 目的: すべての XYZ 出力（ファイル・文字列・アニメーション）の整形を 1 か所にまとめる内部補助関数
    - 呼出先: なし
    - 呼出元: `multiframe_xyz_string`、`write_final_structure`、`write_trajectory`、`xyz_string`
    - 関連テスト: なし

  - `write_final_structure(symbols, coords, filepath: str, comment: str = "Optimized structure") -> None`
    - 引数: 元素、座標、出力先、コメント
    - 戻り値: なし
    - 目的: 最終構造 XYZ を保存する
    - 呼出先: `_format_xyz_block`
    - 呼出元: `write_optimization_outputs`
    - 関連テスト: `tests/test_writer_xyz.py`

  - `write_trajectory(symbols, coords_history, filepath: str, energies = None) -> None`
    - 引数: 元素、座標履歴、出力先、任意のエネルギー
    - 戻り値: なし
    - 目的: 最適化履歴を多フレーム XYZ として保存する
    - 呼出先: `_format_xyz_block`
    - 呼出元: `write_optimization_outputs`
    - 関連テスト: `tests/test_writer_xyz.py`

  - `write_optimization_outputs(out_dir: str, final_symbols, final_coords, final_comment: str, opt_result) -> tuple[str, str]`
    - 引数: 出力先フォルダ、最終構造の元素・座標・コメント、`symbols`・`coords_history`・`energies` を持つ最適化結果（`common_backend.optimization.OptimizationResult`、またはその子クラス）
    - 戻り値: 最終構造とトラジェクトリのパス
    - 目的: 構造最適化の標準の出力 2 ファイルを同じ名前・形式で書き出す
    - 呼出先: `FINAL_STRUCTURE_FILENAME`（定数）、`write_final_structure`、`TRAJECTORY_FILENAME`（定数）、`write_trajectory`
    - 呼出元: `pyscf_backend.pipeline.run_calculation`、`uma_backend.uma_pipeline.run_calculation`
    - 関連テスト: `tests/test_optimization.py`、`tests/test_writer_xyz.py`

  - `xyz_string(symbols, coords, comment: str = "") -> str`
    - 引数: 元素記号のリスト、座標のリスト、任意のコメント
    - 戻り値: XYZ 形式の文字列（末尾に改行つき）
    - 目的: ファイルに書き出さず、py3Dmol などへ直接渡すための XYZ 文字列を作る
    - 呼出先: `_format_xyz_block`
    - 呼出元: なし
    - 関連テスト: `tests/test_writer_xyz.py`

  - `multiframe_xyz_string(symbols, coords_list, comments = None) -> str`
    - 引数: 元素記号のリスト、複数フレームの座標、任意のコメントのリスト
    - 戻り値: 多フレームの XYZ 文字列
    - 目的: py3Dmol の振動アニメーション用に、複数フレームを 1 つの文字列にまとめる
    - 呼出先: `_format_xyz_block`
    - 呼出元: `gui.plot_common.render_vibration`
    - 関連テスト: `tests/test_writer_xyz.py`

### gui

画面の層。ipywidgets・Colab の JavaScript 連携・3D 表示・SVG グラフを扱う。共通の画面部品（`parts`・`inputs`・`outputs`・`colab_widgets`・`energy_plot`・`plot_common`）は計算エンジンのパッケージを import せず、各画面（`pyscf_screen`・`uma_screen`）だけが自分の計算エンジンを呼び出す。ノートブックは、このパッケージの画面を呼び出す。

- `__init__.py`

  画面パッケージの識別用モジュール。公開関数は持たず、何も import しない（import しただけで ipywidgets が必要にならないようにするため）。

- `colab_widgets.py`

  Colab の JavaScript と Python コールバックを接続する部品。ipywidgets の表示差異を回避するため、ドラッグ＆ドロップ領域を外部 JavaScript ライブラリなしで生成する。クリックできるエネルギーグラフは `energy_plot.py` が担当する。

  - `ALLOWED_STRUCTURE_EXTENSIONS`
    - 目的: ドロップ・選択を受け付ける構造ファイルの拡張子（`.xyz`・`.com`・`.gjf`・`.pdb`）
    - 呼出先: なし
    - 呼出元: `build_drop_zone_html`（定数）、`parse_dropped_payload`（定数）
    - 関連テスト: なし

  - `MAX_DROPPED_FILE_BYTES`
    - 目的: ドロップされる構造ファイルの大きさの上限（5 MB）
    - 呼出先: なし
    - 呼出元: `build_drop_zone_html`（定数）、`parse_dropped_payload`（定数）
    - 関連テスト: `tests/test_colab_widgets.py`

  - `is_colab() -> bool`
    - 引数: なし
    - 戻り値: Colab 実行時は `True`
    - 目的: Colab 専用 UI の表示可否を判定する
    - 呼出先: なし
    - 呼出元: なし
    - 関連テスト: なし

  - `register_callback(func, prefix: str = "qchem_cb") -> str | None`
    - 引数: JavaScript から呼ばれる関数、登録名接頭辞
    - 戻り値: Colab では一意なコールバック名、それ以外は `None`
    - 目的: `google.colab.output.register_callback` を安全に隠蔽する
    - 呼出先: なし
    - 呼出元: `gui.parts.EnergyStructureViewer.__init__`、`gui.parts.StructureFileInput.__init__`
    - 関連テスト: なし

  - `check_safe_id(value: str, label: str) -> str`
    - 引数: DOM 識別子・コールバック名と表示名
    - 戻り値: 検証済みの識別子
    - 目的: JavaScript に埋め込む識別子を英数字とアンダースコアに限定し、注入を防ぐ
    - 呼出先: なし
    - 呼出元: `build_drop_zone_html`、`gui.energy_plot.build_energy_plot_html`
    - 関連テスト: `tests/test_colab_widgets.py`、`tests/test_energy_plot.py`

  - `parse_dropped_payload(payload: dict, allowed_extensions = ALLOWED_STRUCTURE_EXTENSIONS, max_bytes: int = MAX_DROPPED_FILE_BYTES) -> tuple[str, bytes]`
    - 引数: ファイル名と Base64 本文を含むブラウザ通知、許可拡張子、最大サイズ
    - 戻り値: 正規化済みファイル名とバイト列
    - 目的: ドロップ入力の拡張子・サイズ・Base64 を検証する
    - 技術選定: ブラウザからの入力を直接ファイルとして扱わず、上限を設けて安全にする
    - 呼出先: `ALLOWED_STRUCTURE_EXTENSIONS`（定数）、`MAX_DROPPED_FILE_BYTES`（定数）
    - 呼出元: `gui.parts.StructureFileInput._on_file_dropped`
    - 関連テスト: `tests/test_colab_widgets.py`

  - `build_drop_zone_html(callback_name: str, uid: str | None = None, extensions = ALLOWED_STRUCTURE_EXTENSIONS, max_bytes: int = MAX_DROPPED_FILE_BYTES) -> str`
    - 引数: 登録済みコールバック名、DOM 識別子、許可拡張子、最大サイズ
    - 戻り値: JavaScript を含むドロップ領域 HTML
    - 目的: ドロップとクリック選択の両方を受け付ける Colab UI を作る
    - 呼出先: `ALLOWED_STRUCTURE_EXTENSIONS`（定数）、`MAX_DROPPED_FILE_BYTES`（定数）、`check_safe_id`
    - 呼出元: `gui.parts.StructureFileInput.__init__`
    - 関連テスト: `tests/test_colab_widgets.py`

- `energy_plot.py`

  クリックできるエネルギー収束グラフ（SVG）と、その目盛りの計算。外部 JavaScript ライブラリに頼らず、素の SVG と Colab の `google.colab.kernel.invokeFunction` だけで点のクリックを Python 側へ伝える。

  - `_nice_step(raw_step: float) -> float`
    - 引数: 目盛りの刻み幅の候補（正の数）
    - 戻り値: 候補以上で最小の、1・2・5 × 10ⁿ の刻み幅
    - 目的: SVG 軸の目盛りを、きりの良い間隔にする内部補助関数
    - 呼出先: なし
    - 呼出元: `nice_ticks`
    - 関連テスト: なし

  - `nice_ticks(vmin: float, vmax: float, target: int = 5, integer_only: bool = False) -> tuple[list[float], float]`
    - 引数: 値域、目標目盛り数、整数目盛り限定フラグ
    - 戻り値: 目盛り値と刻み
    - 目的: SVG グラフの読みやすい軸目盛りを作る
    - 呼出先: `_nice_step`
    - 呼出元: `build_energy_plot_html`
    - 関連テスト: `tests/test_energy_plot.py`

  - `_format_tick(value: float, step: float) -> str`
    - 引数: 目盛り値、刻み幅
    - 戻り値: 整形済みの文字列（刻み幅に応じた小数点以下の桁数。「-0」は避ける）
    - 目的: SVG 軸の目盛りの表示を安定させる内部補助関数
    - 呼出先: なし
    - 呼出元: `build_energy_plot_html`
    - 関連テスト: なし

  - `build_energy_plot_html(energies_hartree, selected_index: int | None = None, callback_name: str | None = None, uid: str | None = None, width: int = 640, height: int = 360) -> str`
    - 引数: エネルギー履歴、選択点、任意のクリックコールバック、DOM 識別子、描画サイズ
    - 戻り値: SVG と任意のクリック JavaScript を含む HTML
    - 目的: 点選択で対応構造を示すエネルギー収束グラフを描く
    - 技術選定: Colab で FigureWidget が空表示になる事例を避け、素の SVG を採用する
    - 呼出先: `common_backend.energy.relative_energies_kcal`、`gui.colab_widgets.check_safe_id`、`nice_ticks`、`_format_tick`
    - 呼出元: `gui.parts.EnergyStructureViewer._draw_energy_plot`
    - 関連テスト: `tests/test_energy_plot.py`

- `inputs.py`

  ipywidgets 本体に依存しない、GUI の「入力」まわりの関数。アップロードされたファイルの取り出し、構造の読込みと検証、電荷の表示と読取り。

  - `extract_uploaded_file(upload_widget, dropped_file: dict | None = None) -> tuple[bytes, str]`
    - 引数: FileUpload 相当の値、任意のドロップ済みファイル
    - 戻り値: 内容とファイル名
    - 目的: ipywidgets 7/8 の異なる値形式を吸収し、ドロップ入力を優先する
    - 呼出先: `common_backend.io_reader.StructureError`
    - 呼出元: `gui.parts.StructureFileInput.read`
    - 関連テスト: `tests/test_gui_input.py`

  - `read_uploaded_structure(content: bytes, filename: str) -> Structure`
    - 引数: 構造ファイルの中身、ファイル名
    - 戻り値: 読み込んだ構造
    - 目的: 拡張子つきの一時ファイルへ書き出して読み込み、一時ファイルを削除する。原子間距離や電荷・多重度の検証はしない（受け取った構造の自動表示に使う）
    - 呼出先: `common_backend.io_reader.read_structure`
    - 呼出元: `load_uploaded_structure`、`gui.parts.StructureFileInput._update_preview`
    - 関連テスト: `tests/test_gui_input.py`

  - `describe_structure(structure: Structure, filename: str) -> str`
    - 引数: 構造、ファイル名
    - 戻り値: 「ファイル: …  原子数: …  組成: …」の 1 行
    - 目的: 計算前のログと、受け取った構造の表示で、同じ概要文を使う
    - 呼出先: なし
    - 呼出元: `load_uploaded_structure`、`gui.parts.StructureFileInput._update_preview`
    - 関連テスト: `tests/test_gui_input.py`

  - `load_uploaded_structure(content: bytes, filename: str, charge: int, multiplicity: int, min_distance: float, log = print) -> Structure`
    - 引数: 構造ファイルの中身、ファイル名、電荷、スピン多重度、原子間距離の下限[Å]、ログ出力関数
    - 戻り値: 検証済みの共通構造
    - 目的: 構造の読込み（`read_uploaded_structure`）、概要のログ出力（`describe_structure`）、原子間距離の検証、電荷・多重度の検証を、PySCF 版・UMA 版で同じ手順にする。エンジンごとに異なる確認（遷移金属の判定など）は呼出元で行う
    - 呼出先: `read_uploaded_structure`、`describe_structure`、`common_backend.io_reader.validate_structure`、`common_backend.io_reader.validate_charge_and_multiplicity`
    - 呼出元: `gui.pyscf_screen.build_app`、`gui.uma_screen.build_app`
    - 関連テスト: `tests/test_gui_input.py`

  - `ChargeInputError(ValueError)`
    - 目的: GUI の電荷文字列が整数として読めないことを示す例外。メッセージはそのまま画面に表示できる
    - 呼出先: なし
    - 呼出元: `parse_charge`、`gui.parts.ChargeInput._on_text_changed`（例外の捕捉）
    - 関連テスト: `tests/test_gui_input.py`

  - `format_charge(value: int) -> str`
    - 引数: 電荷の整数
    - 戻り値: 表示用の符号つき文字列（正の値だけ `+1` の形。0 は `0`、負の値は `-1`）
    - 目的: 電荷の入力欄の表示を `+1` の形にそろえる
    - 呼出先: なし
    - 呼出元: `gui.parts.ChargeInput.__init__`、`gui.parts.ChargeInput._on_text_changed`、`gui.parts.ChargeInput._step`
    - 関連テスト: `tests/test_gui_input.py`

  - `parse_charge(text: str) -> int`
    - 引数: 利用者が入力した文字列
    - 戻り値: 読み取った電荷の整数
    - 目的: `+1`、全角数字、Unicode の符号、符号と数字の間の空白を含む電荷入力を安全に読み取る。整数として読み取れないときは `ChargeInputError` を送出する
    - 呼出先: `ChargeInputError`
    - 呼出元: `gui.parts.ChargeInput._on_text_changed`
    - 関連テスト: `tests/test_gui_input.py`

- `outputs.py`

  ipywidgets 本体に依存しない、GUI の「出力」（ダウンロード）まわりの関数。ファイル名の整形と既定名、最終構造・トラジェクトリのダウンロード項目。

  - `sanitize_filename_stem(raw: str) -> str`
    - 引数: 任意のファイル名幹
    - 戻り値: 禁止文字を除いた名前、空なら `result`
    - 目的: ダウンロード名を安全にする
    - 呼出先: なし
    - 呼出元: `gui.parts.DownloadPanel.show`
    - 関連テスト: `tests/test_gui_output.py`

  - `default_download_stem(input_filename: str) -> str`
    - 引数: 入力ファイル名
    - 戻り値: `<入力名>_result` 形式の既定名
    - 目的: 出力ファイル群の名前を入力に対応付ける。PySCF 版・UMA 版の両方で同じ既定名（`<入力名>_result`）を使う
    - 呼出先: なし
    - 呼出元: `gui.pyscf_screen.build_app`、`gui.uma_screen.build_app`
    - 関連テスト: `tests/test_gui_output.py`

  - `xyz_download_items(final_xyz_path: str, trajectory_path: str) -> list[tuple[str, str, str, str]]`
    - 引数: 最終構造・トラジェクトリのパス
    - 戻り値: `DownloadPanel.show` に渡す項目（説明、パス、ダウンロード名の末尾、ボタン名）2 件
    - 目的: 両 GUI で共通の 2 つのダウンロード項目を 1 か所で定義する。エンジンごとの項目（molden・計算ログ）は呼出元が足す
    - 呼出先: なし
    - 呼出元: `gui.pyscf_screen.build_app`、`gui.uma_screen.build_app`
    - 関連テスト: `tests/test_gui_output.py`

- `parts.py`

  PySCF 版と UMA 版で共有する ipywidgets の複合部品。

  - `dropdown_from_list(items: list[dict], description: str, width: str = "420px") -> ipywidgets.Dropdown`
    - 引数: `label`/`key` を持つ設定項目、表示名、幅
    - 戻り値: ドロップダウン
    - 目的: YAML の選択肢を画面へ変換する
    - 呼出先: なし
    - 呼出元: `gui.pyscf_screen.build_app`、`gui.uma_screen.build_app`
    - 関連テスト: `tests/test_gui_parts.py`

  - `ChargeInput(value: int = 0, description: str = "電荷")`
    - 引数: 初期電荷、表示名
    - 戻り値: `controls`（入力欄と −1/+1 ボタンの HBox）、`message`（エラー表示欄）、`value`（現在の電荷の整数）を公開する部品
    - 目的: 電荷を `+1` の形で表示するテキスト入力欄を PySCF 版・UMA 版で共通にする。Enter／欄外クリックで値を整え、読み取れない入力は直前の値へ戻してメッセージを出す
    - 技術選定: 数値ウィジェット（IntText）では正の値に `+` を付けて表示できないため、Text と関数（`gui.inputs.format_charge`, `parse_charge`）を組み合わせる
    - 呼出先: `gui.inputs.format_charge`、`ChargeInput._on_text_changed`（コールバックとして登録）、`ChargeInput._step`
    - 呼出元: `gui.pyscf_screen.build_app`、`gui.uma_screen.build_app`
    - 関連テスト: `tests/test_gui_parts.py`
    - `value`（プロパティ）
      - 戻り値: 現在の電荷（整数）
      - 目的: 入力欄で読み取れた最後の値を返す。読み取れない入力があっても、直前の有効な値のままになる
      - 呼出先: なし
      - 呼出元: `gui.pyscf_screen.build_app`（属性として参照）、`gui.uma_screen.build_app`（属性として参照）
      - 関連テスト: なし
    - `_on_text_changed(change: dict) -> None`
      - 引数: ipywidgets の値変更通知
      - 戻り値: なし
      - 目的: 入力文字列を `parse_charge` で読み取り、読み取れたら「+1」の形に整え、読み取れなければ直前の値に戻してメッセージを出す内部イベント処理
      - 呼出先: `gui.inputs.parse_charge`、`gui.inputs.ChargeInputError`（例外の捕捉）、`gui.inputs.format_charge`
      - 呼出元: `ChargeInput.__init__`（コールバックとして登録）
      - 関連テスト: なし
    - `_step(delta: int) -> None`
      - 引数: 増減量（−1／+1 ボタンから ±1）
      - 戻り値: なし
      - 目的: −1／+1 ボタンの処理。値を増減して、入力欄を「+1」の形で更新する内部イベント処理
      - 呼出先: `gui.inputs.format_charge`
      - 呼出元: `ChargeInput.__init__`
      - 関連テスト: なし

  - `MultiplicityInput(value: int = 1, description: str = "スピン多重度")`
    - 引数: 初期スピン多重度、表示名
    - 戻り値: `widget`（整数の入力欄 IntText）と `value`（現在の多重度の整数）を公開する部品
    - 目的: 電荷の入力欄と同じ幅・説明欄の幅にそろえ、PySCF 版・UMA 版で同じ見た目にする。値の範囲や電子数との整合は、この部品ではなく計算前の検証（`gui.inputs.load_uploaded_structure`）で確認する
    - 呼出先: なし
    - 呼出元: `gui.pyscf_screen.build_app`、`gui.uma_screen.build_app`
    - 関連テスト: `tests/test_gui_parts.py`
    - `value`（プロパティ）
      - 戻り値: 現在のスピン多重度（整数）
      - 目的: 入力欄（`IntText`）の値を整数で返す
      - 呼出先: なし
      - 呼出元: `gui.pyscf_screen.build_app`（属性として参照）、`gui.uma_screen.build_app`（属性として参照）
      - 関連テスト: なし

  - `StructureFileInput(callback_prefix: str = "qchem_drop")`
    - 引数: Colab コールバック名接頭辞
    - 戻り値: `widgets` 属性に、Colab ではドロップ領域・状態表示・説明・構造の表示欄を、それ以外ではファイル選択ボタン（`upload`）・説明・構造の表示欄を並べる入力部品
    - 目的: ドラッグ＆ドロップ（枠をクリックしても選べる）と通常のファイル選択を統一する
    - 技術選定: Colab では `gui.colab_widgets`、それ以外では標準 FileUpload をフォールバックにする。Colab では、枠をクリックしても選べるため、枠の下のファイル選択ボタンは置かない
    - 呼出先: `gui.colab_widgets.register_callback`、`StructureFileInput._on_file_dropped`（コールバックとして登録）、`gui.colab_widgets.build_drop_zone_html`、`StructureFileInput._on_upload_changed`（コールバックとして登録）
    - 呼出元: `gui.pyscf_screen.build_app`、`gui.uma_screen.build_app`
    - 関連テスト: `tests/test_gui_parts.py`
    - `_on_file_dropped(payload: dict) -> None`
      - 引数: Colab の JavaScript から渡されるペイロード（ファイル名と Base64 本文）
      - 戻り値: なし（Colab のコールバックとして、受取結果を返す）
      - 目的: ドロップされたファイルを検証して最新の入力として記録し、構造の表示を更新する。検証に失敗したときは、理由を表示して、記録を無効にする
      - 呼出先: `gui.colab_widgets.parse_dropped_payload`、`StructureFileInput._clear_preview`、`StructureFileInput._update_preview`
      - 呼出元: `StructureFileInput.__init__`（コールバックとして登録）
      - 関連テスト: なし
    - `_on_upload_changed(change: dict) -> None`
      - 引数: ipywidgets の値変更通知
      - 戻り値: なし
      - 目的: ボタンで選び直されたファイルを最新の入力とし、前のドロップ入力を無効にして、入力方法間の優先順位（最後に受け取ったものを使う）を保つ。構造の表示も更新する
      - 呼出先: `StructureFileInput._update_preview`、`StructureFileInput._clear_preview`
      - 呼出元: `StructureFileInput.__init__`（コールバックとして登録）
      - 関連テスト: なし
    - `_clear_preview() -> None`
      - 引数: なし
      - 戻り値: なし
      - 目的: `preview_output` の表示を消す（ファイルの受取りに失敗したとき、ボタンの選択が空になったとき）
      - 呼出先: なし
      - 呼出元: `StructureFileInput._on_file_dropped`、`StructureFileInput._on_upload_changed`
      - 関連テスト: なし
    - `_update_preview() -> None`
      - 引数: なし
      - 戻り値: なし
      - 目的: 受け取った構造ファイルを（計算前の検証はせずに）読み込み、概要（原子数・組成）と 3D 表示を `preview_output`（`widgets` の最後）に出す。読み込めないときは理由を表示し、ファイルの受取り自体は妨げない
      - 呼出先: `StructureFileInput.read`、`gui.inputs.read_uploaded_structure`、`gui.inputs.describe_structure`、`gui.plot_common.render_single_structure`、`common_backend.io_reader.StructureError`（例外の捕捉）
      - 呼出元: `StructureFileInput._on_file_dropped`、`StructureFileInput._on_upload_changed`
      - 関連テスト: なし
    - `read() -> tuple[bytes, str]`
      - 引数: なし
      - 戻り値: 最後に選択された構造ファイルの内容と名前
      - 目的: 計算パイプラインに入力を渡す
      - 呼出先: `gui.inputs.extract_uploaded_file`
      - 呼出元: `StructureFileInput._update_preview`、`gui.pyscf_screen.build_app`、`gui.uma_screen.build_app`
      - 関連テスト: なし

  - `default_step_label(step_index: int, relative_energy_kcal: float, result) -> str`
    - 引数: ステップ番号、相対エネルギー、最適化結果
    - 戻り値: 構造表示の説明文
    - 目的: 共通の標準ラベルを作る
    - 呼出先: なし
    - 呼出元: `EnergyStructureViewer.__init__`（コールバックとして登録）
    - 関連テスト: なし

  - `EnergyStructureViewer(callback_prefix: str = "qchem_plot", step_label = None)`
    - 引数: Colab コールバック接頭辞、任意の構造表示ラベル生成関数
    - 戻り値: `widget` 属性でグラフ、スライダー、3D 表示を公開する部品
    - 目的: エネルギー点、スライダー、対応構造を同期する
    - 技術選定: SVG のクリック連携とスライダーの双方を提供し、通信失敗時も構造選択を可能にする
    - 呼出先: `default_step_label`（コールバックとして登録）、`EnergyStructureViewer._on_slider_changed`（コールバックとして登録）、`gui.colab_widgets.register_callback`、`EnergyStructureViewer._on_plot_clicked`（コールバックとして登録）
    - 呼出元: `gui.pyscf_screen.build_app`、`gui.uma_screen.build_app`
    - 関連テスト: `tests/test_gui_parts.py`
    - `show(result) -> None`
      - 引数: `energies` と `coords_history` を持つ最適化結果
      - 戻り値: なし
      - 目的: 対応するエネルギー・座標だけを UI に反映する
      - 呼出先: `EnergyStructureViewer._draw_energy_plot`、`EnergyStructureViewer._show_structure_at_step`
      - 呼出元: `gui.pyscf_screen.build_app`、`gui.uma_screen.build_app`
      - 関連テスト: なし
    - `reset() -> None`
      - 引数: なし
      - 戻り値: なし
      - 目的: 前回の結果（グラフ・構造・スライダー・保持している結果）を消す。新しい計算を始めるときに呼ぶ
      - 呼出先: なし
      - 呼出元: `gui.pyscf_screen.build_app`、`gui.uma_screen.build_app`
      - 関連テスト: なし
    - `_show_structure_at_step(step_index: int) -> None`
      - 引数: 表示するステップの番号
      - 戻り値: なし
      - 目的: そのステップの構造を、見出し（相対エネルギーなど）つきで 3D 表示する内部処理
      - 呼出先: `common_backend.energy.HARTREE_TO_KCAL_MOL`（定数）、`gui.plot_common.render_single_structure`
      - 呼出元: `EnergyStructureViewer._on_plot_clicked`、`EnergyStructureViewer._on_slider_changed`、`EnergyStructureViewer.show`
      - 関連テスト: なし
    - `_draw_energy_plot(selected_index: int) -> None`
      - 引数: 赤い菱形で強調するステップの番号
      - 戻り値: なし
      - 目的: エネルギー収束グラフ（クリックできる SVG）を描き直す内部処理。描画に失敗しても、スライダーで構造を切り替えられるよう、メッセージだけを出す
      - 呼出先: `gui.energy_plot.build_energy_plot_html`
      - 呼出元: `EnergyStructureViewer._on_slider_changed`、`EnergyStructureViewer.show`
      - 関連テスト: なし
    - `_on_slider_changed(change: dict) -> None`
      - 引数: ipywidgets の値変更通知
      - 戻り値: なし
      - 目的: スライダーの変更に合わせて、構造とグラフを同期する内部イベント処理。点のクリックが原因の変更では、JavaScript 側がすでに赤い菱形を動かしているため、グラフは描き直さない
      - 呼出先: `EnergyStructureViewer._show_structure_at_step`、`EnergyStructureViewer._draw_energy_plot`
      - 呼出元: `EnergyStructureViewer.__init__`（コールバックとして登録）
      - 関連テスト: なし
    - `_on_plot_clicked(index: int) -> None`
      - 引数: クリックされた点の番号（Colab の JavaScript から渡される）
      - 戻り値: なし（Colab のコールバックとして、結果を返す）
      - 目的: グラフ上の点のクリックを受けて、スライダーを動かし、その構造を表示する内部イベント処理。失敗したときは、スライダーを使うよう案内するメッセージを出す
      - 呼出先: `EnergyStructureViewer._show_structure_at_step`
      - 呼出元: `EnergyStructureViewer.__init__`（コールバックとして登録）
      - 関連テスト: なし

  - `VibrationViewer()`
    - 引数: なし
    - 戻り値: `widget` 属性でモード選択と表示ボタンを公開する部品
    - 目的: 振動数解析結果に基づく振動アニメーションを表示する
    - 呼出先: `VibrationViewer._on_button_clicked`（コールバックとして登録）
    - 呼出元: `gui.pyscf_screen.build_app`、`gui.uma_screen.build_app`
    - 関連テスト: `tests/test_gui_parts.py`
    - `reset() -> None`
      - 引数: なし
      - 戻り値: なし
      - 目的: 前回の振動アニメーションの表示を消す。`setup(None, None, None)` と同じ
      - 呼出先: `VibrationViewer.setup`
      - 呼出元: `gui.pyscf_screen.build_app`、`gui.uma_screen.build_app`
      - 関連テスト: なし
    - `setup(freq_result, symbols, coords) -> None`
      - 引数: 振動数結果、元素記号、最終座標
      - 戻り値: なし
      - 目的: 計算の有無とモードに応じて操作部を有効化する
      - 呼出先: なし
      - 呼出元: `VibrationViewer.reset`、`gui.pyscf_screen.build_app`、`gui.uma_screen.build_app`
      - 関連テスト: なし
    - `_on_button_clicked(_) -> None`
      - 引数: ボタンのクリック通知
      - 戻り値: なし
      - 目的: 選択されたモードの振動アニメーションを 3D ビューへ描画する内部イベント処理
      - 呼出先: `gui.plot_common.render_vibration`
      - 呼出元: `VibrationViewer.__init__`（コールバックとして登録）
      - 関連テスト: なし

  - `DownloadPanel(tmp_prefix: str = "qchem_dl_", description_width: str = "280px")`
    - 引数: 一時保存先接頭辞、説明欄の幅
    - 戻り値: `widget` 属性でダウンロード欄を公開する部品
    - 目的: Colab では任意名でダウンロードし、ローカルでは出力パスを表示する
    - 呼出先: なし
    - 呼出元: `gui.pyscf_screen.build_app`、`gui.uma_screen.build_app`
    - 関連テスト: `tests/test_gui_parts.py`
    - `reset() -> None`
      - 引数: なし
      - 戻り値: なし
      - 目的: 前回のダウンロードボタンを消す。新しい計算を始めるときに呼ぶ
      - 呼出先: なし
      - 呼出元: `gui.pyscf_screen.build_app`、`gui.uma_screen.build_app`
      - 関連テスト: なし
    - `show(items, default_stem: str = "") -> None`
      - 引数: （説明、ファイルのパス、ダウンロード名の末尾、ボタンの表示名）の一覧、ファイル名の既定の幹
      - 戻り値: なし
      - 目的: 現在の計算結果に対応するダウンロードの画面を作り直す。各ボタンに、Colab の `files.download` の呼出しを束縛し、すべての出力に同じ安全なファイル名の規則を適用する
      - 呼出先: `gui.outputs.sanitize_filename_stem`
      - 呼出元: `gui.pyscf_screen.build_app`、`gui.uma_screen.build_app`
      - 関連テスト: なし

- `plot_common.py`

  py3Dmol による、計算エンジン非依存の可視化部品（構造・振動アニメーション・原子電荷の色分け）と、原子電荷の HTML の表。引数は、PySCF の Mole などではなく、元素記号・座標・電荷のプレーンな値に限る。エネルギー収束グラフは `gui.energy_plot.build_energy_plot_html` が自前の SVG で描く。原子電荷の関数は、PySCF の Mole などに依存しない。

  - `render_single_structure(symbols, coords, width: int = 500, height: int = 400) -> py3Dmol.view`
    - 引数: 元素記号、Å 座標、表示サイズ
    - 戻り値: 1 構造の 3D ビュー
    - 目的: 選択した最適化ステップを表示する
    - 呼出先: なし
    - 呼出元: `gui.parts.EnergyStructureViewer._show_structure_at_step`、`gui.parts.StructureFileInput._update_preview`
    - 関連テスト: `tests/test_gui_parts.py`、`tests/test_plot_common.py`

  - `render_vibration(symbols, final_coords, frequencies_cm1, normal_modes, mode_index: int = 0, amplitude: float = 0.6, n_frames: int = 20, width: int = 500, height: int = 400) -> tuple[py3Dmol.view, str]`
    - 引数: 最終構造、振動数、正規モード、表示モード、振幅、フレーム数、サイズ
    - 戻り値: 3D ビューと説明文
    - 目的: 選択モードの変位をループ表示する
    - 呼出先: `common_backend.writer_xyz.multiframe_xyz_string`
    - 呼出元: `gui.parts.VibrationViewer._on_button_clicked`
    - 関連テスト: `tests/test_gui_parts.py`、`tests/test_plot_common.py`

  - `atomic_charges_table_html(charges) -> str`
    - 引数: 原子電荷 [(元素記号, 電荷), ...]（原子と同じ順）
    - 戻り値: 原子番号・元素・Mulliken 電荷を並べた HTML の表
    - 目的: 原子電荷を、符号つきの数値の表で示す
    - 呼出先: なし
    - 呼出元: `gui.pyscf_screen.build_app`
    - 関連テスト: `tests/test_plot_common.py`、`tests/test_visualizer.py`

  - `add_atom_charge_labels(view, coords, charges, font_size: int = 12) -> view`
    - 引数: py3Dmol のビュー、Å 単位の座標のリスト、原子電荷 [(元素記号, 電荷), ...]、フォントの大きさ
    - 戻り値: ラベルを追加したビュー
    - 目的: 各原子の位置に、電荷の数値ラベルを描く。正電荷は青系、負電荷は赤系の背景にする
    - 技術選定: PySCF の Mole ではなく、座標と電荷だけを受け取るため、電荷を出すエンジンから独立している
    - 呼出先: なし
    - 呼出元: `render_charges`
    - 関連テスト: `tests/test_plot_common.py`、`tests/test_visualizer.py`

  - `_charge_gradient_color(charge: float, max_abs_charge: float) -> str`
    - 引数: 電荷、その分子の最大絶対電荷
    - 戻り値: 色（`#rrggbb`）
    - 目的: 電荷を、青（正）・緑（中性付近）・赤（負）のグラデーション色にする内部補助関数。最大絶対電荷を基準に −1〜+1 に正規化して、緑から青または赤へ線形補間する
    - 呼出先: なし
    - 呼出元: `add_atom_charge_spheres`
    - 関連テスト: `tests/test_plot_common.py`、`tests/test_visualizer.py`

  - `add_atom_charge_spheres(view, coords, charges, opacity: float = 0.85, size_variation: float = 0.2) -> view`
    - 引数: py3Dmol のビュー、Å 単位の座標のリスト、原子電荷 [(元素記号, 電荷), ...]、不透明度、大きさの変化の幅
    - 戻り値: 球を追加したビュー
    - 目的: 原子ごとに、電荷に応じた色の半透明の球を重ねる。球の大きさは、元素ごとのファンデルワールス半径を基準にし、電荷の絶対値が大きいほど、わずかに大きくする
    - 技術選定: 電子密度そのものは符号を持たないため、符号を持つ量として Mulliken 電荷を使う。静電ポテンシャルで表面を塗り分ける方法（ESP マッピング）は、3Dmol.js 側の API を実機で検証できていないため、確実に動くこの球の表示にしている
    - 呼出先: `_charge_gradient_color`
    - 呼出元: `render_charges`
    - 関連テスト: `tests/test_plot_common.py`、`tests/test_visualizer.py`

  - `render_charges(symbols, coords, charges, show_labels: bool = True, width: int = 500, height: int = 400) -> py3Dmol.view`
    - 引数: 元素記号のリスト、Å 単位の座標のリスト、原子電荷 [(元素記号, 電荷), ...]、ラベルの表示の有無、表示の大きさ
    - 戻り値: 電荷を色分けした 3D ビュー
    - 目的: 構造（ball and stick）の上に、電荷に応じた色の球と、（任意で）数値ラベルを重ねて表示する。原子数が多いと、ラベルが重なって見づらいため、ラベルは非表示にできる
    - 呼出先: `add_atom_charge_spheres`、`add_atom_charge_labels`
    - 呼出元: `gui.pyscf_screen.build_app`
    - 関連テスト: `tests/test_plot_common.py`、`tests/test_visualizer.py`

- `pyscf_screen.py`

  PySCF 版アプリケーションの画面組み立て役。入力値の収集、アップロードされたファイルの読込みと検証、結果の表示（可視化・ダウンロード）、例外の利用者向けメッセージへの変換だけを行い、計算の流れは `pyscf_backend/pipeline.py`、共通画面部品(`gui.parts` など)を使う。

  - `build_app() -> ipywidgets.VBox`
    - 引数: なし
    - 戻り値: 完成した PySCF GUI
    - 目的: YAML 設定から画面を構成し、実行ボタンで `pyscf_backend.pipeline.run_calculation` を呼び、結果を可視化・ダウンロードへ接続する。実行ボタンは、計算中は無効化して二重実行を防ぐ。計算の開始時に、前回の結果の表示（グラフ・振動アニメーション・分子軌道・原子電荷・ダウンロード）をすべて消す
    - 技術選定: GUI は薄いエントリーポイントに留め、再利用可能な画面部品・計算部品を分離する
    - 呼出先: `common_backend.config_loader.load_yaml`、`common_backend.version.__version__`（定数）、`gui.parts.StructureFileInput`、`gui.parts.dropdown_from_list`、`gui.parts.ChargeInput`、`gui.parts.MultiplicityInput`、`gui.parts.EnergyStructureViewer`、`gui.parts.VibrationViewer`、`gui.parts.DownloadPanel`、`gui.parts.EnergyStructureViewer.reset`、`gui.parts.VibrationViewer.reset`、`gui.parts.DownloadPanel.reset`、`pyscf_backend.analysis_pyscf.orbital_choices`、`pyscf_backend.visualizer_pyscf.render_orbital`、`gui.plot_common.render_charges`、`pyscf_backend.analysis_pyscf.compute_mulliken_charges`、`gui.plot_common.atomic_charges_table_html`、`gui.parts.ChargeInput.value`（属性として参照）、`gui.parts.MultiplicityInput.value`（属性として参照）、`gui.parts.StructureFileInput.read`、`gui.inputs.load_uploaded_structure`、`pyscf_backend.pipeline.CalculationSettings`、`pyscf_backend.pipeline.run_calculation`、`gui.parts.EnergyStructureViewer.show`、`gui.parts.VibrationViewer.setup`、`gui.parts.DownloadPanel.show`、`gui.outputs.xyz_download_items`、`gui.outputs.default_download_stem`、`common_backend.io_reader.StructureError`（例外の捕捉）、`pyscf_backend.engine.SCFConvergenceError`（例外の捕捉）
    - 呼出元: `ColabApp.ipynb`
    - 関連テスト: なし

- `uma_screen.py`

  UMA 版アプリケーションの画面組み立て役。PySCF 版と同じ入力・グラフ・振動・ダウンロード部品を再利用し、UMA 固有のモデル選択を持つ。入力値の収集、アップロードされたファイルの読込みと検証、結果の表示、例外の利用者向けメッセージへの変換だけを行い、計算の流れは `uma_backend/uma_pipeline.py` に委譲する。

  - `build_app() -> ipywidgets.VBox`
    - 引数: なし
    - 戻り値: 完成した UMA GUI
    - 目的: 実行ボタンで `uma_backend.uma_pipeline.run_calculation` を呼び、結果を可視化・ダウンロードへ接続する。実行ボタンは、計算中は無効化して二重実行を防ぐ。計算の開始時に、前回の結果の表示（グラフ・振動アニメーション・ダウンロード）をすべて消す
    - 技術選定: トークンは GUI で保持せず環境変数だけから読むため、ノートブック保存時の漏えいを避ける
    - 呼出先: `common_backend.config_loader.load_yaml`、`common_backend.version.__version__`（定数）、`gui.parts.StructureFileInput`、`gui.parts.dropdown_from_list`、`gui.parts.ChargeInput`、`gui.parts.MultiplicityInput`、`gui.parts.EnergyStructureViewer`、`gui.parts.VibrationViewer`、`gui.parts.DownloadPanel`、`gui.parts.EnergyStructureViewer.reset`、`gui.parts.VibrationViewer.reset`、`gui.parts.DownloadPanel.reset`、`gui.parts.ChargeInput.value`（属性として参照）、`gui.parts.MultiplicityInput.value`（属性として参照）、`gui.parts.StructureFileInput.read`、`gui.inputs.load_uploaded_structure`、`uma_backend.uma_pipeline.CalculationSettings`、`uma_backend.uma_pipeline.run_calculation`、`gui.parts.EnergyStructureViewer.show`、`gui.parts.VibrationViewer.setup`、`gui.parts.DownloadPanel.show`、`gui.outputs.xyz_download_items`、`gui.outputs.default_download_stem`、`common_backend.io_reader.StructureError`（例外の捕捉）、`uma_backend.uma_hf.UmaSetupError`（例外の捕捉）
    - 呼出元: `ColabApp_UMA.ipynb`
    - 関連テスト: なし

### pyscf_backend

PySCF を計算エンジンとする ab initio 計算パッケージ。`common_backend` を共通基盤として利用する。

- `__init__.py`

  パッケージの説明だけを書き、何も import しない。他のモジュールの名前を別名として公開しない（設定の読み込みは `common_backend.config_loader`、バージョンは `common_backend.version` を、使う側が直接 import する）。

- `engine.py`

  PySCF の Mole と SCF を構築・実行し、GPU4PySCF が使えなければ CPU へ戻す。

  - `TRANSITION_METAL_SYMBOLS`
    - 目的: PySCF 版が未対応の遷移金属元素（3d・4d・5d の一部）の元素記号の集合。扱える元素の範囲はエンジンごとに決まるため、UMA 版とは別に、このパッケージに置く
    - 呼出先: なし
    - 呼出元: `contains_transition_metal`（定数）
    - 関連テスト: なし

  - `contains_transition_metal(structure: Structure) -> bool`
    - 引数: 構造
    - 戻り値: PySCF 版が未対応の遷移金属元素（3d・4d・5d の一部）を含むか
    - 目的: 計算を始める前に、ECP 付きの基底関数が未登録の元素を、利用者へ案内するために判定する。扱える元素の範囲はエンジンごとに決まるため、このパッケージに置く
    - 呼出先: `TRANSITION_METAL_SYMBOLS`（定数）
    - 呼出元: `pyscf_backend.pipeline.run_calculation`
    - 関連テスト: `tests/test_engine.py`

  - `SCFConvergenceError(RuntimeError)`
    - 目的: 再試行後にも SCF が収束しない場合の利用者向け例外
    - 呼出先: なし
    - 呼出元: `gui.pyscf_screen.build_app`（例外の捕捉）、`run_scf`
    - 関連テスト: なし

  - `_load_functional(functional_key: str) -> dict`
    - 引数: `functionals.yaml` の手法キー
    - 戻り値: 対応する設定の辞書。登録がなければ `ValueError`
    - 目的: YAML から計算手法の設定を探す内部補助関数
    - 呼出先: `common_backend.config_loader.load_yaml`
    - 呼出元: `build_scf`
    - 関連テスト: なし

  - `_load_basis(basis_key: str) -> dict`
    - 引数: `basis_sets.yaml` の基底関数キー
    - 戻り値: 対応する設定の辞書。登録がなければ `ValueError`
    - 目的: YAML から基底関数の設定を探す内部補助関数
    - 呼出先: `common_backend.config_loader.load_yaml`
    - 呼出元: `build_mole`
    - 関連テスト: なし

  - `build_mole(structure: common_backend.io_reader.Structure, charge: int, multiplicity: int, basis_key: str, verbose: int = 0) -> pyscf.gto.Mole`
    - 引数: 共通構造、電荷、多重度、基底関数キー、PySCF 詳細度
    - 戻り値: 構築済み Mole
    - 目的: YAML の基底関数・ECP を計算入力へ変換する
    - 技術選定: `cart=True` により 6D/10F の Molden 互換出力を優先する
    - 呼出先: `_load_basis`
    - 呼出元: `pyscf_backend.pipeline.run_calculation`
    - 関連テスト: `tests/test_analysis_pyscf.py`、`tests/test_pipeline.py`

  - `_try_import_gpu4pyscf() -> module | None`
    - 引数: なし
    - 戻り値: GPU4PySCF のモジュール。インポートに失敗したら `None`
    - 目的: GPU の任意依存を分離する内部補助関数。インポートできなくても、例外は出さず、CPU の計算に切り替えさせる
    - 呼出先: なし
    - 呼出元: `build_scf`
    - 関連テスト: なし

  - `build_scf(mol, functional_key: str, try_gpu: bool = True) -> tuple[object, bool, str]`
    - 引数: Mole、手法キー、GPU 試行フラグ
    - 戻り値: SCF オブジェクト、GPU 使用有無、表示用メッセージ
    - 目的: HF/DFT と閉殻/開殻を選び SCF を初期化する
    - 技術選定: GPU 初期化失敗は計算を中断せず CPU にフォールバックする
    - 呼出先: `_load_functional`、`_try_import_gpu4pyscf`
    - 呼出元: `pyscf_backend.optimize.run_geometry_optimization`、`pyscf_backend.pipeline.run_calculation`
    - 関連テスト: `tests/test_pipeline.py`

  - `run_scf(mf, defaults: dict, dm0 = None) -> object`
    - 引数: SCF オブジェクト、収束設定、任意の初期密度行列
    - 戻り値: 収束済み SCF オブジェクト
    - 目的: 既定条件で SCF を実行し、失敗時は緩和条件とレベルシフトで一度再試行する
    - 呼出先: `SCFConvergenceError`
    - 呼出元: `pyscf_backend.pipeline.run_calculation`
    - 関連テスト: `tests/test_pipeline.py`

- `optimize.py`

  - `OptimizationResult(common_backend.optimization.OptimizationResult)`
    - 引数: なし
    - 戻り値: 共通の項目に加えて、`mol_final`（最適化後の Mole）、`used_gpu`（GPU4PySCF で最適化したか）、`gpu_message`（GPU の使用・フォールバックの説明）、`dm0_guess`（再計算用の密度行列。取得できなければ `None`）を持つ結果
    - 目的: PySCF 版の構造最適化の結果。共通の親クラスに、最終 Mole・GPU 情報・再計算用密度行列を足す
    - 呼出先: なし
    - 呼出元: `run_geometry_optimization`
    - 関連テスト: `tests/test_optimization.py`、`tests/test_pipeline.py`

  - `_to_numpy(arr) -> numpy.ndarray`
    - 引数: NumPy または CuPy の配列
    - 戻り値: CPU 上の NumPy 配列
    - 目的: GPU4PySCF が返す CuPy 配列を、CPU に転送して NumPy 配列にそろえる内部補助関数
    - 呼出先: なし
    - 呼出元: `run_geometry_optimization`
    - 関連テスト: なし

  - `_make_callback(result: OptimizationResult) -> callable`
    - 引数: 結果を入れる `OptimizationResult`
    - 戻り値: geomeTRIC の各ステップで呼ばれるコールバック関数
    - 目的: 各最適化点のエネルギーと座標を、結果に記録する。1 ステップの記録に失敗しても、最適化自体は止めない
    - 呼出先: なし
    - 呼出元: `run_geometry_optimization`
    - 関連テスト: なし

  - `run_geometry_optimization(mol, functional_key: str, defaults: dict, try_gpu: bool = True) -> OptimizationResult`
    - 引数: 初期 Mole、手法キー、設定、GPU 試行フラグ
    - 戻り値: 最適化結果
    - 目的: geomeTRIC による構造最適化と履歴記録を行う
    - 技術選定: 内部座標を使う geomeTRIC を採用し、有機分子の収束性を優先する
    - 呼出先: `OptimizationResult`、`pyscf_backend.engine.build_scf`、`_make_callback`、`_to_numpy`
    - 呼出元: `pyscf_backend.pipeline.run_calculation`
    - 関連テスト: `tests/test_pipeline.py`

- `freq.py`

  - `_get(d: dict, *keys: str, default = None) -> object`
    - 引数: PySCF の結果辞書、候補キー、既定値
    - 戻り値: 最初に見つかった値または既定値
    - 目的: PySCF の版により変わる結果キーを吸収する内部補助関数
    - 呼出先: なし
    - 呼出元: `run_frequency_analysis`
    - 関連テスト: なし

  - `_signed_wavenumber(f) -> float`
    - 引数: 振動数 [cm^-1]（実数・複素数のどちらでもよい）
    - 戻り値: 虚振動を負の値にした実数の振動数。PySCF は虚振動を、実部が 0 の複素数で返すため、虚部の大きさを負の値にする
    - 目的: 虚振動が 0.0 になって検出されない誤りを防ぐ（`common_backend.vibration` と同じ「虚振動は負の値」にそろえる）
    - 呼出先: なし
    - 呼出元: `run_frequency_analysis`
    - 関連テスト: `tests/test_freq.py`

  - `FrequencyResult(common_backend.vibration.FrequencyResult)`
    - 引数: なし
    - 戻り値: 共通の項目に加えて、`gibbs_hartree`（全自由エネルギー G_tot [Hartree]）と `temperature_K`（熱力学量を求めた温度 [K]）を持つ結果。どちらも、求められなかったときは `None`
    - 目的: PySCF 版の振動数解析の結果。PySCF の `thermo.thermo` が求める熱力学量の項目を、共通の親に足す
    - 呼出先: `common_backend.vibration.FrequencyResult`
    - 呼出元: `run_frequency_analysis`
    - 関連テスト: `tests/test_freq.py`、`tests/test_pipeline.py`

  - `run_frequency_analysis(mf, defaults: dict) -> FrequencyResult`
    - 引数: 収束済み CPU SCF、周波数設定
    - 戻り値: 振動数解析結果
    - 目的: Hessian、調和振動数、ZPE と自由エネルギーを計算する
    - 技術選定: GPU Hessian は十分に検証されていないため CPU PySCF を用いる
    - 呼出先: `FrequencyResult`、`_get`、`_signed_wavenumber`、`common_backend.vibration.FrequencyResult.n_imaginary`
    - 呼出元: `pyscf_backend.pipeline.run_calculation`
    - 関連テスト: `tests/test_freq.py`、`tests/test_pipeline.py`

- `analysis_pyscf.py`

  収束済みの PySCF の SCF オブジェクトから、軌道と電荷の情報を取り出す。描画にもウィジェットにも依存しない（描画は `visualizer_pyscf.py`）。

  - `DEGENERACY_TOLERANCE_HARTREE`
    - 目的: 軌道エネルギーが縮退しているとみなす差（既定 1e-4 Hartree）
    - 呼出先: なし
    - 呼出元: `orbital_choices`（定数）
    - 関連テスト: なし

  - `OrbitalChoices(options, default_index, open_shell)`
    - 目的: 軌道の選択肢の戻り値（表示名と軌道番号の組のリスト、最初に選ぶ軌道番号、開殻かどうか）の `namedtuple`
    - 呼出先: なし
    - 呼出元: `orbital_choices`
    - 関連テスト: なし

  - `_core_and_valence_orbital_counts(symbol: str) -> tuple[int, int]`
    - 引数: 元素記号
    - 戻り値: 1 原子あたりの（内殻軌道の数, 価電子殻の軌道の数）。表にない記号は、内殻なし・価電子殻 4 軌道とする
    - 目的: 軌道の数え上げの内部補助関数。原子番号は `common_backend.elements.ATOMIC_NUMBERS` から求める
    - 呼出先: `common_backend.elements.ATOMIC_NUMBERS`（定数）
    - 呼出元: `valence_space_size`
    - 関連テスト: `tests/test_elements.py`

  - `_atom_symbols(mol) -> list[str]`
    - 引数: PySCF の Mole
    - 戻り値: 原子ごとの元素記号のリスト
    - 目的: 軌道の数え上げのために、Mole から元素記号を取り出す内部補助関数
    - 呼出先: なし
    - 呼出元: `valence_space_size`
    - 関連テスト: なし

  - `valence_space_size(mol) -> tuple[int, int]`
    - 引数: Mole
    - 戻り値: 分子全体の（内殻軌道の数, 価電子殻の軌道の数）
    - 目的: 「各原子の最外殻だけからできる軌道」の数を、原子ごとの値の合計で数える（H・He は 1s の 1 軌道、そのほかは最外殻の s と p の 4 軌道。Ga〜Kr・In〜Xe の (n-1)d 軌道は内殻とみなす）
    - 呼出先: `_atom_symbols`、`_core_and_valence_orbital_counts`
    - 呼出元: `orbital_choices`
    - 関連テスト: `tests/test_analysis_pyscf.py`

  - `_occupations(mf) -> tuple[numpy.ndarray, numpy.ndarray, numpy.ndarray]`
    - 引数: SCF オブジェクト
    - 戻り値: 軌道ごとの総電子数、α スピンの電子数、α スピンの軌道エネルギー
    - 目的: 閉殻・開殻（ROHF を含む）の配列の形の違いを吸収する内部補助関数
    - 呼出先: なし
    - 呼出元: `orbital_choices`
    - 関連テスト: なし

  - `orbital_choices(mol, mf, degeneracy_tolerance: float = DEGENERACY_TOLERANCE_HARTREE) -> OrbitalChoices`
    - 引数: Mole、収束済み SCF オブジェクト、縮退とみなすエネルギー差
    - 戻り値: ドロップダウン用の選択肢、既定の軌道番号、開殻かどうか
    - 目的: 軌道 0 番から「内殻軌道数＋価電子殻の軌道数」番目まで（電子が入っているすべての軌道を含む）を一覧にし、表示名を「軌道n番」とする。閉殻は HOMO・LUMO に「(HOMO)」「(LUMO)」を付け（縮退する軌道すべてに付ける）、開殻は電子が 1 個だけ入っている軌道に「(SOMO)」を付ける。表示名の末尾に軌道エネルギーを eV で併記し（例: 「軌道4番(HOMO)  -13.61 eV」。開殻は α 軌道のエネルギー）、選択肢はエネルギーの低い軌道ほど下に並べる（軌道番号の大きい順）。既定は、電子が入っている（α スピンの）軌道のうち最も高いもの
    - 技術選定: 開殻（UHF/UKS）の `mo_occ`・`mo_energy` は 2 行の配列で保持されるため、α スピンの軌道を基準にする。最外殻の空軌道は軌道の数で近似する
    - 呼出先: `DEGENERACY_TOLERANCE_HARTREE`（定数）、`_occupations`、`valence_space_size`、`common_backend.energy.HARTREE_TO_EV`（定数）、`OrbitalChoices`
    - 呼出元: `gui.pyscf_screen.build_app`
    - 関連テスト: `tests/test_analysis_pyscf.py`

  - `compute_mulliken_charges(mol, mf) -> list[tuple[str, float]]`
    - 引数: Mole、SCF
    - 戻り値: 元素記号と Mulliken 電荷
    - 目的: 原子電荷表と色分け表示の基礎データを得る
    - 呼出先: なし
    - 呼出元: `gui.pyscf_screen.build_app`
    - 関連テスト: `tests/test_analysis_pyscf.py`

- `pipeline.py`

  PySCF 版の計算の流れ。検証済みの構造 → 遷移金属の確認 → 構造最適化（GPU4PySCF・CPU を自動で切替）→ 最終構造での CPU 上の SCF 再計算 → 任意の振動数解析 → 出力ファイル（xyz・molden）の書出し。画面（ipywidgets）にも、アップロードされたファイルの扱いにも依存せず、進捗は `log` 関数（既定は `print`）で受け渡す。例外は捕まえずに送出し、利用者向けの文面への変換は GUI が行う。

  - `CalculationSettings(charge: int, multiplicity: int, functional_key: str, basis_key: str, do_frequency: bool = True, try_gpu: bool | None = None)`
    - 目的: 利用者が指定する計算条件を保持する。`try_gpu` が `None` のときは、GPU ランタイムかどうかを自動で判定する
    - 呼出先: なし
    - 呼出元: `gui.pyscf_screen.build_app`
    - 関連テスト: `tests/test_pipeline.py`

  - `CalculationResult(structure, opt_result, final_mol, mf_final, freq_result, final_symbols, final_coords, out_dir, final_xyz_path, traj_xyz_path, molden_path, total_seconds)`
    - 目的: 計算結果（最適化結果、最終構造の Mole、CPU で収束させた SCF、振動数結果）と、書き出したファイルの場所を保持する。画面表示・ダウンロードにそのまま使う
    - 呼出先: なし
    - 呼出元: `run_calculation`
    - 関連テスト: なし

  - `run_calculation(structure, settings: CalculationSettings, defaults: dict, log = print) -> CalculationResult`
    - 引数: 読込みと入力検証が済んだ構造、計算条件、`config/defaults.yaml` の辞書、ログ出力関数
    - 戻り値: 計算結果
    - 目的: 上記の流れを最初から最後まで実行し、進捗・注意・所要時間を `log` へ出す
    - 技術選定: 計算の流れを画面から分け、PySCF や Colab なしで、段階の呼出し順序と受渡しを単体テストできるようにする
    - 例外: 遷移金属を含む構造は `io_reader.StructureError`、SCF 不収束は `engine.SCFConvergenceError`、構造最適化の不収束は `RuntimeError`
    - 呼出先: `common_backend.runtime.nvidia_gpu_detected`、`pyscf_backend.engine.contains_transition_metal`、`common_backend.io_reader.StructureError`、`pyscf_backend.engine.build_mole`、`pyscf_backend.optimize.run_geometry_optimization`、`pyscf_backend.engine.build_scf`、`pyscf_backend.engine.run_scf`、`pyscf_backend.freq.run_frequency_analysis`、`common_backend.version.__version__`（定数）、`common_backend.writer_xyz.write_optimization_outputs`、`pyscf_backend.writer_molden.write_molden`、`CalculationResult`
    - 呼出元: `gui.pyscf_screen.build_app`
    - 関連テスト: `tests/test_pipeline.py`

- `visualizer_pyscf.py`

  PySCF の Mole/SCF に依存する分子軌道の等値面の可視化。軌道番号や電荷の値を求める解析は `analysis_pyscf.py` が担当し、原子電荷の描画は `gui.plot_common`、cube ファイルの値の読取りは `common_backend.cube` にある。

  - `_mo_coeff_for_cube(mf, orbital_index: int) -> numpy.ndarray`
    - 引数: SCF オブジェクト、軌道番号
    - 戻り値: cube 出力用の、1 つの軌道の係数の列
    - 目的: 開殻（UHF/UKS）で 3 次元（または α・β の組）になる軌道係数から、α スピンの軌道を取り出す内部補助関数
    - 呼出先: なし
    - 呼出元: `render_orbital`
    - 関連テスト: `tests/test_visualizer.py`

  - `render_orbital(mol, mf, orbital_index: int, isoval_fraction: float = 0.12, width: int = 500, height: int = 400) -> py3Dmol.view`
    - 引数: Mole、SCF、軌道番号、等値面比率、サイズ
    - 戻り値: 軌道の正負等値面を含む 3D ビュー
    - 目的: MO を可視化する
    - 技術選定: PySCF cube 出力を py3Dmol へ渡す
    - 呼出先: `_mo_coeff_for_cube`、`common_backend.cube.max_abs_value`
    - 呼出元: `gui.pyscf_screen.build_app`
    - 関連テスト: `tests/test_visualizer.py`

- `writer_molden.py`

  - `write_molden(mf, filepath: str) -> None`
    - 引数: 収束済み CPU SCF、出力先
    - 戻り値: なし
    - 目的: 構造と分子軌道を Molden ファイルへ保存する
    - 技術選定: PySCF の版差を吸収するため高水準 API を順に試し、最後に低水準 API へフォールバックする
    - 呼出先: なし
    - 呼出元: `pyscf_backend.pipeline.run_calculation`
    - 関連テスト: `tests/test_pipeline.py`

### uma_backend

FAIR-Chem/UMA を計算エンジンとする機械学習ポテンシャル用パッケージ。PySCF の電子状態機能には依存せず、ASE の Atoms・最適化器を利用する。

- `__init__.py`

  パッケージの説明だけを書き、何も import しない（`pyscf_backend` にも依存しない）。他のモジュールの名前を別名として公開しない（設定の読み込みは `common_backend.config_loader`、バージョンは `common_backend.version` を、使う側が直接 import する）。

- `uma_engine.py`

  UMA（fairchem-core）で計算するための土台。計算デバイスの判定、学習済みモデルの読込み、ASE の Atoms・Calculator の構築を行う。Hugging Face の認証は `uma_hf.py` が担当する。

  - `describe_device(device: str) -> str`
    - 引数: デバイス名（`"cuda"` または `"cpu"`）
    - 戻り値: ログ表示用の説明文（GPU の名前、または CPU で時間がかかる旨の注意）
    - 目的: 利用者へ、計算デバイスと性能上の注意を示す
    - 呼出先: なし
    - 呼出元: `uma_backend.uma_pipeline.run_calculation`
    - 関連テスト: `tests/test_uma_engine.py`、`tests/test_uma_pipeline.py`

  - `load_predictor(model_name: str, device: str) -> object`
    - 引数: FAIR-Chem モデル名、デバイス
    - 戻り値: 読込み済み予測器
    - 目的: UMA 学習済みモデルを取得・初期化する
    - 技術選定: `fairchem.core.pretrained_mlip` の公開 API を使う。ゲート付きモデルの拒否は `uma_hf.explain_hf_error` で利用者向けの文面にし、`uma_hf.UmaSetupError` として送出する（再エクスポートはしない）
    - 呼出先: `uma_backend.uma_hf.UmaSetupError`、`uma_backend.uma_hf.explain_hf_error`
    - 呼出元: `uma_backend.uma_pipeline.run_calculation`
    - 関連テスト: `tests/test_uma_engine.py`、`tests/test_uma_pipeline.py`

  - `clear_predictor_cache() -> None`
    - 引数: なし
    - 戻り値: なし
    - 目的: 読み込み済みのモデルを解放する（GPU メモリを空けたいとき用）
    - 呼出先: なし
    - 呼出元: なし
    - 関連テスト: `tests/test_uma_engine.py`

  - `make_calculator(predictor, task_name: str = "omol") -> object`
    - 引数: 学習済みモデル（predict unit）、タスク名
    - 戻り値: ASE の Calculator として使える `FAIRChemCalculator`
    - 目的: UMA の予測を、ASE の最適化器から使える計算器にする
    - 呼出先: なし
    - 呼出元: `uma_backend.uma_pipeline.run_calculation`
    - 関連テスト: `tests/test_uma_engine.py`、`tests/test_uma_pipeline.py`

  - `build_atoms(structure, charge: int, multiplicity: int) -> ase.Atoms`
    - 引数: 共通の構造（`Structure`）、電荷、スピン多重度
    - 戻り値: 電荷とスピン多重度つきの ASE `Atoms`
    - 目的: UMA（omol タスク）へ渡す入力を作る。Atoms 本体は `common_backend.ase_bridge.structure_to_atoms` で作り、ここでは、電荷を `atoms.info["charge"]`、スピン多重度を `atoms.info["spin"]` に設定する（fairchem の README・ColabReaction と同じ方式。このキー名は UMA 固有の約束）
    - 呼出先: `common_backend.ase_bridge.structure_to_atoms`
    - 呼出元: `uma_backend.uma_pipeline.run_calculation`
    - 関連テスト: `tests/test_uma_engine.py`、`tests/test_uma_pipeline.py`

- `uma_optimize.py`

  - `ALLOWED_OPTIMIZERS`
    - 目的: 設定ファイルで指定できる ASE の最適化アルゴリズム（`LBFGS`・`BFGS`・`FIRE`）
    - 呼出先: なし
    - 呼出元: `run_geometry_optimization`（定数）
    - 関連テスト: `tests/test_uma_config.py`

  - `OptimizationResult(common_backend.optimization.OptimizationResult)`
    - 引数: なし
    - 戻り値: 共通の項目に加えて、`energies_ev`（各ステップのエネルギー [eV]）、`fmax_history`（各ステップの力の最大値 [eV/Å]）、`fmax_target`（収束条件 [eV/Å]）、`optimizer_name`（最適化アルゴリズム名）、`max_steps`（最大ステップ数）を持つ結果
    - 目的: UMA 版の構造最適化の結果。共通の親クラスに、eV のエネルギー・最大力の履歴・最適化の条件を足す。`final_fmax` プロパティは最終最大力 [eV/Å] を返す
    - 呼出先: なし
    - 呼出元: `run_geometry_optimization`
    - 関連テスト: `tests/test_optimization.py`、`tests/test_uma_notice_report.py`、`tests/test_uma_pipeline.py`
    - `final_fmax`（プロパティ）
      - 戻り値: 最後のステップの力の最大値 [eV/Å]（履歴がなければ `None`）
      - 目的: 収束の判定と、ログ・画面の表示に使う
      - 呼出先: なし
      - 呼出元: `run_geometry_optimization`（属性として参照）、`uma_backend.uma_pipeline.run_calculation`、`uma_backend.uma_report.build_log_text`
      - 関連テスト: `tests/test_optimization.py`

  - `run_geometry_optimization(atoms: ase.Atoms, calculator, opt_cfg: dict, progress = None) -> OptimizationResult`
    - 引数: 初期 Atoms、計算器、最適化設定、任意の進捗コールバック
    - 戻り値: 最適化結果
    - 目的: LBFGS/BFGS/FIRE の設定された ASE 最適化を実行し、GUI 用の履歴を記録する
    - 技術選定: ASE 最適化器を用いて UMA Calculator と直結する
    - 呼出先: `ALLOWED_OPTIMIZERS`（定数）、`OptimizationResult`、`common_backend.energy.HARTREE_TO_EV`（定数）、`OptimizationResult.final_fmax`（属性として参照）
    - 呼出元: `uma_backend.uma_pipeline.run_calculation`
    - 関連テスト: `tests/test_uma_optimize.py`、`tests/test_uma_pipeline.py`

- `uma_freq.py`

  UMA を使った振動数解析（調和近似）。数値計算の本体は `common_backend.vibration` にあり、このモジュールは、UMA の計算器から力の関数を作り、結果を共通の `common_backend.vibration.FrequencyResult` にまとめる。

  - `run_frequency_analysis(atoms, calculator, freq_cfg: dict, progress = None) -> FrequencyResult`
    - 引数: 電荷・スピンつきの最適化後の ASE `Atoms`、UMA の計算器、`uma_defaults.yaml` の `frequency` 節、任意の進捗コールバック
    - 戻り値: 振動数・基準振動モード・ZPE・注意文を持つ共通の `FrequencyResult`（`common_backend.vibration`）
    - 目的: UMA の力から数値 Hessian を作り、調和解析して結果をまとめる。虚振動が出たときは、小さい場合（収束不足・数値誤差の可能性）と大きい場合（極小構造でない可能性）で、注意文を変える。原子が 1 個だけのときは、振動モードがない旨の注意文を返す
    - 技術選定: ASE の `Vibrations` を使わず、並進・回転を除いた振動モードだけを、PySCF 版と同じ個数・同じ形式で返す
    - 呼出先: `common_backend.vibration.FrequencyResult`、`common_backend.vibration.compute_hessian_fd`、`common_backend.vibration.harmonic_analysis`、`common_backend.vibration.zero_point_energy_ev`、`common_backend.energy.HARTREE_TO_EV`（定数）、`common_backend.vibration.FrequencyResult.n_imaginary`（属性として参照）
    - 呼出元: `uma_backend.uma_pipeline.run_calculation`
    - 関連テスト: `tests/test_uma_freq.py`

- `uma_hf.py`

  UMA の学習済みモデルを取得するための Hugging Face のトークン管理とアクセス権の確認。トークンは環境変数 `HF_TOKEN` だけを見る。

  - `MODEL_REPO_ID`
    - 目的: UMA の Hugging Face のリポジトリ名（`facebook/UMA`）
    - 呼出先: なし
    - 呼出元: `check_model_access`（定数）、`explain_hf_error`（定数）
    - 関連テスト: `tests/test_uma_engine.py`

  - `HF_TOKEN_ENV`
    - 目的: トークンの受け渡しに使う環境変数名（`HF_TOKEN`。Hugging Face 公式の標準）
    - 呼出先: なし
    - 呼出元: `login_from_environment`（定数）
    - 関連テスト: `tests/test_uma_engine.py`

  - `LICENSE_FILENAME`
    - 目的: アクセス確認のために取得する、小さなファイルの名前（`LICENSE`。約 6.5 kB）
    - 呼出先: なし
    - 呼出元: `check_model_access`（定数）
    - 関連テスト: `tests/test_uma_engine.py`

  - `UmaSetupError(RuntimeError)`
    - 目的: Hugging Face 認証、アクセス権、ライブラリ未導入など、UMA を使うための準備の問題に関する利用者向け例外。`uma_engine.py` からは再エクスポートせず、利用側は `uma_hf.UmaSetupError` と書く
    - 呼出先: なし
    - 呼出元: `ColabApp_UMA.ipynb`（例外の捕捉）、`gui.uma_screen.build_app`（例外の捕捉）、`uma_backend.uma_engine.load_predictor`、`check_model_access`、`login_from_environment`、`login_with_token`
    - 関連テスト: `tests/test_uma_engine.py`、`tests/test_uma_hf.py`、`tests/test_uma_pipeline.py`

  - `login_with_token(token: str) -> None`
    - 引数: Hugging Face のトークン
    - 戻り値: なし。トークンが空のときは `UmaSetupError`
    - 目的: トークンで Hugging Face にログインし、環境変数 `HF_TOKEN` にも設定する（fairchem がモデルを取得するときに参照するため）。トークンは、画面やログに出さない
    - 呼出先: `UmaSetupError`
    - 呼出元: `login_from_environment`
    - 関連テスト: `tests/test_uma_engine.py`、`tests/test_uma_hf.py`

  - `login_from_environment() -> None`
    - 引数: なし
    - 戻り値: なし。トークンが設定されていないときは `UmaSetupError`
    - 目的: 環境変数 `HF_TOKEN` のトークンでログインする。トークンは、関数内の一時的な変数としてだけ扱い、モジュールの変数にもファイルにも残さない
    - 技術選定: 環境変数 `HF_TOKEN` を使い、ノートブックの入力方法（`getpass`・シークレット）を、このモジュールから見えなくする。入力欄を GUI（ipywidgets）に置くと、入力値が保存されるノートブックに残りうるため、採用しない
    - 呼出先: `HF_TOKEN_ENV`（定数）、`UmaSetupError`、`login_with_token`
    - 呼出元: `ColabApp_UMA.ipynb`
    - 関連テスト: `tests/test_uma_engine.py`、`tests/test_uma_hf.py`、`tests/test_uma_notebook.py`

  - `has_hf_token() -> bool`
    - 引数: なし
    - 戻り値: トークンが設定済みか（環境変数、または保存済みのログイン）
    - 目的: アクセスの確認の前に、トークンの有無を調べる
    - 呼出先: なし
    - 呼出元: `check_model_access`
    - 関連テスト: `tests/test_uma_engine.py`、`tests/test_uma_hf.py`

  - `explain_hf_error(error: Exception) -> str`
    - 引数: Hugging Face 関連の例外
    - 戻り値: 利用者向けの日本語メッセージ
    - 目的: ゲート付きモデルへの未同意・認証エラー、接続エラー、その他を区別して案内する
    - 呼出先: `MODEL_REPO_ID`（定数）
    - 呼出元: `uma_backend.uma_engine.load_predictor`、`check_model_access`
    - 関連テスト: `tests/test_uma_engine.py`、`tests/test_uma_hf.py`

  - `check_model_access() -> str`
    - 引数: なし
    - 戻り値: 取得した LICENSE ファイルのパス
    - 目的: UMA のゲート付きモデルへのアクセス権を、モデル本体を取得する前に確認する
    - 呼出先: `has_hf_token`、`UmaSetupError`、`MODEL_REPO_ID`（定数）、`LICENSE_FILENAME`（定数）、`explain_hf_error`
    - 呼出元: `ColabApp_UMA.ipynb`、`uma_backend.uma_pipeline.run_calculation`
    - 関連テスト: `tests/test_uma_engine.py`、`tests/test_uma_hf.py`、`tests/test_uma_notebook.py`、`tests/test_uma_pipeline.py`

- `uma_notice.py`

  - `UMA_LICENSE_NAME`
    - 目的: UMA のライセンス名（FAIR Chemistry License v1）
    - 呼出先: なし
    - 呼出元: `notice_text`（定数）
    - 関連テスト: `tests/test_uma_notice_report.py`

  - `LICENSE_URL`
    - 目的: ライセンス全文（一次情報）の URL
    - 呼出先: なし
    - 呼出元: `notice_text`（定数）
    - 関連テスト: `tests/test_uma_notebook.py`、`tests/test_uma_notice_report.py`

  - `MODEL_CARD_URL`
    - 目的: モデルカード（Acceptable Use Policy・引用の依頼を含む。一次情報）の URL
    - 呼出先: なし
    - 呼出元: `notice_text`（定数）
    - 関連テスト: `tests/test_uma_notebook.py`、`tests/test_uma_notice_report.py`

  - `PAPER_URL`
    - 目的: UMA の論文（arXiv）の URL
    - 呼出先: なし
    - 呼出元: `notice_text`（定数）
    - 関連テスト: `tests/test_uma_notebook.py`、`tests/test_uma_notice_report.py`

  - `FAIRCHEM_URL`
    - 目的: fairchem のリポジトリの URL
    - 呼出先: なし
    - 呼出元: なし
    - 関連テスト: `tests/test_uma_notebook.py`

  - `CITATION`
    - 目的: モデルカードが引用を求めている論文の書誌。ノートブック冒頭の文面と同じ内容に保つ（`tests/test_uma_notebook.py` が検査する）
    - 呼出先: なし
    - 呼出元: `notice_text`（定数）
    - 関連テスト: `tests/test_uma_notice_report.py`

  - `notice_text() -> str`
    - 引数: なし
    - 戻り値: UMA のライセンス・利用規定・引用についての一次情報へのリンクを並べた、プレーンテキスト
    - 目的: 計算ログの末尾に入れる。我々の解釈や要約を加えず、一次情報の所在と、求められている引用の形だけを伝える
    - 呼出先: `UMA_LICENSE_NAME`（定数）、`LICENSE_URL`（定数）、`MODEL_CARD_URL`（定数）、`CITATION`（定数）、`PAPER_URL`（定数）
    - 呼出元: `uma_backend.uma_report.build_log_text`
    - 関連テスト: `tests/test_uma_notice_report.py`

- `uma_pipeline.py`

  UMA 版の計算の流れ。検証済みの構造 → Hugging Face のアクセス権の確認 → モデルの読込み（デバイスの判定）→ 構造最適化 → 任意の振動数解析 → 出力ファイル（xyz・計算ログ）の書出し。画面（ipywidgets）にも、アップロードされたファイルの扱いにも依存せず、進捗は `log` 関数（既定は `print`）で受け渡す。例外は捕まえずに送出し、利用者向けの文面への変換は GUI が行う。PySCF 版の `pyscf_backend/pipeline.py` とは独立しており（`uma_backend` は `pyscf_backend` に依存しない）、エンジンごとに別々に変えていける。

  - `CalculationSettings(charge: int, multiplicity: int, model_key: str, do_frequency: bool = True, input_filename: str = "")`
    - 目的: 利用者が指定する計算条件を保持する。`input_filename` は計算ログに記載する
    - 呼出先: なし
    - 呼出元: `gui.uma_screen.build_app`
    - 関連テスト: `tests/test_uma_pipeline.py`

  - `CalculationResult(structure, opt_result, freq_result, final_symbols, final_coords, device_label, out_dir, final_xyz_path, traj_xyz_path, log_path, total_seconds)`
    - 目的: 計算結果（最適化結果、振動数結果、最終構造、デバイスの説明）と、書き出したファイルの場所を保持する。画面表示・ダウンロードにそのまま使う
    - 呼出先: なし
    - 呼出元: `run_calculation`
    - 関連テスト: なし

  - `run_calculation(structure, settings: CalculationSettings, defaults: dict, log = print) -> CalculationResult`
    - 引数: 読込みと入力検証が済んだ構造、計算条件、`config/uma_defaults.yaml` の辞書、ログ出力関数
    - 戻り値: 計算結果
    - 目的: 上記の流れを最初から最後まで実行し、進捗（最適化の各ステップ、Hessian 計算の進み具合）・注意（CPU での低速、収束しなかった場合、原子数が多い場合）・所要時間を `log` へ出す
    - 技術選定: 計算の流れを画面から分け、UMA・fairchem・Colab なしで、段階の呼出し順序と受渡しを単体テストできるようにする
    - 例外: トークン・アクセス権・ライブラリ未導入は `uma_hf.UmaSetupError`、ライブラリを読み込めない場合は `ImportError`、設定の誤りは `ValueError`
    - 呼出先: `uma_backend.uma_hf.check_model_access`、`common_backend.runtime.torch_cuda_available`、`uma_backend.uma_engine.describe_device`、`uma_backend.uma_engine.load_predictor`、`uma_backend.uma_engine.make_calculator`、`uma_backend.uma_engine.build_atoms`、`uma_backend.uma_optimize.run_geometry_optimization`、`uma_backend.uma_freq.run_frequency_analysis`、`common_backend.version.__version__`（定数）、`common_backend.writer_xyz.write_optimization_outputs`、`uma_backend.uma_report.build_log_text`、`CalculationResult`、`common_backend.vibration.FrequencyResult.n_imaginary`、`uma_backend.uma_optimize.OptimizationResult.final_fmax`
    - 呼出元: `gui.uma_screen.build_app`
    - 関連テスト: `tests/test_uma_pipeline.py`

- `uma_report.py`

  - `build_log_text(*, version: str, model_key: str, task_name: str, device_label: str, input_filename: str, charge: int, multiplicity: int, opt_result, freq_result = None, total_seconds: float | None = None) -> str`
    - 引数: バージョン、計算条件、入力名、電荷・多重度、最適化結果、任意の振動数結果・合計時間
    - 戻り値: UTF-8 テキストログ
    - 目的: 再現に必要な条件、履歴、振動数、UMA 通知をひとつの出力にまとめる
    - 呼出先: `common_backend.energy.HARTREE_TO_KCAL_MOL`（定数）、`uma_backend.uma_notice.notice_text`、`common_backend.vibration.FrequencyResult.zpe_kcal_per_mol`、`uma_backend.uma_optimize.OptimizationResult.final_fmax`
    - 呼出元: `uma_backend.uma_pipeline.run_calculation`
    - 関連テスト: `tests/test_uma_notice_report.py`、`tests/test_uma_pipeline.py`

### config

YAML に選択肢と既定値を置き、既存パイプライン内の手法・基底関数・UMA モデルの追加をコード変更から分離する。

- `basis_sets.yaml`

  PySCF 用基底関数の表示名、キー、PySCF 名、ECP を定義する。`pyscf_backend.engine.build_mole` が参照する。

- `functionals.yaml`

  HF/DFT の計算エンジン種別と交換相関汎関数を定義する。`pyscf_backend.engine.build_scf` が参照する。

- `purposes.yaml`

  PySCF GUI の計算目的と、最適化・振動数解析の可否を定義する。

- `defaults.yaml`

  PySCF GUI、SCF、最適化、振動数（温度・圧力、振動数計算に時間がかかる旨を表示する原子数 `warn_natoms`）、入力検証、GPU の既定値を定義する。

- `uma_models.yaml`

  UMA GUI に提示する FAIR-Chem のモデルキーと表示名を定義する。

- `uma_defaults.yaml`

  UMA GUI、タスク名、ASE 最適化、数値振動数解析、入力検証の既定値を定義する。

### .githooks

`main`ブランチに`AGENTS.md`を入れないための、gitフック(シェルスクリプト)。全ブランチで追跡する。使うには、クローンごとに `git config core.hooksPath .githooks`と`chmod +x .githooks/*`が必要(「`AGENTS.md`のGit管理」を参照)。

- `check-agents.sh`
  - 目的: 現在のブランチが`main`で、`AGENTS.md`が追跡されている(git のインデックスに入っている)ときは、メッセージを出して終了コード1で終わる。それ以外は0。`pre-commit`・`pre-merge-commit`が呼び出す
  - 呼出先: なし
  - 呼出元: `pre-commit`, `pre-merge-commit`

- `pre-commit`
  - 目的: `check-agents.sh` を呼び出すだけのスクリプト。通常のコミットの前に、git が自動で実行する
  - 呼出先: `check-agents.sh`
  - 呼出元: git（コミットの前に自動で実行される）

- `pre-merge-commit`
  - 目的: `check-agents.sh` を呼び出すだけのスクリプト。マージのコミットの前に、git が自動で実行する
  - 呼出先: `check-agents.sh`
  - 呼出元: git（マージのコミットの前に自動で実行される）

- `pre-push`
  - 目的: pushされる参照のうち、`refs/heads/main`・`refs/tags/*`の指すコミットに`AGENTS.md`が含まれていれば、終了コード1でpushを中止する。削除のpushは対象外
  - 呼出先: なし
  - 呼出元: git（push の前に自動で実行される）


### tests

テストは `python3.12 -m unittest discover -s tests -p "test_*.py"` で実行する(「ローカルの開発環境」を参照)。PySCF・ASE・py3Dmol・geomeTRIC・ipywidgets・torch・fairchem は、入っていれば実物を使い(`real_molecules.py`)、入っていなければ、そのテストだけをスキップする。実際のモデルの読み込み・推論(Hugging Face のトークンが必要)・GPU は、フェイクの環境・差し替えで境界だけを検証する。以下は各テストモジュールが検証するプロジェクト内の関数・クラス・ファイルの完全一覧である。

- `fake_gui_env.py`

	`fake_gui_env(colab: bool = True)`、`_build_ipywidgets`、`_build_ipython_display`、`_Env` は、`test_gui_parts.py` で `gui.parts` をブラウザや Colab 接続なしで検証するための代用品（`qchem_colab_app.gui.parts` などを読み込み直す際、`sys.modules` だけでなく、親パッケージの属性も消す）（Text・IntText・Button・Dropdown などの代用ウィジェットを含む）を提供する。

- `real_molecules.py`

	`HAS_PYSCF`・`HAS_GEOMETRIC`・`HAS_ASE`・`HAS_PY3DMOL`・`HAS_IPYWIDGETS`・`HAS_TORCH`・`HAS_FAIRCHEM`（ライブラリが入っているか。入っていない環境では、`unittest.skipUnless` で、そのテストだけをスキップする）、`build_mole`・`atom_mole`・`run_scf`、実物の小さな計算結果（`water_rhf`・`methyl_uhf`・`methyl_rohf`・`oxygen_triplet_uhf`・`ethanol_cation_uhf`・`benzene_rhf`・`water_equilibrium_rhf`・`linear_water_rhf`。最初に使ったときに 1 回だけ計算して使い回す。どれも 1 秒未満）、`modified_copy`（使い回す結果を、複製してから書き換える）、`hypothetical_rhf`（計算していない RHF に、仮の軌道の占有数・エネルギーを入れる）は、テストで、外部ライブラリの代用品ではなく、実物を使うための補助を提供する。PySCF は関数の中で import するため、入っていない環境でも、このモジュールは読み込める。

- `test_agents_spec.py`

	対象: `AGENTS.md`の仕様書(`tests/spec_analysis.py`の解析と突き合わせる)。ソースの定義すべてに仕様書の項目があること(逆も同じ)、「呼出先」「呼出元」「関連テスト」の行が最新であること(古ければ`python3.12 tests/spec_analysis.py --fix`で更新する)、`tests/`のテストファイルすべてに、この節の項目があること(逆も同じ)を検査する。`AGENTS.md`がない`main`ブランチでは、スキップする。

- `test_analysis_pyscf.py`

	対象: `pyscf_backend.analysis_pyscf.valence_space_size`, `orbital_choices`, `compute_mulliken_charges`。実物の PySCF で、水・メチルラジカル・酸素（三重項）・エタノール陽イオン・ベンゼンの SCF を実際に計算して（`real_molecules.py`、どれも 1 秒未満）、価電子殻・内殻の軌道数の数え上げ、閉殻の HOMO/LUMO 表示名と縮退（ベンゼンの 2 重に縮退した HOMO・LUMO）、開殻（UHF の α・β の 2 行配列、2 つの配列の組、ROHF）の SOMO 表示名と既定の軌道、エネルギー（eV）の併記と換算、リストの並び順（エネルギーの低い軌道が下）、軌道数の上限、元素と電荷の対応（Mulliken 電荷の和が全電荷に一致すること）を検証する。軌道エネルギーの値を指定したいテストは、実物の SCF の結果を複製して、軌道エネルギーだけを書き換える。実際には起こらない軌道の数の確認は、計算していない実物の RHF に、仮の軌道の占有数・エネルギーを入れる。元素記号の表記ゆれは、PySCF が正規化するため実物では現れないので、実物の Mole の `atom_pure_symbol` だけを差し替える。エネルギーの換算は`common_backend.energy.HARTREE_TO_EV`を使い、`analysis_pyscf`が自前の定数を持たないことも検証する。PySCF が入っていない環境では、すべてスキップする。

- `test_colab_widgets.py`

	対象: `gui.colab_widgets.parse_dropped_payload`, `build_drop_zone_html`, `check_safe_id`。許可拡張子、Base64、サイズ制限、ディレクトリ部分の除去、HTML 識別子の安全性を検証する。

- `test_config_loader.py`

	対象: `common_backend.config_loader.load_yaml`, `CONFIG_DIR`, `PROJECT_ROOT`。`config/` の場所、YAML の読込み、存在しないファイルのエラー、`pyscf_backend`・`uma_backend` が `load_yaml`・`CONFIG_DIR`・`PROJECT_ROOT` を再エクスポートしていないことを検証する。

- `test_ase_bridge.py`

	対象: `common_backend.ase_bridge.structure_to_atoms`。ASE を代用のモジュールに差し替えて、元素記号と座標が渡ること、入力の構造と座標を共有しないこと、電荷・スピン多重度を設定しないこと、ASE 未導入時に `ImportError` になることを検証する。ASE が入っている環境では、本物の `Atoms` でも確認する(入っていなければ、この部分だけスキップ)。構造は、実物の `common_backend.io_reader.Structure` で作る。

- `test_cube.py`

	対象: `common_backend.cube.max_abs_value`。PySCF を実行せず、cube ファイルの値の最大絶対値、ヘッダー部分の値を数えないこと、値がないときの 0.0、原子数が負のヘッダーを検証する。

- `test_elements.py`

	対象: `common_backend.elements.ATOMIC_NUMBERS`。H〜Xe の 54 元素、原子番号の連続性、代表的な元素、元素記号の表記、Xe より重い元素を含まないこと、`io_reader`・`analysis_pyscf` が自前の表を持たず、表の全元素で軌道の数え上げができることを検証する。

- `test_energy.py`

	対象: `common_backend.energy.relative_energies_kcal`, `HARTREE_TO_KCAL_MOL`, `HARTREE_TO_EV`。最後の点を基準にした相対エネルギー[kcal/mol]、空のリスト・NaN のエラー、換算係数を検証する。

- `test_energy_plot.py`

	対象: `gui.energy_plot.nice_ticks`, `build_energy_plot_html`。目盛り、SVG の点・選択マーカー・ツールチップ・クリックコールバック、識別子の安全性、`colab_widgets` との分離、換算・相対エネルギーが `common_backend.energy` にだけ定義されていること（`gui.energy_plot` は同じ関数を使うだけ）を検証する。

- `test_engine.py`

	対象: `pyscf_backend.engine.contains_transition_metal`。遷移金属の判定（各周期の d ブロック元素と、隣接する主族元素の区別）と、GPU ランタイムの判定が `engine` に残っていない（`common_backend.runtime` にある）ことを検証する（Mole・SCF の構築と実行は PySCF が必要なため、Colab 実機で確認する）。構造は、実物の `common_backend.io_reader.Structure` で作る。

- `test_freq.py`

	対象: `pyscf_backend.freq.FrequencyResult`, `run_frequency_analysis`, `_signed_wavenumber`。実物の PySCF で、水（HF/STO-3G）の Hessian・調和振動数・熱力学量を実際に計算して、振動数と基準振動モードの取り出し（PySCF を直接呼んだ結果との一致）、熱力学量（ZPE・自由エネルギー・温度）の格納、結果が共通の親クラスの子であることを検証する。虚振動は、鞍点である直線の水で実際に出し、2 個の虚振動が負の値で数えられ、注意文が出ることを検証する（PySCF は虚振動を複素数で返す）。熱力学量の計算に失敗したときも振動数が残ること（部分的な値を残さない）と、PySCF の版によるキー名の違いは、実物の `pyscf.hessian.thermo` の関数だけを差し替えて検証する。PySCF が入っていない環境では、PySCF を使うテストだけをスキップする。

- `test_githooks.py`

	対象: `.githooks/`の4つのファイル。実行権限とシバン行の確認に加え、一時的なgitリポジトリ(利用者のgit設定の影響を受けないよう、`HOME`を差し替える)で、`main`上で`AGENTS.md`を追跡したコミットの拒否、`develop`上のコミットの許可、`develop`→`main`のマージ(`--no-ff --no-commit`)が`git rm --cached`の後にだけ成功すること、自動コミットされるマージの拒否、`main`・注釈付きタグのpushの中止、`develop`のpushの許可、削除のpushが妨げられないことを検証する。gitが使えない環境では、動作の検証だけスキップする。

- `test_gui_input.py`

	対象: `gui.inputs.extract_uploaded_file`, `load_uploaded_structure`, `format_charge`, `parse_charge`, `ChargeInputError`。実物の ipywidgets 8.x の `FileUpload` で、アップロードされたファイルの取り出し（辞書のタプル・bytes への変換・先頭のファイル・何も選んでいない状態）とドロップ入力の優先順位を検証する。今の ipywidgets が作らない形の value（7.x の辞書形式・属性を持つオブジェクト・想定外の型・空の値のうちタプル以外）だけは、`SimpleNamespace` で代用する。構造の読込みと検証の順序・一時ファイルの拡張子と後始末、電荷の正負の表示・全角数字・Unicode のマイナス・空白・無効値を検証する。`load_uploaded_structure` は `io_reader` の関数を差し替え、受け渡しだけを確認する。 `read_uploaded_structure`（一時ファイルの拡張子・後始末・検証をしないこと）と `describe_structure` も検証する。構造は、実物の `common_backend.io_reader.Structure` で作る。ipywidgets が入っていない環境では、`FileUpload` を使うテストだけをスキップする。

- `test_gui_output.py`

	対象: `gui.outputs.sanitize_filename_stem`, `default_download_stem`, `xyz_download_items`。ファイル名の禁止文字除去、日本語名、既定の結果名、ダウンロード項目の形を検証する。

- `test_gui_parts.py`

	対象: `gui.parts.dropdown_from_list`; `StructureFileInput.__init__`, `_on_file_dropped`, `_on_upload_changed`, `read`; `EnergyStructureViewer.__init__`, `show`, `_show_structure_at_step`, `_draw_energy_plot`, `_on_slider_changed`, `_on_plot_clicked`; `VibrationViewer.__init__`, `setup`, `_on_button_clicked`; `DownloadPanel.__init__`, `show`; `ChargeInput.__init__`, `_on_text_changed`, `_step`; `MultiplicityInput.__init__`, `value`。Colab／非 Colab 入力、SVG コールバック、エネルギーと座標の対応、スライダー同期、描画失敗表示、振動モード、ダウンロード名と再描画、電荷入力の整形・無効値の巻き戻し・±1 ボタン、多重度入力の値の取得を検証する。 受け取った構造の自動表示（ドロップ・ボタン、概要、読み込めない内容の説明、表示の失敗がファイルの受取りを妨げないこと）、`EnergyStructureViewer`・`VibrationViewer`・`DownloadPanel` の `reset`、`VibrationViewer.setup` による前回のアニメーションの消去も検証する。
Colab では、ファイル選択ボタンが画面に置かれていないこと（ドロップ領域だけ）、説明文が「枠をクリック」を案内すること、最後にドロップしたファイルが使われることを、Colab 以外では、ファイル選択ボタンが最初のウィジェットで、選んだファイルの読込み・構造の表示が動くことを検証する。最適化結果・振動数解析の結果は、実物の共通のクラス（`common_backend.optimization.OptimizationResult`・`common_backend.vibration.FrequencyResult`）で作る（`gui` は計算エンジンのパッケージを使わないため、親クラスを使う）。

- `test_io_reader.py`

	対象: `common_backend.io_reader.read_xyz`, `read_structure`, `validate_structure`, `validate_charge_and_multiplicity`, `Structure`, `StructureError`。XYZ の読込み、元素記号正規化、異常入力、原子重なり、電荷・多重度の整合、拡張子振り分けを検証する。

- `test_config.py`

	対象: `common_backend.config_loader.load_yaml` と `config/purposes.yaml`, `functionals.yaml`, `basis_sets.yaml`, `defaults.yaml`。PySCF 用 YAML の必須キー、HF/B3LYP、基底関数、既定値を検証する。

- `test_notebooks_hidden_code.py`

	対象: `ColabApp.ipynb`, `ColabApp_UMA.ipynb`。すべてのコードセルが `cellView: form` と先頭行の `#@title 題名` を持ち（コード非表示）、題名が重複せず、セル ID が保持されていることを検証する。

- `test_optimization.py`

	対象: `common_backend.optimization.OptimizationResult`、および、その子クラス `pyscf_backend.optimize.OptimizationResult`・`uma_backend.uma_optimize.OptimizationResult`（`final_fmax` を含む）。空の状態、インスタンス間でリストを共有しないこと、子クラスが共通の項目を親から引き継ぎ、エンジン固有の項目だけを足していること（PySCF 版と UMA 版が、お互いの項目を持たないこと）、どちらのエンジンの結果も、共通の出力関数（`common_backend.writer_xyz.write_optimization_outputs`）が同じように受け取れることを検証する。PySCF・ASE・UMA は使わない。

- `test_pipeline.py`

	対象: `pyscf_backend.pipeline.CalculationSettings`, `CalculationResult`, `run_calculation`。2 通りで検証する。(1) `engine`・`optimize`・`freq`・`writer_molden`・`runtime` の関数だけを差し替え、段階の呼出し順序と引数（再計算は常に CPU、最適化時の密度行列を初期値に渡す）、振動数計算の有無、GPU の自動判定と明示指定、原子数の注意の閾値、遷移金属の拒否（計算前）、段階の例外がそのまま送出されること、出力ファイルの名前と中身、ログの内容を検証する。分子は実物の `pyscf.gto.Mole`、SCF オブジェクトは計算していない実物の RHF、構造・最適化結果・振動数結果は、実物のクラス（`common_backend.io_reader.Structure`・`pyscf_backend.optimize.OptimizationResult`・`pyscf_backend.freq.FrequencyResult`）を使う。(2) 実際の計算（`TestRealCalculation`）: 少し歪めた水（HF/3-21G）の構造最適化・CPU での再計算・振動数計算・出力（xyz・トラジェクトリ・molden）を、PySCF と geomeTRIC で、差し替えずに実際に走らせる（約 3 秒）。収束した構造（O-H 約 0.967 Å、H-O-H 約 108°）、虚振動がないこと、ZPE、出力ファイルの中身、ログを検証する。GPU4PySCF を使う計算は、Colab 実機で確認する。PySCF・geomeTRIC が入っていない環境では、このファイルのテストをスキップする（遷移金属の拒否など PySCF を使わない部分を含む。）。

- `test_plot_common.py`

	対象: `gui.plot_common.atomic_charges_table_html`, `_charge_gradient_color`, `add_atom_charge_labels`, `add_atom_charge_spheres`, `render_charges`, `render_single_structure`, `render_vibration`。電荷表の HTML、正・中性・負の色、原子ごとのラベル・球の追加（位置・色・ファンデルワールス半径・電荷による大きさの変化）は、呼び出しを記録するテスト用のクラス（`FakeView`）で検証する。`render_charges`・`render_single_structure`・`render_vibration` は、実物の py3Dmol で `view` を作り、それが組み立てた JavaScript（`startjs`）の呼び出しと引数（球・ラベルの数と色、フレーム数、アニメーションの設定、虚振動のラベル）を検証する。`plot_common` が計算エンジンのパッケージを import していないことも検証する。ブラウザ上での実際の 3D 表示は、Colab 実機で確認する。py3Dmol が入っていない環境では、それを使うテストだけをスキップする。

- `test_package_layering.py`

	対象: リポジトリのパッケージ構成と、import の依存の向き。ルート直下に `.py` が無いこと、`qchem_colab_app` の下が `common_backend`・`gui`・`pyscf_backend`・`uma_backend` だけであること、最上位と各パッケージの `__init__.py` が何も import しない（再エクスポートをしない）こと、各パッケージが許された依存先（`gui` → `pyscf_backend`・`uma_backend` → `common_backend`）だけを import していること（関数の中の import も含む。相対 import は不可）、バックエンドが `ipywidgets`・`IPython` を import しないこと、`gui` の共通部品が計算エンジンのパッケージを import せず、各画面が自分のエンジンだけを呼ぶこと、ノートブックが `gui` の画面と `uma_backend.uma_hf` だけを import し、各ノートブックが自分の画面を1つだけ読み込むことを、ソースの構文解析で検証する（ipywidgets などが無くても動く）。

- `test_readme.py`

	対象: `README.md`, `common_backend.version.__version__`。README 冒頭の版数の表示、一対のコードフェンス、相対リンク、バッククォートで記載されたファイル、両 Colab ノートブックへのリンク、`README.md` に `build_notebook.py` が書かれていないことを検証する。

- `test_requirements.py`

	対象: `requirements.txt`, `requirements-uma.txt`。PySCF 用／UMA 用の必須パッケージ、PySCF 専用パッケージの UMA 側からの除外、`torch` と `ipywidgets` を requirements で固定しない方針を検証する。`plotly` と `kaleido` は、必須パッケージの検証対象に含めない。

- `test_runtime.py`

	対象: `common_backend.runtime.nvidia_gpu_detected`, `torch_cuda_available`。`subprocess.run` を差し替え（戻り値は実物の `subprocess.CompletedProcess`）、`nvidia-smi` の成功・失敗・コマンド不在・タイムアウトで GPU 有無を正しく判定すること、実物の torch の `cuda.is_available` だけを差し替えて、CUDA の可否と、torch 未導入時の `False`、2 つの判定が独立であること(GPU ランタイムでも CPU 版の torch なら、前者だけが `True`)を検証する。torch が入っていない環境では、torch を使うテストだけをスキップする。

- `test_uma_config.py`

	対象: `common_backend.config_loader.load_yaml` と `config/uma_defaults.yaml`, `uma_models.yaml`。UMA の GUI・タスク・最適化・振動数・検証設定、モデルキーの一意性と非推奨モデルの除外、存在しない YAML のエラーを検証する。

- `test_uma_engine.py`

	対象: `uma_backend.uma_engine.describe_device`, `load_predictor`, `clear_predictor_cache`, `build_atoms`。CPU 警告、GPU の名前の表示（実物の torch の `cuda.get_device_name` だけを差し替える）、`fairchem` 未導入時の準備エラー、ゲート付きモデルの拒否が `uma_hf.UmaSetupError` になること、他の例外は包まないこと、モデル名・デバイスが fairchem に渡ること、同じモデル・デバイスは 1 回だけ読み込むことを、実物の fairchem の `pretrained_mlip.get_predict_unit`（モデルを取得する関数）だけを差し替えて検証する（Hugging Face への接続・ダウンロードはしない）。認証関連の名前が `uma_engine` に残っていない（再エクスポートされていない）こと、デバイスを選ぶ関数が `uma_engine` に残っていないことも検証する。`build_atoms` は、実物の ASE の `Atoms` と、`ase_bridge` の本物の変換で、電荷・スピン多重度が `atoms.info` に整数で入ることを検証する。ASE・torch・fairchem が入っていない環境では、それを使うテストだけをスキップする。

- `test_uma_hf.py`

	対象: `uma_backend.uma_hf.login_with_token`, `login_from_environment`, `has_hf_token`, `explain_hf_error`, `check_model_access`, `UmaSetupError`。Hugging Face トークンの空値・環境変数処理・非保持、ゲート付きモデル・HTTP エラーの説明を検証する。

- `test_uma_freq.py`

	対象: `uma_backend.uma_freq.run_frequency_analysis`。ASE も UMA も使わず、バネのモデルの力を返す代用の Atoms・計算器で、二原子分子の振動数の個数、ZPE の Hartree・kcal/mol への換算、入力 Atoms 非変更、進捗通知、大きな虚振動と小さな虚振動での注意文の違い、原子 1 個のときの扱いを検証する。ASE が入っている環境では、さらに、結果を、ASE の`Vibrations`(EMT で緩和した Cu₂・Cu₃・Cu₄。ゼロ付近の並進・回転の値を除き、絶対値の大きい 3N-6 個[直線分子は 3N-5 個]と比較)と照合する(ASE が入っていない環境では、この部分だけスキップ)。

- `test_uma_pipeline.py`

	対象: `uma_backend.uma_pipeline.CalculationSettings`, `CalculationResult`, `run_calculation`。`uma_hf`・`uma_engine`・`uma_optimize`・`uma_freq`・`runtime` を代用の関数に差し替え、段階の呼出し順序と引数（タスク名は設定ファイルから）、振動数計算の有無と、最終構造に置いた複製への実行、デバイスごとの注意（CPU での低速）、収束しなかった場合の注意、原子数の注意の閾値、Hessian 進捗の報告間隔、アクセス権の確認が最初に行われること、段階の例外がそのまま送出されること、出力ファイルの名前と中身、計算ログへ渡す内容を検証する。構造・最適化結果・振動数結果は、実物のクラス（`common_backend.io_reader.Structure`・`uma_backend.uma_optimize.OptimizationResult`・`common_backend.vibration.FrequencyResult`）で作る（虚振動の数は、振動数から求まる）。

- `test_uma_notebook.py`

	対象: `ColabApp_UMA.ipynb` と `uma_backend.uma_notice.notice_text` が示す一次情報。ノートブックのメタデータ、セル ID、保存出力、トークン非保存、トークン入力セルの順序、ライセンス案内と引用の位置・内容を検証する。

- `test_uma_notice_report.py`

	対象: `uma_backend.uma_notice.notice_text`, `uma_backend.uma_report.build_log_text`, `uma_backend.uma_optimize.OptimizationResult`, `common_backend.vibration.FrequencyResult`。UMA の一次情報・引用、計算条件、履歴、未収束表示、振動数、通知、秘匿情報を含まないログを検証する。最適化結果・振動数結果は、実物のクラスで作る（最終の最大力は、`fmax_history` の最後の値から求まる）。

- `test_uma_optimize.py`

	対象: `uma_backend.uma_optimize.run_geometry_optimization`, `OptimizationResult.final_fmax`。ASE EMT を使い、対応する最適化器の選択、収束・未収束、エネルギーの eV→Hartree 変換(換算係数を、このモジュールに持たず、`common_backend.energy.HARTREE_TO_EV`を使うこと)、重複しない履歴、入力 Atoms 非変更、進捗通知を検証する。

- `test_version_sync.py`

	対象: `common_backend.version.__version__`, `pyscf_backend`, `uma_backend`。`major.minor.patch` 形式のリリース番号であること、`pyscf_backend`・`uma_backend` が `__version__` を別に持たないことを検証する。

- `test_vibration.py`

	対象: `common_backend.vibration.compute_hessian_fd`, `harmonic_analysis`, `zero_point_energy_ev`, `FrequencyResult`。二原子・直線／非直線三原子・単原子の有限差分 Hessian、質量依存性、負の曲率、並進・回転除去、回転不変性、進捗通知、ZPE(虚振動を数えないこと)を、バネのモデルの解析解で検証する。結果の入れ物`FrequencyResult`は、空の状態、虚振動の数が振動数から求まること、ZPEの kcal/mol への換算を検証する。ASE が入っている環境では、さらに、`harmonic_analysis`の結果を、ASE の`VibrationsData.from_2d`(バネのモデルの Hessian)と照合する(ASE が入っていない環境では、この部分だけスキップ。ASE の返す値を比較用にそろえる補助関数は、ASE なしでも検証する)。

- `test_visualizer.py`

	対象: `pyscf_backend.visualizer_pyscf._mo_coeff_for_cube`, `render_orbital`。実物の PySCF（水 RHF/6-31G・メチルラジカル UHF/6-31G）で、閉殻の 2 次元の軌道係数、開殻（UHF）の 3 次元の係数、α・β の組から、α スピンの軌道を取り出すことを検証する。`render_orbital` は、実物の PySCF（cubegen）で cube ファイルを実際に作り、実物の py3Dmol が組み立てた JavaScript で、cube データの埋め込み、正・負の等値面（青・赤）、等値面の閾値が軌道の最大絶対値の割合（既定 12%）であること、割合を変えられること、開殻では α の係数を使うことを検証する。あわせて、原子電荷の描画関数や cube の読取りが、このモジュールに存在しないことも確認する。PySCF・py3Dmol が入っていない環境では、それを使うテストだけをスキップする。

- `test_writer_xyz.py`

	対象: `common_backend.writer_xyz.xyz_string`, `multiframe_xyz_string`, `write_final_structure`, `write_trajectory`, `write_optimization_outputs`。XYZ の形式、コメント、フレーム数、標準のファイル名と書出し先、最終構造がトラジェクトリの最終フレームと別でもよいことを検証する。最適化結果は、共通の親クラス `common_backend.optimization.OptimizationResult` の実物で作る。

### references

外部プロジェクト ColabReaction の notebook、利用者マニュアル、ライセンスの参照コピー。アプリケーションの実行時依存ではなく、UI・操作設計の比較資料としてのみ保管する。
