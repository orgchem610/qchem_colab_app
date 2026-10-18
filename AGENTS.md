# AGENTS.md

このリポジトリの開発・保守のための管理文書。コードを読む・書く人(AIエージェントを含む)向けに、
作業のルール、実装・設計のメモ、過去のトラブルシューティングの経緯、そして
ディレクトリ構成と各モジュール・関数の仕様(末尾の「仕様書」)を、このファイル1つにまとめている。

**`main`ブランチではGit管理の対象外、`develop`・`feature/*`ブランチではGit管理の対象**にしている
(v0.2.2から。運用は、「`AGENTS.md`のGit管理」の節を参照)。`main`には存在しないため、`README.md`・`tests/`・
ソースコードからは、このファイルを参照しない(参照すると、`main`でテストが失敗する)。
`develop`・`feature/*`はGitHubにpushされるため、GitHubが公開リポジトリの場合、そのブランチ上のこのファイルは
第三者にも読める。パスワード・トークン・個人情報は、書かない。

このファイルの構成:

- 前半: 作業のルール、設計・実装のメモ、バージョン管理・ブランチ運用、トラブルシューティングの経緯、
  v0.2.1の見直しの経緯
- 末尾の「仕様書」: ファイル一覧、各モジュール・関数の仕様、呼出先の一覧、テストの対象

## 作業のルール

- ソースコードを変更するときは、同時に、このファイル末尾の「仕様書」(ファイル一覧・各モジュールと関数の仕様・
  呼出先の一覧・テストの対象)と`README.md`も更新する(`README.md`は利用者向けの内容だけ。
  実装に関するメモは、このファイルの前半に書く)。
- `common/`は、計算エンジンに依存しない共通部品だけを置く。`uma_backend/`は`pyscf_backend/`をimportしない。
- PySCF版とUMA版で似たコードがあっても、将来それぞれ独立に変えていく可能性があるものは、無理に共通化しない
  (v0.2.1の見直しで、「共通化したもの」と「独立のまま残したもの」を判断した)。
- `AGENTS.md`は、`develop`・`feature/*`では追跡し、`main`では追跡しない。Claudeが`main`へのマージの手順を案内するときは、
  必ず「`AGENTS.md`のGit管理」と「`main`ブランチへのリリース(マージ)の手順」の4(`--no-ff --no-commit`でマージ →
  `git rm --cached --ignore-unmatch AGENTS.md` → 確認 → コミット)を含める。
- 新しいタグを打つ前に、単体テストを通し、Colab実機で動作を確認する(単体テストでは、PySCF・fairchem・
  Colab上のJavaScript連携は確認できない)。
- GitHubのリポジトリは`orgchem610/qchem_colab_app`のみを対象にする。履歴を消す操作(強制プッシュ等)はしない。

## 開発・動作確認の進め方について

コードの作成・単体テストは、ネットワークに接続できないサンドボックスで行っているため、
PySCF・fairchem・Google Colab実機を使った動作は、そこでは確認できません。
Colab上での動作(PySCFの呼び出し、UMAの推論、ドラッグ&ドロップ・グラフのクリックの
JavaScript連携など)は、リリース前にColab実機で確認してから、タグを打つ運用にしています。
単体テストで確認できる範囲は`tests/`にあります(実行方法は下記「ディレクトリ構成」参照)。


## ディレクトリ構成(各ファイルの役割)

```
qchem_colab_app/
├── ColabApp.ipynb              # PySCF版ノートブック(Setup Section / Execution Section)
├── ColabApp_UMA.ipynb           # UMA版ノートブック(ランタイム 2026.07・T4 GPUが記録済み)
├── README.md                     # 利用者向けの説明
├── AGENTS.md                       # 開発・保守の管理文書(作業のルール・設計メモ・経緯・仕様書)。develop・feature/*だけで追跡し、mainでは追跡しない
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
├── common/                    # 計算エンジンに依存しない共通モジュール(PySCF版・UMA版の両方が使う)
│   ├── config.py                 # config/のYAMLの読み込み(pyscf_backend・uma_backendの両方が使う)
│   ├── version.py                 # バージョン番号(__version__。リポジトリ全体で1か所だけ)
│   ├── io_reader.py             # 構造ファイルの読み込み・入力バリデーション
│   ├── writer_xyz.py             # xyz出力(単一構造・多フレーム・最適化の標準出力2ファイル)
│   ├── plot_common.py             # 構造・振動アニメーションの3D表示(py3Dmol)
│   ├── colab_widgets.py            # ブラウザ側JavaScript ↔ Colabのコールバック(ドロップ領域・コールバック登録)
│   ├── energy_plot.py                # クリックできるエネルギー収束グラフ(SVG)と、相対エネルギー・目盛りの計算
│   ├── gui_input.py                  # GUIの入力まわりの関数(アップロードされたファイルの取り出し・読み込みと検証・電荷の表示と読み取り)
│   ├── gui_output.py                 # GUIの出力まわりの関数(ダウンロード名・ダウンロード項目)
│   └── gui_parts.py                  # GUI共通の画面部品(ファイル入力・グラフ+構造表示・振動・ダウンロード・電荷入力・スピン多重度入力)
├── pyscf_backend/                     # PySCFを計算エンジンとするab initio計算専用(uma_backendからは呼ばない)
│   ├── __init__.py               # __version__・load_yaml(common.version・common.configの別名)
│   ├── analysis_pyscf.py          # 分子軌道の選択肢(HOMO/LUMO/SOMO)・Mulliken電荷など、SCF結果からの情報の取り出し
│   ├── engine.py                  # Mole構築・SCF実行(GPU4PySCF自動フォールバック含む)
│   ├── optimize.py                 # geomeTRICによる構造最適化
│   ├── pipeline.py                 # PySCF版の計算の流れ(最適化→CPU再計算→振動数→出力ファイル)。GUI・ファイル入力に依存しない
│   ├── freq.py                      # Hessian・振動数解析
│   ├── writer_molden.py              # moldenファイル出力
│   └── visualizer_pyscf.py            # 分子軌道・原子電荷等、PySCF固有の可視化
├── uma_backend/                   # UMA(機械学習ポテンシャル)専用(pyscf_backendには依存しない)
│   ├── __init__.py               # __version__・load_yaml(common.version・common.configの別名)
│   ├── uma_hf.py                   # Hugging Faceのトークン・アクセス確認、UmaSetupError
│   ├── uma_engine.py              # モデルの読み込み、計算デバイスの判定、ASEのAtoms/Calculator
│   ├── uma_optimize.py             # ASE(LBFGS等)+UMAによる構造最適化
│   ├── uma_pipeline.py             # UMA版の計算の流れ(アクセス確認→モデル→最適化→振動数→出力ファイル)。GUI・ファイル入力に依存しない
│   ├── uma_freq.py                  # 数値Hessianによる振動数解析(並進・回転を除去)
│   ├── uma_notice.py                  # UMAのライセンス・引用の一次情報へのリンク
│   ├── uma_report.py                   # 計算ログの組み立て
│   └── README.md                        # UMA版の詳細・トラブルシューティング
├── gui.py                     # PySCF版のGUI組み立て(ipywidgets)
├── gui_uma.py                  # UMA版のGUI組み立て(ipywidgets)
└── tests/
    ├── test_io_reader.py / test_config.py / test_visualizer.py   # 入力・設定・可視化(PySCF非依存部分)
    ├── test_analysis_pyscf.py       # 分子軌道の選択肢・Mulliken電荷(PySCFなしの代用オブジェクトで確認)
    ├── test_engine.py                # GPUランタイムの判定(PySCFなし)
    ├── test_pipeline.py              # PySCF版の計算の流れ(engine等を代用の関数に差し替えて確認)
    ├── test_writer_xyz.py            # xyz出力・最適化の標準出力2ファイル
    ├── test_colab_widgets.py       # ドロップ領域(JavaScriptを含むHTMLの生成)・識別子の安全確認
    ├── test_energy_plot.py           # クリックできるエネルギー収束グラフ(SVG)・相対エネルギー・目盛り
    ├── test_common_config.py          # config/のYAMLの読み込み(pyscf_backend・uma_backendが同じ関数を使っていること)
    ├── test_gui_input.py             # ファイルの取り出し・構造の読み込みと検証・電荷の表示と読み取り
    ├── test_gui_output.py            # ダウンロード名・ダウンロード項目
    ├── test_gui_parts.py             # 共通の画面部品(電荷・スピン多重度の入力を含む。ipywidgets・Colabの代用品を使用)
    ├── test_notebooks_hidden_code.py  # 両ノートブックのコードセルが、既定でコード非表示になっているか
    ├── fake_gui_env.py                # test_gui_parts.py用の、ipywidgets・Colabの代用品
    ├── test_uma_*.py                   # UMA版(振動数の数値計算・最適化・認証・計算の流れ・ログ・設定・ノートブックの構成など)
    ├── test_requirements.py             # requirements*.txtの方針(ipywidgetsを指定しない、など)
    ├── test_githooks.py                  # .githooksの動作(一時的なgitリポジトリで、mainでのAGENTS.mdの拒否・pushの中止を確認)
    └── test_version_sync.py / test_readme.py   # バージョン番号が1つであること・README.mdとの整合
```

テストは、次のコマンドで実行できます(ASEが入っていない環境では、ASEを使う一部のテストはスキップされます)。

```
python3 -m unittest discover -s tests -p "test_*.py"
```

### `common`/`pyscf_backend`/`uma_backend`という3つのトップレベルパッケージに分けた理由

「PySCF版・UMA版の両方から呼び出せる汎用的なコード」と「各計算エンジンに固有のコード」を
物理的に分離しておくための整理です。`common/`は引数がプレーンな
Pythonの値(元素記号・座標・エネルギーの数列等)で完結しており、PySCF版・UMA版の
どちらからもそのままimportして再利用しています。`pyscf_backend/`(=PySCF専用)は
PySCFのMole/SCFオブジェクトに直接依存しており、UMA版では使えません。`uma_backend/`
(=UMA専用)は`pyscf_backend`を一切importしません(PySCFがインストールされていない環境でも
動くようにするため)。
`common`・`pyscf_backend`・`uma_backend`はいずれもリポジトリ直下の対等な(どれが親でも子でもない)
パッケージとして置いています。

GUIの画面部品も、同じ考え方で整理しています。構造ファイルの入力・エネルギーグラフと構造表示・
振動アニメーション・ダウンロードは、PySCF版とUMA版で同じ動作のため、`common/gui_parts.py`に
共通の部品として切り出しました(v0.2.0)。各部品は、計算エンジンのモジュールをimportせず、
エネルギー・座標・振動数などのプレーンな値だけを受け取ります。エンジンごとに違う部分
(構造表示の見出しに足す情報など)は、部品に関数を渡して差し替えます。

(以前のバージョンでは`common/`を`pyscf_backend/`の中に入れる構成でお渡ししましたが、
「`common`は`pyscf_backend`専用の一部ではなく、`pyscf_backend`と`uma_backend`が対等に依存する
共通基盤である」という位置づけをより素直に表せるよう、上記の構成に修正しました)

### `gui.py`/`gui_uma.py`をルート直下に置いている理由(設計意図)

`gui.py`は「`pyscf_backend`パッケージが提供する部品(入出力・計算・可視化)を
1つのColabアプリの画面として組み立てる」役割に特化した、**アプリの
組み立て役(エントリーポイント)**であり、`pyscf_backend`パッケージ自体が提供する
再利用可能な部品(ライブラリ)とは性質が異なるため、意図的にパッケージの
外に置いています。UMA版の`gui_uma.py`も同じ考え方です。`gui.py`は`pyscf_backend`と
`common`から、`gui_uma.py`は`uma_backend`と`common`から、それぞれ必要な部品を
自由に組み合わせています。仮に`gui.py`を`pyscf_backend`の中に、`gui_uma.py`を
`uma_backend`の中に入れてしまうと、例えば`gui_uma.py`(`uma_backend`側)が
`common`の関数を再利用する際に「`uma_backend`パッケージの中から`common`
パッケージを参照する」という向きの依存が生まれます。これ自体は`common`が
独立したトップレベルパッケージである今の構成なら実は問題にはなりませんが、
「アプリの組み立て役」と「再利用可能な部品」という役割の違いを分かりやすく
保つため、`gui.py`/`gui_uma.py`はルート直下に置くことにしています。


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


## Hugging Faceのトークンの扱い(設計上の理由)

`uma_hf.login_from_environment()`が環境変数を読み取ってログインするため、入力セルの作りを変えても、
`uma_backend`や`gui_uma.py`を変更する必要はありません(疎結合)。トークンの入力欄をGUI(ipywidgets)に置く方式は、
入力値がウィジェットの状態として保持され、保存されるノートブックに残りうるため採用していません。

## 今後の予定・検討中の事項(開発者向け)

- **PySCF版のノートブックへの対応**: ipywidgetsが8.x系に更新された場合に備えて、UMA版の「II-0」のセルと同様のセルを
  `ColabApp.ipynb`にも追加することを検討しています。
- **2つ目の計算目的を追加するとき**: 下記「設計方針メモ」のとおり、`config/purposes.yaml`の移行を検討します。


## requirements-lock.txtを軽量に保つ理由

`pip freeze`は現在の環境に入っている**すべての**パッケージ(Colabの場合、
プリインストール済みのものだけで700個以上)を書き出してしまいます。これを
そのまま`requirements-lock.txt`として使うと、次回以降のインストール処理
(1パッケージずつインストールして失敗箇所を特定する方式)が700回以上の
`pip install`呼び出しになり、非常に時間がかかっていました。

対策として、`ColabApp.ipynb`のSetup Section側で、`pip freeze`の結果から
「`requirements.txt`に明示的に書かれているパッケージ」と「`gpu4pyscf`関連
パッケージ」だけを抜き出して`requirements-lock.txt`を生成するように変更しました。
これにより、ロックファイルは`requirements.txt`とほぼ同じ数(数個)の
パッケージだけを含む軽量なものになります。UMA版(`ColabApp_UMA.ipynb`)も同じ方針で、
`requirements-uma.txt`に書かれたパッケージだけを`requirements-uma-lock.txt`に記録します
(どちらのロックファイルも、現在はGit管理の対象外です)。

**トレードオフ**: この方式では、pyscfやgeometricなどが依存する間接的な
パッケージ(例: h5py等)まではバージョンを固定していません。そのため、
将来それらの間接的な依存パッケージに破壊的変更が入った場合、影響を受ける
可能性はゼロではありません。ただし、これは元々`requirements.txt`(下限/上限
指定のみ)が持っていたのと同程度のリスクであり、`pip freeze`の全量出力
(700個以上を厳密固定)と比べて特別にリスクが増えたわけではありません。
また、Colabの「ランタイムバージョン」を固定していれば、Python本体や
numpy等の基盤部分はそもそも変化しないため、実際に影響が及ぶ範囲は限定的
です。万一この間接的な依存関係が原因で動かなくなった場合も、1パッケージ
ずつインストールする方式のおかげで、どのパッケージが問題かはすぐに
分かるようになっています。

## 設計方針メモ: 新しい計算目的(TS最適化等)を追加するときの方針

TS最適化のように新しい「計算目的」を追加する場合、必ず新しいコード
(処理関数)が必要になり、その点では設定ファイルだけでは完結しません。
ただし、**「`config/purposes.yaml`に載っている計算目的」と「実際に
バックエンドで処理できる計算目的」を必ず一致させる**ことには意味があるため、
今後は以下の方針で実装します。

1. `config/purposes.yaml`は今まで通り維持し、UI(ドロップダウン)はここから生成する。
2. バックエンド側に `key` → 処理関数 の対応表を1箇所だけ持つ(例: `pyscf_backend/dispatch.py`の`_HANDLERS`辞書)。
3. `tests/`に、「`purposes.yaml`のキー集合」と「`_HANDLERS`のキー集合」が
   完全に一致することを確認する自動テストを追加する。

これにより、UIに選択肢を追加したのに処理を実装し忘れる/処理を実装したのに
UIに出し忘れる、というズレをテストが機械的に検出できる。基底関数・計算手法
のように「既存の処理内でパラメータだけ変える」ものは、これまで通り設定
ファイルの追記のみで拡張できる(この場合は上記のような不整合が起こりえない)。

## 拡張のしかた(新しい手法・基底関数を追加する)

コードを変更せず、`config/` 以下のYAMLに1エントリ追加するだけで選択肢が増えます。
実際にB3LYP・6-31G系列を追加した際も`engine.py`等のコードは無変更のまま
動作しました。

例: PBE0を追加する場合、`config/functionals.yaml` に以下を追記します。

```yaml
- label: "PBE0"
  key: "pbe0"
  engine: "dft"
  xc: "pbe0"
```

例: 6-31+G**を追加する場合、`config/basis_sets.yaml` の `main_group` に以下を追記します。

```yaml
- label: "6-31+G**"
  key: "6-31+g**"
  pyscf_basis: "6-31+g**"
  ecp: null
```

### `purposes.yaml`(計算目的)の位置づけについて

計算手法・基底関数とは異なり、TS(遷移状態)最適化のような**新しい計算目的**の
追加には、`config/purposes.yaml`に1行足すだけでは済まず、新しいコード
(新しい最適化関数・GUI要素等)が必ず必要になります。これは、手法・基底関数が
「同じ計算パイプライン(Mole構築→SCF実行)の中のパラメータ違い」であるのに
対し、計算目的は「実行される処理そのものが異なる」ためです。

そのため、`purposes.yaml`の役割は「コード変更なしで機能を増やす」ことではなく、
**「バックエンドの機能一覧と画面上の選択肢に食い違いが起きないようにする」
という一貫性の保証**に変わります。この目的であれば、`purposes.yaml`を
使い続ける意味は十分にあると考えます。以下、設定ファイルを使う場合・
使わない場合、それぞれの実装方針です。

**方針A: 設定ファイル(YAML)を使い、`handler`キーで実装と対応付ける**

```yaml
# config/purposes.yaml (将来のイメージ)
- key: "geometry_optimization"
  label: "構造最適化"
  handler: "geometry_optimization"   # ← 対応するPython側のハンドラ名
  supports_frequency: true
- key: "ts"
  label: "TS(遷移状態)最適化"
  handler: "ts_optimization"
  supports_frequency: true
```
```python
# gui.py or 別モジュールで、handler名 → 実際の関数、の対応表を持つ
PURPOSE_HANDLERS = {
    "geometry_optimization": optimize.run_geometry_optimization,
    "ts_optimization": optimize.run_ts_optimization,  # 実装時に追加
}

# 起動時に、YAMLに書かれている全purposeについてハンドラが
# 登録されているかを検証する(片方だけ追加してもう片方を忘れる、という
# 事故をここで検出する)
def validate_purpose_handlers(purposes, handlers):
    missing = [p["key"] for p in purposes if p["handler"] not in handlers]
    if missing:
        raise RuntimeError(f"ハンドラが未登録のpurposeがあります: {missing}")
```
新しい計算目的を追加する際は、①`purposes.yaml`にエントリを追記、②対応する
関数を実装、③`PURPOSE_HANDLERS`に登録、の3点セットが必要ですが、
どれか1つを忘れると`validate_purpose_handlers()`がノートブック起動時に
エラーで教えてくれるため、「画面には選択肢があるのに実装がない」
「実装したのに画面から選べない」という食い違いを機械的に防げます。

**方針B: 設定ファイルを使わず、Pythonのデコレータで登録する**

```python
# optimize.py
PURPOSE_REGISTRY = {}

def register_purpose(key, label, supports_frequency=True):
    def _decorator(func):
        PURPOSE_REGISTRY[key] = {"label": label, "handler": func,
                                  "supports_frequency": supports_frequency}
        return func
    return _decorator

@register_purpose("geometry_optimization", label="構造最適化")
def run_geometry_optimization(...):
    ...

@register_purpose("ts", label="TS(遷移状態)最適化")
def run_ts_optimization(...):
    ...
```
実装とメタデータ(ラベル・対応可否)が同じ場所に書かれるため、「実装だけ
追加して登録を忘れる」という食い違いがそもそも起きにくいのが利点です。
YAMLファイルを介さない分、非プログラマが選択肢一覧をぱっと確認しづらい
(コードを読む必要がある)のが欠点です。

**方針C: 設定ファイルは表示用ラベルのみとし、対応関係はテストで検証する**

`purposes.yaml`は現状通り「ラベルのみ」の簡素な形に留め、`config/`の
内容とコード側の対応関係が崩れていないかを`tests/`内の自動テストで
継続的に確認する方針です。実装の手間は増えませんが、食い違いに気づけるのは
テスト実行時(≒Colabで動かす前にご自身の手元で気づける)に限られ、
方針Aのような実行時の即時検出はできません。

**このプロジェクトでの推奨**: 現状は計算目的が1つ(構造最適化)しかなく
過剰な設計になるため、今すぐ方針A/Bを導入する必要はないと考えます。
次にTS最適化等、2つ目の計算目的を追加するタイミングで方針A(YAML+
ハンドラ対応表+起動時検証)への移行をご提案します。理由は、`purposes.yaml`
が持つ「非プログラマにも選択肢一覧が一目で分かる」という利点を保ちつつ、
起動時の自動検証で一貫性を機械的に保証できるためです。


## パッケージ構成の見直し(v0.2.2)

- **実施済み(段階1)**: PySCF版のパッケージ`qcapp`を`pyscf_backend`に、UMA版のパッケージ`uma_app`を`uma_backend`に改名した
  (`git mv`で、履歴を保ったまま改名。コードの変更はない)。画面(`gui.py`・`gui_uma.py`)を`gui`層に分けたあと、
  計算側のパッケージが「バックエンド」になるため、`*_app`でなく`*_backend`とした。名前の表記(アンダースコアあり・
  スネークケース)も、これで統一した。
  このファイルの経緯の記述(v0.2.1以前)に出てくるパッケージ名は、改名後の名前に置き換えてある(旧名は`qcapp`・`uma_app`)。
- **検討中(段階2以降。未決定・未実施)**: 「ノートブック → 画面(gui) → バックエンド」の向きを、パッケージ構成で確保する。
  - 画面の層に置くもの: `common/colab_widgets.py`・`gui_parts.py`・`gui_input.py`・`gui_output.py`・`plot_common.py`(3D表示。
    使っているのは`gui_parts.py`だけ)と、`gui.py`・`gui_uma.py`。将来のインプットファイル作成の画面も、ここに置く。
  - `common/energy_plot.py`は、エネルギーの換算・相対エネルギー(`uma_report.py`が使う。バックエンド側)と、
    クリックできるSVGグラフ(Colabのコールバックに依存する。画面側)が同居している。分ける必要がある。
  - 残る共通部分(`config.py`・`version.py`・`io_reader.py`・`writer_xyz.py`・換算)は、バックエンドだけの共通部品になる。
  - `uma_hf`は、当面`uma_backend`に残す。ノートブックが直接読み込んでよいのは、「画面」と「環境準備用の関数(`uma_hf`)」だけ。
  - パッケージ名は、一般的すぎる名前(`gui`・`core`・`common`)を避ける案を検討中(プロジェクト名の名前空間パッケージの下に置く案、
    または`common_backend`・`gui_frontend`のような名前の案)。

## UMA版の振動数解析(Hessian)を自前実装のままにしている理由(v0.2.2での検討)

v0.2.2で、「Hessianの計算を、ASEの`Vibrations`に置き換えたほうが信頼性が高いか」を検討し、
**自前実装(`uma_backend/uma_freq.py`)を維持**して、ASEとの照合テストを追加することにした。

- 置き換えて減るのは、有限差分のループ(`compute_hessian_fd`)だけである。ASEの`Vibrations`も、力の中心差分
  (既定0.01 Å)で作った行列を対称化する方式で、実質的に同じ計算である。
- 並進・回転のモードを除いて、振動モードだけを取り出す処理(`harmonic_analysis`)は、ASEの標準機能にはないため
  (ASEの`Vibrations`は、ゼロ付近のモードが混ざった3N個を返す)、置き換えても、自前で残る。
- 置き換えると、ASEのキャッシュファイル(`Vibrations`は、変位ごとの結果をフォルダに書き出す)の管理、
  ASEのバージョンごとのAPIの変化への追従、GUIへの進捗通知(原子ごとのコールバック)の作り直しが、必要になる。
- 信頼性の根拠は、ASEを使うことそのものではなく、独立した基準との照合にある。`tests/test_uma_freq.py`は、
  (1)解析解(バネのモデル)・同位体効果・回転不変性などと、(2)ASEの`Vibrations`(EMTのCu₂・Cu₃・Cu₄)および
  `VibrationsData.from_2d`(バネのモデルのHessian)と、一致することを確認する。ASEが入っていない環境では、
  (2)だけスキップされる。
- 限界: 照合で確認できるのは、実装(単位換算・質量の重み・並進回転の除去)の正しさである。UMAという機械学習モデルの
  精度は、確認できない(必要なら、Colab実機で、PySCF版との比較などを手動で行う)。
- 検討して見送った案: 並進・回転のモードに残る微小な振動数を、構造とUMAの力の質の診断として、ログに表示する機能。

## バージョン管理・ブランチ運用の方針

### そもそも「ブランチ」とは

一言でいうと、**同じコードの「並行世界」を作れる仕組み**です。`main`ブランチ(本流)から
枝分かれ(branch)した別バージョンの中でファイルを自由に編集・コミットでき、
そこでの変更は元の`main`には影響しません。うまくいったら`main`に合流(merge)させ、
ダメだったらそのブランチごと捨てれば`main`は無傷のまま、ということができます。

### このプロジェクトで使うブランチ

ご提示いただいた nvie の Gitflow ( https://nvie.com/posts/a-successful-git-branching-model/ )
は、複数人が同時並行で多くの機能を開発する中〜大規模プロジェクト向けのモデルです。
このプロジェクトは基本的にお一人での開発ですので、Gitflowをそのまま採用するとブランチの
種類が多すぎて逆に管理コストが増えます。そこで、Gitflowの考え方を踏まえつつ、
**必要な部分だけを取り入れた縮小版**を提案します。

| ブランチ | 役割 | 存続期間 |
|---|---|---|
| `main` | **常に動く状態を保つ本流。ここに乗っている各コミットが「1つのリリース」**。タグ(v0.1.2等)は必ずこのブランチ上に打つ | 恒久的 |
| `develop` | 次のリリースに向けた作業をまとめる場所。複数のfeatureブランチをここに集約してから、動作確認してmainに合流させる | 恒久的 |
| `feature/<name>` | 1つの新機能ごとに`develop`から切る作業用ブランチ(例: `feature/b3lyp-and-more-basis`, `feature/uma-preopt`)。完成したら`develop`に合流させ、削除する | 一時的 |

`release`ブランチと`hotfix`ブランチは、今の規模では作らないことを提案します。理由は次の
「masterとreleaseブランチの違い」で説明します。

### `master`(=`main`)ブランチと`release`ブランチの違い

ここが分かりにくいポイントだと思いますので整理します。

- **`master`は「もう完成してリリース済みのコードだけ」が乗っている場所**です。
  `master`上の1コミット = 1つの正式リリースで、そこには必ずバージョンタグが付きます。
- **`release`ブランチは「リリース直前の、仕上げ作業専用の一時的な作業場所」**です。
  nvieの記事の想定では、`develop`に複数人が次々と新機能を追加し続けている状況で、
  「そろそろ次のリリースを出したいが、develop上の新機能追加はまだ止めたくない」
  という場面が出てきます。このとき、develop上の"その時点"の状態だけを`release`
  ブランチとして切り出し、そこで最終バグ取り・バージョン番号の確定などの仕上げを行う
  ことで、**develop側は他の人がその間も新機能をどんどん追加し続けられる**ようにする、
  という「作業の分離」が`release`ブランチの存在理由です。
  仕上げが終わったら`release`ブランチを`master`と`develop`の両方にマージして、
  `release`ブランチ自体は役目を終えて削除します。

**つまり`release`ブランチは、"同時並行で動いている複数の未完成機能" が
存在して初めて意味を持つ仕組み**です。お一人で開発していて、機能を1つずつ順番に
`feature`ブランチで作っている今の進め方であれば、`develop`がそのまま
「次のリリース候補」を兼ねられるため、`release`ブランチを別途作る必要はありません。
`hotfix`ブランチ(リリース済み`master`の緊急パッチ用)も同様に、`develop`側で
現在進行中の別作業と衝突する心配がなければ、`main`上で直接直せば十分です。
将来、共同開発者が増えて複数機能が同時進行するようになったら、その時点で
`release`/`hotfix`ブランチの導入を検討すれば大丈夫です。

### GitHub上でのブランチの見え方

`main`・`develop`・`feature/*` はすべて同じ1つのGitHubリポジトリの中に共存できます
(別々のリポジトリを作る必要はありません)。`git push origin <ブランチ名>` を実行した
ブランチだけがGitHub上にも現れ、リポジトリ右上の「Branches」やコードのブランチ切り替え
プルダウンから確認できます。`feature/*` は完成後に`develop`へ合流したら用済みになる
一時的な作業ブランチなので、GitHubに逐一pushせず手元だけで作業し、合流できたら
ローカルでもリモートでも削除してしまって構いません(バックアップ目的で毎回pushしても
問題はありません)。

**エンドユーザー(高校生等)から見えるのは常に`main`ブランチだけ**です。Colabの共有リンクは
`.../blob/main/ColabApp.ipynb` のように特定のブランチ・ファイルを指しているため、
`develop`や`feature/*`で何を作業していても、`main`にマージしてpushするまでは
公開版には一切影響しません。

### 具体的な運用の流れ

1. 新機能に着手するとき: `git checkout develop && git checkout -b feature/xxx`
2. `feature/xxx` 上で自由にコミットを重ねる(細かいコミットで構いません)。
3. 動作確認(Colab上での実行含む)が取れたら `develop` に合流させて削除:
   ```
   git checkout develop
   git merge --no-ff feature/xxx
   git branch -d feature/xxx
   ```
   `--no-ff` を付けるのがポイントで、これにより「featureブランチをまとめて
   取り込みました」という合流専用のコミットが必ず1つ作られます(このコミットの
   メッセージに、その機能で何ができるようになったかを書いておきます)。
4. `develop`に十分な変更が溜まり、リリースしたくなったら `main` に合流させてタグを打つ:
   ```
   git checkout main
   git merge --no-ff develop
   git tag -a v0.2.0 -m "このリリースで何が変わったかをここに書く"
   git push origin main --tags
   ```

### 変更履歴の記録方法(CHANGELOG.mdは廃止しました)

`git merge --no-ff` で作られる合流コミットのメッセージや、リリース時のタグメッセージ
そのものが「このバージョンで何が変わったか」の記録になります。これをそのまま
GitHubの **Releases** 機能(タグを選んで「Create a new release」からリリースノートとして
貼り付けるだけ)に転記すれば、変更履歴はGitHub上の1箇所(タグメッセージ・Releaseページ)
に集約できます。`CHANGELOG.md`は二重管理になるため削除済みです。新しいタグを打つ際は、
必ず `git tag -a vX.Y.Z -m "変更点"` のメッセージを具体的に書き、GitHub上でもその
タグから「Create a new release」→リリースノートに同内容を貼り付けてください。

### バージョン番号(`__version__`)の更新

`__version__` は、**リポジトリ全体のリリース番号(Gitタグ。先頭に`v`を付けた`vX.Y.Z`)と同じ値**にします。
値は`common/version.py`に1か所だけ書いてあり、`pyscf_backend.__version__`・`uma_backend.__version__`は、その別名です
(以前は2つの`__init__.py`に別々に書いていたため、タグはv0.1.16なのに`__version__`が0.1.12のままだった
更新漏れがありました)。新しい機能を`develop`から`main`へリリースする直前に、次をすべて行います。

1. `common/version.py`の`__version__`を、新しい`X.Y.Z`に更新する(`pyscf_backend`・`uma_backend`は別名なので、更新は不要。
   `tests/test_version_sync.py`が、両パッケージの値と一致していることを検査します)。
2. `README.md`冒頭の「現在のバージョン」を、`vX.Y.Z`に更新する(`tests/test_readme.py`が、`__version__`との
   一致、リンク、コードフェンス、記載ファイルの存在を検査します)。
3. このファイル末尾の「仕様書」(ファイル一覧・各モジュールと関数の仕様・呼出先の一覧・テストの対象)を見直し、
   追加・変更したファイルと仕様を反映する。
4. テストが通ることを確認する(`python3 -m unittest discover -s tests -p "test_*.py"`)。
5. Colab実機で動作を確認したあと、`main`上で`git tag -a vX.Y.Z -m "変更内容"`を作成して、pushする。

この手順により、GUI表示、出力ログ、README、両計算エンジンの版数が異なるリリースを防ぎます。

### lockファイルの運用(`main`ブランチだけでGit管理する)

`requirements-lock.txt`(PySCF版)・`requirements-uma-lock.txt`(UMA版)は、**`main`ブランチにだけ**含める。
開発中のブランチ(`develop`・`feature/*`)には含めない。

- **仕組み**: `.gitignore`には、`AGENTS.md`・`requirements-lock.txt`・`requirements-uma-lock.txt`の3つを
  **全ブランチ共通で**書いておく(`AGENTS.md`は、lockファイルと逆に、`main`以外で追跡する。次の節を参照)。`.gitignore`が効くのは、まだ追跡していないファイルだけである。
  `main`でlockファイルを`git add -f`(強制追加)して一度コミットすれば、以後は追跡されるため、
  `.gitignore`に書いてあっても、変更は普通の`git add -A`で記録される。`develop`・`feature/*`には
  lockファイルが存在しないため、追跡されず、`.gitignore`のとおり無視される。
- **Colab上の挙動**: ノートブックのインストールのセルは、lockファイルがあればそれを、なければ
  `requirements*.txt`を使う。そのため、`main`で実行すると、常に動作確認済みの同じ組み合わせになり、
  開発中のブランチでは、`requirements*.txt`の指定どおりにインストールされる。
- **lockファイルを作る場所**: Colab上で、ノートブックが自動生成する(PySCF版は「2-c」、UMA版は「3-b」のセル)。
  生成先はColabの`/content/qchem_colab_app/`なので、リリースのときに、ダウンロードして、手元の`main`に置く。
- **`requirements*.txt`を変更したリリース**: 古いlockファイルには新しいパッケージが含まれず、lockを使うインストールで
  不足が出るため、Colabで確認する前に、`main`の古いlockを`git rm`で削除して、pushしておく
  (Colabの実行で、新しいlockが生成される)。
- **注意(守ること)**:
  - `main`を`develop`にマージしない(lockファイルが`develop`に入ってしまう)。マージは、常に`develop`→`main`の向き。
  - `develop`・`feature/*`では、lockファイルを`git add -f`しない。
  - `AGENTS.md`を`git add -f`するのは、`develop`・`feature/*`で追跡を始める最初の1回だけ(次の「`AGENTS.md`のGit管理」を参照)。
    `main`では、しない。
  - `main`から`develop`へ切り替えると、lockファイルが作業フォルダから消える。`main`にだけ存在するためで、正常。
  - Colabのランタイムのバージョンが変わった場合は、lockの内容が合わなくなることがある。そのときは、
    lockを削除して、Colabで再生成する。

### `AGENTS.md`のGit管理(`main`では追跡しない、`develop`・`feature/*`では追跡する)

`AGENTS.md`は、開発者向けの文書であり、エンドユーザーが見る`main`には載せない。一方、`develop`・`feature/*`では、
GitHubに履歴とバックアップを残すため、追跡する(v0.2.2から。それまでは、全ブランチで追跡対象外だった)。

- **仕組み**:
  - `.gitignore`の`AGENTS.md`の行は、全ブランチ共通で残す(ブランチごとに`.gitignore`を変えると、マージのたびに
    競合や上書きが起きるため)。`.gitignore`は、まだ追跡していないファイルにしか効かないので、追跡を始めた
    `develop`・`feature/*`では、変更は普通の`git add -A`で記録される。
  - `develop`・`feature/*`で追跡を始めるときは、最初の1回だけ`git add -f AGENTS.md`を行う(v0.2.2の作業ブランチで実施)。
  - `develop`→`main`のマージでは、`AGENTS.md`が`main`に入ってしまう。そのため、マージの直後(コミットの前)に、
    `git rm --cached --ignore-unmatch AGENTS.md`で、`main`の追跡から外す(手順は、次の「リリースの手順」の4)。
  - 2回目以降のリリースでは、「`main`では削除済み」と「`develop`で変更」がぶつかり、
    `CONFLICT (modify/delete): AGENTS.md`と表示される。これは想定どおりで、同じ`git rm --cached`で解消できる。
- **手順の漏れを防ぐ仕組み(gitフック)**: `.githooks/`に、次のフックを置いている(全ブランチで追跡)。
  - `pre-commit`・`pre-merge-commit`: `main`上で`AGENTS.md`が追跡されている状態のコミットを、拒否する(検査の本体は`check-agents.sh`)。
  - `pre-push`: `main`・タグのpushに、`AGENTS.md`を含むコミットが入っていたら、pushを中止する。
  - フックは、クローンごとに、次の設定を1回だけ行わないと有効にならない(設定は`.git/config`に保存され、リポジトリには含まれない):
    `git config core.hooksPath .githooks`と`chmod +x .githooks/*`。
  - フックは、自動で直すのではなく、間違いを止めて、直し方を表示する。`--no-verify`を付けると、フックはスキップされる(付けないこと)。
  - `tests/test_githooks.py`が、フックの動作(拒否・許可)を、一時的なリポジトリで検査する。
- **注意(守ること・起こること)**:
  - `main`を`develop`にマージしない。`main`では`AGENTS.md`が追跡されていないため、`develop`の`AGENTS.md`まで削除されてしまう。
    マージは、常に`develop`→`main`の向き。
  - `AGENTS.md`を編集したら、ブランチを切り替える前に、コミットする(未コミットのまま切り替えると、gitが警告して拒否することがある)。
  - `main`に切り替えると、`AGENTS.md`が作業フォルダから消えることがある(`main`では追跡していないため)。`develop`に戻ると、再び現れる。どちらも正常。
  - `main`の最新の状態には`AGENTS.md`が無いが、マージコミットを通して履歴をたどると、`develop`上の`AGENTS.md`の過去の内容は見える。
    GitHubが公開リポジトリの場合、`develop`・`feature/*`上の`AGENTS.md`も、第三者が読める。秘密情報は、書かない。
  - `main`に`AGENTS.md`が入った状態でコミットしてしまった場合(フックが無効だった等)は、`git rm --cached AGENTS.md` →
    `git commit`で追跡から外す。履歴を消す操作(強制プッシュ等)は、しない。`push`済みの場合は、状況を相談する。

### `main`ブランチへのリリース(マージ)の手順(Claudeが、`main`へのマージのコマンドを案内するときは、必ず次をすべて含める)

利用者はgitに不慣れなため、**実行するコマンドと、実行するタイミングを、毎回、省略せずに書く**。
`vX.Y.Z`は新しいバージョン、`feature/名前`は作業ブランチ名に置き換える。

1. **事前確認**:
   - `git status` が `nothing to commit, working tree clean` であること。
   - `grep -n "lock\|AGENTS" .gitignore` で、`.gitignore`に`AGENTS.md`・`requirements-lock.txt`・
     `requirements-uma-lock.txt`の3行があること。足りなければ、`printf 'ファイル名\n' >> .gitignore`で追加する。
   - `git config core.hooksPath`が`.githooks`と表示されること。表示されなければ、`git config core.hooksPath .githooks`と
     `chmod +x .githooks/*`を実行する。
   - `git ls-files AGENTS.md`が、`develop`上で`AGENTS.md`と表示されること(追跡されていること)。
2. **バージョンの更新**(作業ブランチ上): `common/version.py`・`README.md`冒頭を`X.Y.Z`に更新し、
   このファイル末尾の「仕様書」を見直し、テストを通して、コミットとpushをする
   (詳しくは「バージョン番号(`__version__`)の更新」)。
3. **`develop`への統合**: `git checkout develop` → `git pull origin develop` →
   `git merge --no-edit feature/名前` → `git push origin develop`。
4. **`main`への統合**(`AGENTS.md`を`main`に入れない手順を含む。コミットの前に、必ず、止めて確認する):
   1. `git checkout main` → `git pull origin main`
   2. `git merge --no-ff --no-commit develop`(マージの内容を確認してからコミットするための指定。
      `CONFLICT (modify/delete): AGENTS.md`と出るのは、想定どおり。それ以外のファイルで`CONFLICT`と出たら、
      `git merge --abort`で中止して、状況を相談する)
   3. `git diff --name-only --diff-filter=U`(`AGENTS.md`だけが表示されるか、何も表示されないこと)
   4. `git rm --cached --ignore-unmatch AGENTS.md`
   5. `git diff --name-only --diff-filter=U`(何も表示されないこと)と、`git status`(`AGENTS.md`が出ないこと)
   6. `git commit -m "vX.Y.Z: developをmainに統合"` → `git push origin main`(フックが、`AGENTS.md`の混入を検査する)
5. **`requirements*.txt`を変更したリリースだけ**: `git rm requirements-lock.txt requirements-uma-lock.txt` →
   `git commit -m "古いlockファイルを削除(依存パッケージの変更のため)"` → `git push origin main`
   (`main`にlockファイルが、まだ無い場合は不要)。
6. **Colabでの確認とlockファイルの生成**: 両ノートブックを、「1-b」セルの`BRANCH`を`main`にして、上から実行する。
   PySCF版の「2-c」セルが`requirements-lock.txt`を、UMA版の「3-b」セルが`requirements-uma-lock.txt`を生成する。
   動作を確認できたら、Colab左のファイルパネルで、`qchem_colab_app`フォルダ内の両ファイルを、右クリックから
   「ダウンロード」し、手元のリポジトリ直下(`main`が選ばれている状態)に置く。
7. **lockファイルの記録**(`main`上): `git add -f requirements-lock.txt requirements-uma-lock.txt` →
   `git status`(`new file:`または`modified:`の2つが出ること。`AGENTS.md`が出ないこと) →
   `git commit -m "vX.Y.Z: 動作確認済みの依存バージョンを記録(lockファイル)"` → `git push origin main`。
8. **タグ**: `git tag -a vX.Y.Z -m "変更内容"` → `git push origin vX.Y.Z`。
   (タグは、lockファイルの記録のあとに付ける。タグの時点のlockが、その版の依存バージョンになる。)
9. **後片付け**: `git branch -d feature/名前` → `git push origin --delete feature/名前` →
   `git checkout develop`(開発に戻る。lockファイルが作業フォルダから消え、`AGENTS.md`が現れるのは正常)。

### ロールバックの方法

- 「最新版に不具合があった場合にすぐ前の版へ戻す」には、
  `git checkout v0.1.1` のようにタグを指定してチェックアウトするか、
  問題のコミットを `git revert <コミットID>` で打ち消してください。
- **lockファイル**: `main`ブランチには、動作確認済みの依存バージョンを記録した
  `requirements-lock.txt`・`requirements-uma-lock.txt`がGit管理で含まれるため、タグを指定して
  チェックアウトすれば、その版の依存バージョンも一緒に再現できます(運用は、前の
  「lockファイルの運用」を参照)。


## トラブルシューティングの経緯・開発メモ(README.mdの「トラブルシューティング」には、利用者向けの要点だけを載せている)


- **`pip install` が `python setup.py egg_info did not run successfully` /
  `metadata-generation-failed` で失敗する**(v0.1.0で実際に発生した不具合):
  原因は、`requirements.txt` で `numpy` / `scipy` / `PyYAML` などを
  Colabのベースイメージに既に入っているものと異なる厳密バージョンで
  `==` 指定してしまい、pipがそのバージョンをソースからビルドしようとして
  失敗していたことでした(Python 3.12ではビルドに使う`distutils`が
  標準ライブラリから削除されているため、古いビルド方式に依存するパッケージの
  ソースビルドが失敗しやすくなっています)。
  **v0.1.1で対策済み**: `requirements.txt` から `numpy`/`scipy` の指定を削除し、
  残りのパッケージも `==` の厳密指定から `>=` の最小バージョン指定に変更しました。
  また、Setup Sectionのインストールセルを、1パッケージずつインストールして
  失敗箇所を特定できる方式に変更しています。もし今後も同種のエラーが出た場合は、
  表示される「どのパッケージで失敗したか」とエラー末尾の内容をご確認ください。
- **構造最適化のエネルギー履歴(グラフ)がほぼ1点しかない場合**:
  `pyscf_backend/optimize.py` の `_make_callback()` 内で、
  PySCFのgeomeTRIC連携が実行時に渡すコールバック引数のキー名
  (`energy` / `e_tot` / `mol` / `coords` 等)が、お使いのPySCFのバージョンと
  一致していない可能性があります。該当箇所のキー名を、実際のPySCFの
  ドキュメント・ソースコード(`pyscf.geomopt.geometric_solver`)と
  照らし合わせて調整してください。
- **GPU4PySCFのインストールに失敗する / GPUが使われない**:
  ColabのCUDAバージョンと `gpu4pyscf-cuda12x` / `gpu4pyscf-cuda11x` の
  対応関係が変わっている可能性があります。`ColabApp.ipynb` のSetup Section内、
  GPU4PySCFインストールセルのパッケージ名を読み替えてください。GPUが
  使えなくても、CPU実行として問題なく計算は継続されます。GPUを使うかどうかは、GPUランタイム
  (`nvidia-smi`が成功するか)かどうかで**自動的に判定**します(以前あったGUIのチェックボックスは
  v0.1.17で廃止しました。実行ログに「GPUランタイム: 検出されました/検出されませんでした」と表示されます)。
- **最終構造でのCPU再計算・振動数計算になぜGPUを使わないのか**:
  GPU4PySCFの解析的Hessian・分子軌道(cubegen)・Mulliken電荷計算などの
  対応状況は主にDFT向けに整備されており、現在のプロトタイプで使っているHFでの
  対応状況や、GPU上のSCFオブジェクトをこれらの解析関数にそのまま渡せるかは
  今回のリサーチでは確認しきれませんでした。無理にGPUを使わせようとして
  失敗する(あるいは気づかないまま不正確な結果になる)リスクを避け、
  確実に動作するCPU版に一度変換する設計にしています。GPUを使う場合の
  デメリットとしては、Hessian計算はエネルギー計算よりメモリを多く使うため
  Colab無料枠のGPU(T4, VRAM 約15GB)ではむしろメモリ不足になりやすいこと、
  GPU側のこれらの機能はCPU版ほど枯れていない(実績が少ない)ことが挙げられます。
  Hessian計算だけ試験的にGPUを使う(失敗したらCPUにフォールバックする)という
  改善は可能だと考えていますが、可視化まわりで何度か実機でしか分からない
  不具合が続いたこともあり、今回は見送っています。ご要望があれば次の対応で
  試験的に実装します。
- **SCFが収束しない**: `engine.run_scf()` がレベルシフト付きで自動的に
  1回リトライしますが、それでも収束しない場合は画面に日本語の原因・対策が
  表示されます。初期構造・電荷・スピン多重度・基底関数の設定を見直してください。
- **moldenファイルの分子軌道がMacMolPltで表示されない**: v0.1.3で
  `mol.cart = True`(デカルト型のd/f軌道を使用)に変更し、MacMolPltが
  分子軌道の等値面表示に対応しているのがデカルト型ガウス関数のみである
  (球面調和関数型/5D7Fには対応していない)という制約に合わせました。
  ただし、開発環境の制約により実際にMacMolPltで開いての確認はできていません。
  この修正後も表示できない場合は、`.molden`ファイルの中身([Atoms]・[GTO]・
  [MO]の各セクション)をお送りいただければ、より詳しく原因を調査いたします。
- **原子電荷の球の色付けをESP(静電ポテンシャル)基準にしようとして断念した経緯**:
  v0.1.13で試みたが、`Cartesian orbitals for mol and spherical orbitals for
  auxmol not supported` というエラーで失敗した。原因は、`mol.cart = True`
  (上記のMacMolPlt対応のため)にしている一方、ESP計算に使う
  `pyscf.gto.fakemol_for_charges()` が内部で作る補助分子(auxmol)が
  球面調和関数型(cart=False)固定であり、両者の型が一致しないと
  `df.incore.aux_e2()` が計算できないため。`mol.cart`を計算のためだけに
  一時的にFalseへ切り替える対処も考えられるが、可視化まわりで実機検証なしの
  変更を繰り返すリスクを避け、v0.1.14でMulliken電荷基準の色分け(v0.1.12と
  同じ方式)に戻した。
- **エネルギー収束グラフが表示されない(経緯)**: v0.1.3で`display(fig)`に
  変更、v0.1.4で`display(HTML(fig.to_html(...)))`に変更したが、いずれも
  Colab上のipywidgets.Output()内では描画されなかった。plotlyのインタラク
  ティブ表示はJavaScriptの実行に依存しており、Colabの出力領域のサンドボックス
  環境でそのJavaScriptが実行されないことが原因と考えられる。v0.1.6で、
  JavaScript実行に一切依存しない静的PNG画像(kaleido使用)に変換して埋め込む
  方式に変更した。kaleidoは1.0以降でAPIが刷新されplotly 6.1.1以降が必須になり
  現行のplotly 5.x系とは非互換のため、`kaleido==0.2.1`に固定している。
  **その後、v0.1.17で、グラフを自前のSVGで描く方式に変更した**(点のクリックにも対応。詳細は
  下記「GUI部品の実装メモ」)。その後、v0.2.1で
  `common/plot_common.py`のplotly・kaleido依存の関数を削除し、`requirements.txt`からも外した。
- **電荷密度の等値面が単色にしか見えない**: 軌道(HOMO/LUMO)とは異なり、
  電子密度は原子核付近と分子表面付近とで値の桁が大きく異なるため、
  「最大値に対する割合」で等値面のしきい値を決める方式(軌道と同じ方式)
  だと3段階ともほぼ同じ範囲に収まってしまい、グラデーションに見えなかった。
  v0.1.6で、電子密度の可視化で慣習的に使われる絶対値
  (0.002 / 0.02 / 0.2 e/bohr^3 、原子単位)を既定値として使う方式に変更した。
- **操作画面が表示されず、Colab右側の「コードスニペット」パネルが
  (`enable_custom_widget_manager`で絞り込まれた状態で)開くだけになる**(UMA版のセットアップ中に
  実際に発生): ipywidgetsが8.x系に更新されていることが原因と考えられます。Colab標準のGUI部品の
  表示の仕組みはipywidgets 7.x向け(Colabのランタイムには7.7.1が入っています)で、8.xが読み込まれると
  Colab公式の「カスタムウィジェットマネージャー」を有効にしない限り表示されません。
  そのため、`requirements.txt`・`requirements-uma.txt`のどちらでもipywidgetsの版は指定せず、
  Colab標準のものをそのまま使っています(`tests/test_requirements.py`が検査します)。
  別のライブラリがipywidgetsを更新してしまった場合は、UMA版では「II-0」のセルが
  `output.enable_custom_widget_manager()`を実行します(PySCF版のノートブックには、現時点では
  同じセルを追加していません)。`common/gui_parts.py`・`common/gui_input.py`は、7.x・8.xの
  どちらでも動くように書いてあります。
- **UMA版のトラブルシューティング**(Hugging Faceのアクセス、`torch`の更新、GPUが使えない、など)は、
  [`uma_backend/README.md`](uma_backend/README.md)にまとめています。
- (v0.2.1の補足)`render_density`(電子密度の等値面)は、現在のGUIから使われていないため削除した。


## GUI部品の実装メモ(ドラッグ&ドロップ・グラフのクリック)

### 現在の方式

ファイルの**ドラッグ&ドロップ**と、エネルギーグラフの**点のクリック**は、どちらも
`common/colab_widgets.py`(ドロップ領域・コールバック登録)と`common/energy_plot.py`(グラフ)にある
「ブラウザ側のJavaScript → Colabのコールバック → Python」という
Colab公式の仕組み(`google.colab.output.register_callback`と`google.colab.kernel.invokeFunction`)で
実現しています。外部のライブラリ(Plotly.js等)には依存しません。

- **ドロップ領域**: ドロップされたファイルをJavaScriptが読み取り、Python側の関数に渡します
  (拡張子・5 MBの上限は、JavaScript側とPython側の両方で確認します)。「ファイルを選択」ボタンも
  残してあり、両方を使った場合は、最後に選んだファイルが使われます。
- **エネルギーグラフ**: 素のSVGで描き、点をクリックすると、その点の番号がPython側に渡されて、
  対応する構造が表示されます。選択中の点は赤い菱形で強調されます(ColabReactionと同じ体裁)。
  グラフの点そのものは静的なSVGなので、クリックの連携が動かない環境でも必ず表示され、
  スライダーで同じ操作ができます。
- **Colab以外の環境**: ドロップ領域は出さず、通常のファイル選択ボタンとスライダーだけで動作します。

JavaScriptを含むHTMLは、`ipywidgets.HTML`ウィジェットの`value`ではなく、`Output`ウィジェットの中で
`display(HTML(...))`して表示する必要があります(`ipywidgets.HTML`では`script`が実行されないため)。

### 以前の方式を採らなかった理由

- `ipywidgets`純正の`FileUpload`のドラッグ&ドロップ: 環境によって、ドロップを受け付けない場合があったため。
- Plotlyの`FigureWidget`によるクリック連動: Colab上で、グラフの枠だけが表示され、点が表示されない
  事例があったため(原因は特定できていません)。
- 静的PNG(kaleido)への変換: 点のクリックができないため。

### 共通の画面部品

PySCF版(`gui.py`)とUMA版(`gui_uma.py`)で共通の画面部品は、`common/gui_parts.py`にあります
(`StructureFileInput`、`EnergyStructureViewer`、`VibrationViewer`、`DownloadPanel`、`ChargeInput`、`MultiplicityInput`)。
電荷の表示・読み取りの関数(`format_charge`、`parse_charge`)、アップロードされた構造の読み込みと検証
(`load_uploaded_structure`)、ダウンロード項目(`xyz_download_items`)は、それぞれ`common/gui_input.py`(入力)・`common/gui_output.py`(出力)にあります。
ipywidgets 7.x・8.xのどちらでも動くように書いてあり、`tests/test_gui_parts.py`で、
ipywidgetsやColabの代用品を使って、部品どうしのつなぎ方を検査しています
(実際の見た目やJavaScriptの動作は、Colab実機での確認が必要です)。

### ColabReactionの実装について

エネルギーグラフのクリックによる構造表示やファイル入力は、`ColabReaction.ipynb`(Panelベースで、
`pn.pane.Plotly`の`click_data`と`pn.widgets.FileDropper`を使用)を参考にしました。
本プロジェクトはipywidgetsベースのため、Panelは使わず、上記の方式で実装しています。

### 依存ライブラリの増減

| 変更 | ライブラリ | 増減 |
|---|---|---|
| ドラッグ&ドロップ・グラフのクリック | (追加なし。標準ライブラリと、Colab標準のJavaScript連携のみ) | 増減なし |
| `.com`/`.gjf`/`.pdb`ファイルの読み込み | `ase` | **追加**(下限のみ指定、`requirements.txt`参照) |
| (見送り)`.mol`/`.sdf`ファイルの読み込み | `rdkit` | 未追加。追加する場合はもう1つライブラリが増えるため、ご希望があれば別途対応します |
| UMA版 | `fairchem-core`、`huggingface_hub`(`requirements-uma.txt`、PySCF版には影響しません) | UMA版のみ |


## 使用ライブラリの調査の経緯

本アプリを公開するにあたり、利用しているライブラリのライセンス・引用に関する
表示義務を調査しました。結論として、**いずれのライブラリも「コードを改変せず
依存パッケージとして利用する」範囲では、アプリの画面上に法的な表示義務を課す
ものはありません**でした(Apache-2.0・BSD・MIT等、いずれも許諾的なオープン
ソースライセンスで、著作権表示の保持義務は「そのソフトウェア自身のソース/
バイナリを再配布する場合」に生じるものであり、pip経由で利用しているだけの
本アプリには該当しません)。とはいえ、実際に計算を行っているソフトウェアを
明記することは学術的にも礼儀としても重要なため、以下の通り情報を整理し、
本README内に謝辞として記載することにしました。

**アプリ内の対応**: `README.md`にこの謝辞表を追加しました。あわせて、`ColabApp.ipynb`
の冒頭のMarkdownセルにも簡潔な謝辞を追記することを推奨します(次回のセル修正時に
反映します)。UMA(学習済みモデル)のライセンス・引用については、一次情報へのリンクを、
下記「UMA版」の節と`THIRD_PARTY_NOTICES.md`に掲載しています。

## v0.2.1 の見直しで行った整理(経緯)

PySCF版とUMA版の重複・ズレと、モジュールの分け方を見直した。

- 共通化したもの: 電荷・スピン多重度の入力欄(`gui_parts`)、構造の読み込みと検証(`gui_input.load_uploaded_structure`)、
  最適化の標準出力2ファイルとダウンロード項目(`writer_xyz.write_optimization_outputs`・`gui_output.xyz_download_items`)、
  ダウンロード名の既定値、`load_yaml`と`__version__`(`common/config.py`・`common/version.py`)。
- 独立のまま残したもの: エラー表示の`except`の連鎖、進捗・ログの文面、結果クラス(`OptimizationResult`等)の並行定義、
  設定ファイル(`defaults.yaml`・`uma_defaults.yaml`)、ノートブックの「1-a〜1-c」セル(リポジトリ取得前に動くため)。
- 分けたもの: `gui.py`の計算の流れ(最適化→CPU再計算→振動数→出力ファイルの書き出し)を`pyscf_backend/pipeline.py`へ、`gui_uma.py`の
  計算の流れ(アクセス確認→モデル→最適化→振動数→出力ファイルの書き出し)を`uma_backend/uma_pipeline.py`へ(GUIは入力・表示・
  例外のメッセージ変換だけ。両パイプラインは独立のまま)、`colab_widgets.py`から`energy_plot.py`(グラフと数値処理)、`visualizer_pyscf.py`から`analysis_pyscf.py`
  (HOMO/LUMO・Mulliken電荷の解析)、`gui.py`から`engine.gpu_runtime_detected`、`common/io_reader.py`から
  `engine.contains_transition_metal`、`gui_helpers.py`から`gui_input.py`(入力)と`gui_output.py`(出力)、`uma_engine.py`から`uma_hf.py`(Hugging Faceの認証。`UmaSetupError`は再エクスポートせず、利用側が`uma_hf.UmaSetupError`と書く)(扱える元素の範囲は、エンジンごとに独立と判断した)。
- 削除したもの: plotly依存の関数(`plot_common.py`)、`pyscf_backend/visualizer.py`(ファサード)、`render_density`、`render_trajectory`、
  `uma_backend/uma_inputs.py`。
- v0.2.1で追加した画面の改善: 構造ファイルを受け取ると、その構造を自動で表示する(`StructureFileInput`)。計算を実行し直すと、前回の結果の
  表示をすべて消す(各部品の`reset`)。
- lockファイル: `main`ブランチだけでGit管理する運用にした(「lockファイルの運用」「`main`ブランチへのリリース(マージ)の手順」)。
- 開殻分子の分子軌道: PySCFの開殻(UHF/UKS)では、`mo_occ`・`mo_energy`が2行、`mo_coeff`が3次元の配列になる。
  v0.2.0までは閉殻の形しか想定しておらず、開殻で軌道番号の判定と軌道の表示がずれていた。
  v0.2.1で、αスピンの軌道を基準に扱うように直した(`analysis_pyscf._occupations`・`visualizer_pyscf._mo_coeff_for_cube`)。


# 仕様書(ファイル一覧・モジュールと関数の仕様)

この仕様書は、リポジトリに含まれるソース、設定、ノートブックおよびテストの構成と公開的な仕様をまとめたものである。`.venv/`、`__pycache__/`、`.pytest_cache/`、`.ipynb_checkpoints/`、OS が生成する `.DS_Store` は使い捨ての環境・キャッシュであるため、構成図および仕様の対象外とする。

## ファイル一覧(全ファイル)

```text
qchem_colab_app
├── .githooks
│   ├── check-agents.sh
│   ├── pre-commit
│   ├── pre-merge-commit
│   └── pre-push
├── .gitignore
├── ColabApp.ipynb
├── ColabApp_UMA.ipynb
├── README.md
├── THIRD_PARTY_NOTICES.md
├── gui.py
├── gui_uma.py
├── requirements.txt
├── requirements-lock.txt
├── requirements-uma.txt
├── requirements-uma-lock.txt
├── common
│   ├── __init__.py
│   ├── colab_widgets.py
│   ├── config.py
│   ├── energy_plot.py
│   ├── gui_input.py
│   ├── gui_output.py
│   ├── gui_parts.py
│   ├── io_reader.py
│   ├── plot_common.py
│   ├── version.py
│   └── writer_xyz.py
├── config
│   ├── basis_sets.yaml
│   ├── defaults.yaml
│   ├── functionals.yaml
│   ├── purposes.yaml
│   ├── uma_defaults.yaml
│   └── uma_models.yaml
├── pyscf_backend
│   ├── __init__.py
│   ├── analysis_pyscf.py
│   ├── engine.py
│   ├── freq.py
│   ├── optimize.py
│   ├── pipeline.py
│   ├── visualizer_pyscf.py
│   └── writer_molden.py
├── uma_backend
│   ├── README.md
│   ├── __init__.py
│   ├── uma_engine.py
│   ├── uma_freq.py
│   ├── uma_hf.py
│   ├── uma_notice.py
│   ├── uma_optimize.py
│   ├── uma_pipeline.py
│   └── uma_report.py
├── tests
│   ├── fake_gui_env.py
│   ├── test_analysis_pyscf.py
│   ├── test_colab_widgets.py
│   ├── test_common_config.py
│   ├── test_config.py
│   ├── test_energy_plot.py
│   ├── test_engine.py
│   ├── test_githooks.py
│   ├── test_gui_input.py
│   ├── test_gui_output.py
│   ├── test_gui_parts.py
│   ├── test_io_reader.py
│   ├── test_notebooks_hidden_code.py
│   ├── test_pipeline.py
│   ├── test_readme.py
│   ├── test_requirements.py
│   ├── test_uma_config.py
│   ├── test_uma_engine.py
│   ├── test_uma_freq.py
│   ├── test_uma_hf.py
│   ├── test_uma_notebook.py
│   ├── test_uma_notice_report.py
│   ├── test_uma_optimize.py
│   ├── test_uma_pipeline.py
│   ├── test_version_sync.py
│   ├── test_visualizer.py
│   └── test_writer_xyz.py
└── references
    ├── ColabReaction.ipynb
    ├── ColabReaction_User_Guide_JP.pdf
    └── LICENSE
```

`references/` は実装方針を比較・参照するための外部資料であり、アプリケーションから import・実行されない。

`AGENTS.md` は、この一覧には含めていない。`develop`・`feature/*`にだけ存在し、`main`には存在しない(「`AGENTS.md`のGit管理」を参照)。

## 仕様(モジュールと関数)

- `ColabApp.ipynb`

	PySCF 版の Colab 実行入口。実行環境の表示、GitHub からのブランチ／タグ選択取得、依存関係と任意 GPU4PySCF の導入、lock ファイルの生成、サンプル構造の作成、`gui.build_app()` の表示を順に行う。目的はブラウザだけで PySCF 計算を実行可能にすること。すべてのコードセルは、メタデータ `cellView: form` と先頭行の `#@title 題名` により、既定でコードを折りたたんで題名だけを表示する（ColabReaction と同じ方式。クリックすればコードを開ける）。呼出先: `gui.build_app`, `pyscf_backend.__init__.load_yaml`（`gui` 経由）。

- `ColabApp_UMA.ipynb`

	UMA 版の Colab 実行入口。Hugging Face の利用案内とトークンの環境変数への設定、UMA 用依存関係の導入、GPU 確認、ウィジェット表示の準備、`gui_uma.build_app()` の表示を行う。トークンをノートブックの保存状態や GUI 状態へ残さない設計を採る。すべてのコードセルは、メタデータ `cellView: form` と先頭行の `#@title 題名` により、既定でコードを折りたたんで題名だけを表示する（ColabReaction と同じ方式。クリックすればコードを開ける）。呼出先: `uma_backend.uma_hf.login_from_environment`, `uma_backend.uma_hf.check_model_access`, `uma_backend.uma_hf.UmaSetupError`, `gui_uma.build_app`。

- `gui.py`

	PySCF 版アプリケーションの画面組み立て役。入力値の収集、アップロードされたファイルの読込みと検証、結果の表示（可視化・ダウンロード）、例外の利用者向けメッセージへの変換だけを行い、計算の流れは `pyscf_backend/pipeline.py`、共通画面部品は `common` に委譲する（v0.2.1 で計算の流れを `pipeline.py` へ移した）。

	- `build_app() -> ipywidgets.VBox`

		引数: なし。戻り値: 完成した PySCF GUI。目的: YAML 設定から画面を構成し、実行ボタンで `pyscf_backend.pipeline.run_calculation` を呼び、結果を可視化・ダウンロードへ接続する。実行ボタンは、計算中は無効化して二重実行を防ぐ。計算の開始時に、前回の結果の表示（グラフ・振動アニメーション・分子軌道・原子電荷・ダウンロード）をすべて消す。技術選定: GUI は薄いエントリーポイントに留め、再利用可能な画面部品・計算部品を分離する。呼出先: `pyscf_backend.load_yaml`, `common.gui_parts.StructureFileInput`, `common.gui_parts.EnergyStructureViewer`, `common.gui_parts.VibrationViewer`, `common.gui_parts.DownloadPanel`, `common.gui_parts.ChargeInput`, `common.gui_parts.MultiplicityInput`, `common.gui_input.load_uploaded_structure`, `common.gui_output.default_download_stem`, `pyscf_backend.analysis_pyscf.orbital_choices`, `pyscf_backend.analysis_pyscf.compute_mulliken_charges`, `pyscf_backend.visualizer_pyscf.render_orbital`, `pyscf_backend.visualizer_pyscf.render_charges`, `pyscf_backend.pipeline.CalculationSettings`, `pyscf_backend.pipeline.run_calculation`, `common.gui_output.xyz_download_items`。

- `gui_uma.py`

	UMA 版アプリケーションの画面組み立て役。PySCF 版と同じ入力・グラフ・振動・ダウンロード部品を再利用し、UMA 固有のモデル選択を持つ。入力値の収集、アップロードされたファイルの読込みと検証、結果の表示、例外の利用者向けメッセージへの変換だけを行い、計算の流れは `uma_backend/uma_pipeline.py` に委譲する（v0.2.1 で計算の流れを `uma_pipeline.py` へ移した）。

	- `build_app() -> ipywidgets.VBox`

		引数: なし。戻り値: 完成した UMA GUI。目的: 実行ボタンで `uma_backend.uma_pipeline.run_calculation` を呼び、結果を可視化・ダウンロードへ接続する。実行ボタンは、計算中は無効化して二重実行を防ぐ。計算の開始時に、前回の結果の表示（グラフ・振動アニメーション・ダウンロード）をすべて消す。技術選定: トークンは GUI で保持せず環境変数だけから読むため、ノートブック保存時の漏えいを避ける。呼出先: `uma_backend.load_yaml`, `common.gui_parts.StructureFileInput`, `common.gui_parts.EnergyStructureViewer`, `common.gui_parts.VibrationViewer`, `common.gui_parts.DownloadPanel`, `common.gui_parts.ChargeInput`, `common.gui_parts.MultiplicityInput`, `common.gui_input.load_uploaded_structure`, `uma_backend.uma_pipeline.CalculationSettings`, `uma_backend.uma_pipeline.run_calculation`, `uma_backend.uma_hf.UmaSetupError`, `common.gui_output.xyz_download_items`, `common.gui_output.default_download_stem`。

- `README.md`

	利用者向けの文書。利用目的、できること・できないこと、Colab 実行手順、UMA 版の使い方とライセンス・引用、トラブルシューティング、使用ライブラリを説明する。冒頭の「現在のバージョン」は `common.version.__version__` と一致させる。

- `THIRD_PARTY_NOTICES.md`

	PySCF 版・UMA 版で使用する第三者ソフトウェアのライセンスおよび通知情報を記録する。

- `requirements.txt` / `requirements-lock.txt`

	PySCF 版の依存関係を定義する。前者は導入時の許容範囲、後者は Colab またはローカルで確認した軽量な固定記録である。GPU4PySCF は Colab 側で条件付き導入する。

- `requirements-uma.txt` / `requirements-uma-lock.txt`

	UMA 版の依存関係を定義する。`fairchem-core`、ASE、Hugging Face クライアントを中心とし、Colab 標準の `ipywidgets` を維持する。

### common

PySCF と UMA のどちらにも依存しない共通基盤。引数・戻り値を元素記号、座標、数値、辞書などのプレーンな値に寄せ、両アプリが同じ入出力・表示部品を使えるようにする。

- `__init__.py`

	共通パッケージの識別用モジュール。公開関数は持たない。

- `colab_widgets.py`

	Colab の JavaScript と Python コールバックを接続する部品。ipywidgets の表示差異を回避するため、ドラッグ＆ドロップ領域を外部 JavaScript ライブラリなしで生成する。クリックできるエネルギーグラフは `energy_plot.py` が担当する（v0.2.1 で分離）。

	- `is_colab() -> bool`

		引数: なし。戻り値: Colab 実行時は `True`。目的: Colab 専用 UI の表示可否を判定する。

	- `register_callback(func, prefix: str = "qchem_cb") -> str | None`

		引数: JavaScript から呼ばれる関数、登録名接頭辞。戻り値: Colab では一意なコールバック名、それ以外は `None`。目的: `google.colab.output.register_callback` を安全に隠蔽する。呼出先: `common.gui_parts.StructureFileInput`, `common.gui_parts.EnergyStructureViewer`。

	- `parse_dropped_payload(payload: dict, allowed_extensions = ALLOWED_STRUCTURE_EXTENSIONS, max_bytes: int = MAX_DROPPED_FILE_BYTES) -> tuple[str, bytes]`

		引数: ファイル名と Base64 本文を含むブラウザ通知、許可拡張子、最大サイズ。戻り値: 正規化済みファイル名とバイト列。目的: ドロップ入力の拡張子・サイズ・Base64 を検証する。技術選定: ブラウザからの入力を直接ファイルとして扱わず、上限を設けて安全にする。呼出先: `common.gui_parts.StructureFileInput._on_file_dropped`。

	- `build_drop_zone_html(callback_name: str, uid: str | None = None, extensions = ALLOWED_STRUCTURE_EXTENSIONS, max_bytes: int = MAX_DROPPED_FILE_BYTES) -> str`

		引数: 登録済みコールバック名、DOM 識別子、許可拡張子、最大サイズ。戻り値: JavaScript を含むドロップ領域 HTML。目的: ドロップとクリック選択の両方を受け付ける Colab UI を作る。呼出先: `common.gui_parts.StructureFileInput`。

	- `check_safe_id(value: str, label: str) -> str`

		引数: DOM 識別子・コールバック名と表示名。戻り値: 検証済みの識別子。目的: JavaScript に埋め込む識別子を英数字とアンダースコアに限定し、注入を防ぐ。呼出元: `build_drop_zone_html`, `common.energy_plot.build_energy_plot_html`。

- `config.py`

	`config/` 配下の YAML 設定を読み込む共通関数。PySCF 版・UMA 版が同じ関数を使う（v0.2.1 で、2 つの `__init__.py` に重複していた定義を統一した）。

	- `PROJECT_ROOT` / `CONFIG_DIR`

		目的: リポジトリのルートと `config/` の場所を `pathlib.Path` で保持する。

	- `load_yaml(filename: str) -> dict | list`

		引数: `config/` 内の YAML ファイル名。戻り値: パース結果。目的: 設定読込みを一元化し、ファイルが無いときは配置を確認する日本語メッセージの `FileNotFoundError` にする。呼出元: `pyscf_backend.load_yaml`, `uma_backend.load_yaml`（別名）。

- `energy_plot.py`

	クリックできるエネルギー収束グラフ（SVG）と、そのための数値処理。外部 JavaScript ライブラリに頼らず、素の SVG と Colab の `google.colab.kernel.invokeFunction` だけで点のクリックを Python 側へ伝える（v0.2.1 で `colab_widgets.py` から分離した）。

	- `HARTREE_TO_KCAL_MOL`

		目的: エネルギーの単位換算（1 Hartree = 627.5094740631 kcal/mol）を 1 か所で定義する。呼出元: `relative_energies_kcal`, `common.gui_parts.EnergyStructureViewer`, `uma_backend.uma_report`。

	- `relative_energies_kcal(energies_hartree) -> list[float]`

		引数: 各最適化点の全エネルギー[Hartree]。戻り値: 最終点をゼロとする相対エネルギー[kcal/mol]。目的: グラフと構造表示で同じエネルギー基準を使う。呼出元: `build_energy_plot_html`, `common.gui_parts.default_step_label`。

	- `nice_ticks(vmin: float, vmax: float, target: int = 5, integer_only: bool = False) -> tuple[list[float], float]`

		引数: 値域、目標目盛り数、整数目盛り限定フラグ。戻り値: 目盛り値と刻み。目的: SVG グラフの読みやすい軸目盛りを作る。呼出元: `build_energy_plot_html`。

	- `build_energy_plot_html(energies_hartree, selected_index: int | None = None, callback_name: str | None = None, uid: str | None = None, width: int = 640, height: int = 360) -> str`

		引数: エネルギー履歴、選択点、任意のクリックコールバック、DOM 識別子、描画サイズ。戻り値: SVG と任意のクリック JavaScript を含む HTML。目的: 点選択で対応構造を示すエネルギー収束グラフを描く。技術選定: Colab で FigureWidget が空表示になる事例を避け、素の SVG を採用する。呼出先: `relative_energies_kcal`, `nice_ticks`, `_format_tick`, `common.colab_widgets.check_safe_id`; 呼出元: `common.gui_parts.EnergyStructureViewer._draw_energy_plot`。

	- `_nice_step(raw_step: float) -> float` / `_format_tick(value: float, step: float) -> str`

		引数: 目盛り候補、目盛り値と刻み。戻り値: きりの良い刻み、整形済み文字列。目的: SVG 軸の表示を安定させる内部補助関数。呼出元: `nice_ticks`, `build_energy_plot_html`。

- `gui_input.py`

	ipywidgets 本体に依存しない、GUI の「入力」まわりの関数。アップロードされたファイルの取り出し、構造の読込みと検証、電荷の表示と読取り（v0.2.1 で `gui_helpers.py` を入力と出力に分けた）。

	- `extract_uploaded_file(upload_widget, dropped_file: dict | None = None) -> tuple[bytes, str]`

		引数: FileUpload 相当の値、任意のドロップ済みファイル。戻り値: 内容とファイル名。目的: ipywidgets 7/8 の異なる値形式を吸収し、ドロップ入力を優先する。呼出先: `common.gui_parts.StructureFileInput.read`。

	- `read_uploaded_structure(content: bytes, filename: str) -> Structure`

		引数: 構造ファイルの中身、ファイル名。戻り値: 読み込んだ構造。目的: 拡張子つきの一時ファイルへ書き出して読み込み、一時ファイルを削除する。原子間距離や電荷・多重度の検証はしない（受け取った構造の自動表示に使う）。呼出先: `common.io_reader.read_structure`; 呼出元: `load_uploaded_structure`, `common.gui_parts.StructureFileInput._update_preview`。

	- `describe_structure(structure: Structure, filename: str) -> str`

		引数: 構造、ファイル名。戻り値: 「ファイル: …  原子数: …  組成: …」の 1 行。目的: 計算前のログと、受け取った構造の表示で、同じ概要文を使う。呼出元: `load_uploaded_structure`, `common.gui_parts.StructureFileInput._update_preview`。

	- `load_uploaded_structure(content: bytes, filename: str, charge: int, multiplicity: int, min_distance: float, log = print) -> Structure`

		引数: 構造ファイルの中身、ファイル名、電荷、スピン多重度、原子間距離の下限[Å]、ログ出力関数。戻り値: 検証済みの共通構造。目的: 構造の読込み（`read_uploaded_structure`）、概要のログ出力（`describe_structure`）、原子間距離の検証、電荷・多重度の検証を、PySCF 版・UMA 版で同じ手順にする。エンジンごとに異なる確認（遷移金属の判定など）は呼出元で行う。呼出先: `read_uploaded_structure`, `describe_structure`, `common.io_reader.validate_structure`, `validate_charge_and_multiplicity`; 呼出元: `gui.build_app`, `gui_uma.build_app`。

	- `ChargeInputError(ValueError)`

		目的: GUI の電荷文字列が整数として読めないことを示す例外。メッセージはそのまま画面に表示できる。

	- `format_charge(value: int) -> str` / `parse_charge(text: str) -> int`

		引数: 整数／利用者入力文字列。戻り値: 表示用符号付き文字列（正の値だけ `+1` の形）／正規化した整数。目的: `+1`、全角数字、Unicode 符号を含む電荷入力を安全に扱う。呼出先: `common.gui_parts.ChargeInput`。

- `gui_output.py`

	ipywidgets 本体に依存しない、GUI の「出力」（ダウンロード）まわりの関数。ファイル名の整形と既定名、最終構造・トラジェクトリのダウンロード項目（v0.2.1 で `gui_helpers.py` から分けた）。

	- `sanitize_filename_stem(raw: str) -> str`

		引数: 任意のファイル名幹。戻り値: 禁止文字を除いた名前、空なら `result`。目的: ダウンロード名を安全にする。呼出先: `common.gui_parts.DownloadPanel.show`。

	- `default_download_stem(input_filename: str) -> str`

		引数: 入力ファイル名。戻り値: `<入力名>_result` 形式の既定名。目的: 出力ファイル群の名前を入力に対応付ける。PySCF 版・UMA 版の両方で同じ既定名（`<入力名>_result`）を使う。呼出先: `gui.build_app`, `gui_uma.build_app`。

	- `xyz_download_items(final_xyz_path: str, trajectory_path: str) -> list[tuple[str, str, str, str]]`

		引数: 最終構造・トラジェクトリのパス。戻り値: `DownloadPanel.show` に渡す項目（説明、パス、ダウンロード名の末尾、ボタン名）2 件。目的: 両 GUI で共通の 2 つのダウンロード項目を 1 か所で定義する。エンジンごとの項目（molden・計算ログ）は呼出元が足す。呼出元: `gui.build_app`, `gui_uma.build_app`。

- `gui_parts.py`

	PySCF 版と UMA 版で共有する ipywidgets の複合部品。

	- `dropdown_from_list(items: list[dict], description: str, width: str = "420px") -> ipywidgets.Dropdown`

		引数: `label`/`key` を持つ設定項目、表示名、幅。戻り値: ドロップダウン。目的: YAML の選択肢を画面へ変換する。呼出先: `gui.build_app`, `gui_uma.build_app`。

	- `StructureFileInput(callback_prefix: str = "qchem_drop")`

		引数: Colab コールバック名接頭辞。戻り値: `widgets` 属性でドロップ領域と FileUpload を公開する入力部品。目的: ドラッグ＆ドロップと通常のファイル選択を統一する。技術選定: Colab では `common.colab_widgets`、それ以外では標準 FileUpload をフォールバックにする。呼出先: `common.colab_widgets.is_colab`, `common.colab_widgets.register_callback`, `common.colab_widgets.build_drop_zone_html`, `common.colab_widgets.parse_dropped_payload`, `common.gui_input.extract_uploaded_file`。

		- `read() -> tuple[bytes, str]`

			戻り値: 最後に選択された構造ファイルの内容と名前。目的: 計算パイプラインに入力を渡す。呼出先: `gui.build_app`, `gui_uma.build_app`。

		- `_on_file_dropped(payload: dict) -> None` / `_on_upload_changed(change: dict) -> None`

			引数: Colab JavaScript のペイロード／ipywidgets の値変更通知。戻り値: なし。目的: 最新の入力を記録し、前の入力を無効化して入力方法間の優先順位を保つ。呼出先: `common.colab_widgets.parse_dropped_payload`。 ファイルを受け取ると（ドロップ・ボタンのどちらでも）、その構造を、`preview_output`（`widgets` の最後）に自動で表示する（原子数・組成の概要と 3D 表示。読み込めないときは理由を表示し、ファイルの受取り自体は妨げない）。呼出先（表示）: `_update_preview` → `common.gui_input.read_uploaded_structure`, `describe_structure`, `common.plot_common.render_single_structure`。

	- `default_step_label(step_index: int, relative_energy_kcal: float, result) -> str`

		引数: ステップ番号、相対エネルギー、最適化結果。戻り値: 構造表示の説明文。目的: 共通の標準ラベルを作る。呼出先: `EnergyStructureViewer`。

	- `EnergyStructureViewer(callback_prefix: str = "qchem_plot", step_label = None)`

		引数: Colab コールバック接頭辞、任意の構造表示ラベル生成関数。戻り値: `widget` 属性でグラフ、スライダー、3D 表示を公開する部品。目的: エネルギー点、スライダー、対応構造を同期する。技術選定: SVG のクリック連携とスライダーの双方を提供し、通信失敗時も構造選択を可能にする。呼出先: `common.colab_widgets.register_callback`, `common.energy_plot.build_energy_plot_html`, `common.energy_plot.relative_energies_kcal`, `common.plot_common.render_single_structure`。

		- `show(result) -> None`

			引数: `energies` と `coords_history` を持つ最適化結果。戻り値: なし。目的: 対応するエネルギー・座標だけを UI に反映する。呼出先: `gui.build_app`, `gui_uma.build_app`。

		- `_show_structure_at_step(step_index: int) -> None` / `_draw_energy_plot(selected_index: int) -> None` / `_on_slider_changed(change: dict) -> None` / `_on_plot_clicked(index: int) -> None`

			引数: 選択ステップ、描画対象ステップ、ウィジェット変更通知、SVG クリック位置。戻り値: なし。目的: 3D 構造、赤い選択マーカー、スライダーを相互に同期する内部イベント処理。呼出先: `common.plot_common.render_single_structure`, `common.energy_plot.build_energy_plot_html`。 `reset()` は、前回の結果（グラフ・構造・スライダー・保持している結果）を消す。新しい計算を始めるときに呼ぶ。

	- `VibrationViewer()`

		引数: なし。戻り値: `widget` 属性でモード選択と表示ボタンを公開する部品。目的: 振動数解析結果に基づく振動アニメーションを表示する。呼出先: `common.plot_common.render_vibration`。

		- `setup(freq_result, symbols, coords) -> None`

			引数: 振動数結果、元素記号、最終座標。戻り値: なし。目的: 計算の有無とモードに応じて操作部を有効化する。呼出先: `gui.build_app`, `gui_uma.build_app`。

		- `_on_button_clicked(_) -> None`

			引数: ボタンクリック通知。戻り値: なし。目的: 選択されたモードを 3D ビューへ描画する内部イベント処理。呼出先: `common.plot_common.render_vibration`。 `setup()` は、呼ばれるたびに前回のアニメーションの表示を消す（振動数計算をしない実行でも、前回のものを残さない）。`reset()` は `setup(None, None, None)` と同じ。

	- `DownloadPanel(tmp_prefix: str = "qchem_dl_", description_width: str = "280px")`

		引数: 一時保存先接頭辞、説明欄の幅。戻り値: `widget` 属性でダウンロード欄を公開する部品。目的: Colab では任意名でダウンロードし、ローカルでは出力パスを表示する。呼出先: `common.gui_output.sanitize_filename_stem`。

		- `show(items, default_stem: str = "") -> None`

			引数: 説明・パス・接尾辞・表示名の出力定義、既定ファイル名幹。戻り値: なし。目的: 現在の計算結果に対応するダウンロード UI を再構成する。呼出先: `gui.build_app`, `gui_uma.build_app`。

			内部で `_make_handler(src_path, suffix)` と `_handler(_)` を生成し、Colab の `files.download` 呼出しを各ボタンへ束縛する。目的は各出力に同じ安全なファイル名規則を適用すること。 `reset()` は、前回のダウンロードボタンを消す。

	- `ChargeInput(value: int = 0, description: str = "電荷")`

		引数: 初期電荷、表示名。戻り値: `controls`（入力欄と −1/+1 ボタンの HBox）、`message`（エラー表示欄）、`value`（現在の電荷の整数）を公開する部品。目的: 電荷を `+1` の形で表示するテキスト入力欄を PySCF 版・UMA 版で共通にする。Enter／欄外クリックで値を整え、読み取れない入力は直前の値へ戻してメッセージを出す。技術選定: 数値ウィジェット（IntText）では正の値に `+` を付けて表示できないため、Text と関数（`common.gui_input.format_charge`, `parse_charge`）を組み合わせる。呼出先: `common.gui_input.format_charge`, `parse_charge`; 呼出元: `gui.build_app`, `gui_uma.build_app`。

	- `MultiplicityInput(value: int = 1, description: str = "スピン多重度")`

		引数: 初期スピン多重度、表示名。戻り値: `widget`（整数の入力欄 IntText）と `value`（現在の多重度の整数）を公開する部品。目的: 電荷の入力欄と同じ幅・説明欄の幅にそろえ、PySCF 版・UMA 版で同じ見た目にする。値の範囲や電子数との整合は、この部品ではなく計算前の検証（`common.gui_input.load_uploaded_structure`）で確認する。呼出元: `gui.build_app`, `gui_uma.build_app`。

- `io_reader.py`

	構造ファイルの読込みと、計算前の元素・座標・電荷・スピン検証を担当する。

	- `StructureError(ValueError)`

		目的: 利用者に表示可能な構造入力エラーを表す例外。

	- `Structure(symbols: list[str], coords: list[list[float]], comment: str = "")`

		目的: 元素記号、Å 単位座標、注釈を保持するデータクラス。PySCF/UMA 共通入力形式。

	- `read_xyz(filepath: str) -> Structure`

		引数: XYZ ファイルパス。戻り値: `Structure`。目的: 外部ライブラリなしで標準 XYZ を読む。技術選定: 最小形式を自前実装し、基本入力の依存関係を減らす。

	- `read_structure(filepath: str) -> Structure`

		引数: 入力ファイルパス。戻り値: `Structure`。目的: `.xyz` は `read_xyz`、`.com`/`.gjf`/`.pdb` は ASE に振り分ける。呼出先: `common.io_reader.read_xyz`, `common.io_reader._read_with_ase`; 呼出元: `gui.build_app`, `gui_uma.build_app`。

	- `validate_structure(structure: Structure, min_distance: float = 0.4) -> None`

		引数: 構造、原子間最小距離[Å]。戻り値: 正常時はなし、異常時は `StructureError`。目的: 空構造、配列不整合、原子重なりを検出する。呼出元: `gui.build_app`, `gui_uma.build_app`。

	- `validate_charge_and_multiplicity(structure: Structure, charge: int, multiplicity: int) -> None`

		引数: 構造、総電荷、スピン多重度。戻り値: 正常時はなし、矛盾時は `StructureError`。目的: 電子数・多重度の化学的整合性を確認する。呼出元: `gui.build_app`, `gui_uma.build_app`。

- `plot_common.py`

	py3Dmol による、計算エンジン非依存の可視化部品。エネルギー収束グラフは `common.energy_plot.build_energy_plot_html` が自前の SVG で描く（Plotly 版は v0.2.1 で削除）。

	- `render_single_structure(symbols, coords, width: int = 500, height: int = 400) -> py3Dmol.view`

		引数: 元素記号、Å 座標、表示サイズ。戻り値: 1 構造の 3D ビュー。目的: 選択した最適化ステップを表示する。呼出元: `common.gui_parts.EnergyStructureViewer`。

	- `render_vibration(symbols, final_coords, frequencies_cm1, normal_modes, mode_index: int = 0, amplitude: float = 0.6, n_frames: int = 20, width: int = 500, height: int = 400) -> tuple[py3Dmol.view, str]`

		引数: 最終構造、振動数、正規モード、表示モード、振幅、フレーム数、サイズ。戻り値: 3D ビューと説明文。目的: 選択モードの変位をループ表示する。呼出先: `common.writer_xyz.multiframe_xyz_string`; 呼出元: `common.gui_parts.VibrationViewer`。

- `version.py`

	リポジトリ全体のリリース番号 `__version__`（Git タグと同じ値）を 1 か所だけで定義する。`pyscf_backend.__version__`・`uma_backend.__version__` は、この値の別名。更新手順は「リリース時のバージョン番号更新」を参照する。

- `writer_xyz.py`

	XYZ 形式の単一構造・複数構造を文字列またはファイルとして出力する。

	- `FINAL_STRUCTURE_FILENAME` / `TRAJECTORY_FILENAME`

		目的: 最適化の出力ファイル名（`final_structure_for_ColabReaction.xyz`、`optimization_trajectory.xyz`）を PySCF 版・UMA 版で共通にする。

	- `write_optimization_outputs(out_dir: str, final_symbols, final_coords, final_comment: str, opt_result) -> tuple[str, str]`

		引数: 出力先フォルダ、最終構造の元素・座標・コメント、`symbols`・`coords_history`・`energies` を持つ最適化結果。戻り値: 最終構造とトラジェクトリのパス。目的: 構造最適化の標準の出力 2 ファイルを同じ名前・形式で書き出す（v0.2.1 で両 GUI の重複を統一した）。呼出先: `write_final_structure`, `write_trajectory`; 呼出元: `gui.build_app`, `gui_uma.build_app`。

	- `write_final_structure(symbols, coords, filepath: str, comment: str = "Optimized structure") -> None`

		引数: 元素、座標、出力先、コメント。戻り値: なし。目的: 最終構造 XYZ を保存する。呼出先: `common.writer_xyz.xyz_string`; 呼出元: `write_optimization_outputs`。

	- `write_trajectory(symbols, coords_history, filepath: str, energies = None) -> None`

		引数: 元素、座標履歴、出力先、任意のエネルギー。戻り値: なし。目的: 最適化履歴を多フレーム XYZ として保存する。呼出先: `common.writer_xyz.multiframe_xyz_string`; 呼出元: `write_optimization_outputs`。

	- `xyz_string(symbols, coords, comment: str = "") -> str` / `multiframe_xyz_string(symbols, coords_list, comments = None) -> str`

		引数: 単一／複数の元素・座標と任意コメント。戻り値: XYZ 文字列。目的: ファイル出力と py3Dmol 入力を共有する。呼出先: `_format_xyz_block`。

### pyscf_backend

PySCF を計算エンジンとする ab initio 計算パッケージ。`common` を入力・可視化の共通基盤として利用する。

- `__init__.py`

	`common.config` の `PROJECT_ROOT`・`CONFIG_DIR`・`load_yaml` と `common.version.__version__` を、このパッケージの名前でも使えるようにした別名。独自の関数は持たない。呼出元: `gui.build_app`, `pyscf_backend.engine._load_functional`, `pyscf_backend.engine._load_basis`。

- `engine.py`

	PySCF の Mole と SCF を構築・実行し、GPU4PySCF が使えなければ CPU へ戻す。

	- `SCFConvergenceError(RuntimeError)`

		目的: 再試行後にも SCF が収束しない場合の利用者向け例外。

	- `build_mole(structure: common.io_reader.Structure, charge: int, multiplicity: int, basis_key: str, verbose: int = 0) -> pyscf.gto.Mole`

		引数: 共通構造、電荷、多重度、基底関数キー、PySCF 詳細度。戻り値: 構築済み Mole。目的: YAML の基底関数・ECP を計算入力へ変換する。技術選定: `cart=True` により 6D/10F の Molden 互換出力を優先する。呼出先: `pyscf_backend.engine._load_basis`; 呼出元: `gui.build_app`。

	- `TRANSITION_METAL_SYMBOLS` / `contains_transition_metal(structure: Structure) -> bool`

		引数: 構造。戻り値: PySCF 版が未対応の遷移金属元素（3d・4d・5d の一部）を含むか。目的: 計算を始める前に、ECP 付き基底が未登録の元素を案内する。扱える元素の範囲はエンジンごとに決まるため、v0.2.1 で `common/io_reader.py` から移した。呼出元: `gui.build_app`。

	- `gpu_runtime_detected() -> bool`

		引数: なし。戻り値: GPU ランタイムが割り当てられていれば `True`。目的: Colab の実行環境で GPU4PySCF を試す可否を `nvidia-smi` の成否で判定する（v0.2.1 で `gui.py` から移した）。`nvidia-smi` が無い・失敗・タイムアウトのときは `False`。呼出元: `gui.build_app`。

	- `_load_functional(functional_key: str) -> dict` / `_load_basis(basis_key: str) -> dict` / `_try_import_gpu4pyscf() -> module | None`

		引数: YAML の手法／基底関数キー、またはなし。戻り値: 対応する設定辞書、または GPU4PySCF モジュール・`None`。目的: YAML 検索と GPU の任意依存を分離する内部補助関数。呼出先: `pyscf_backend.load_yaml`; 呼出元: `build_mole`, `build_scf`。

	- `build_scf(mol, functional_key: str, try_gpu: bool = True) -> tuple[object, bool, str]`

		引数: Mole、手法キー、GPU 試行フラグ。戻り値: SCF オブジェクト、GPU 使用有無、表示用メッセージ。目的: HF/DFT と閉殻/開殻を選び SCF を初期化する。技術選定: GPU 初期化失敗は計算を中断せず CPU にフォールバックする。呼出先: `_load_functional`, `_try_import_gpu4pyscf`; 呼出元: `gui.build_app`, `pyscf_backend.optimize.run_geometry_optimization`。

	- `run_scf(mf, defaults: dict, dm0 = None) -> object`

		引数: SCF オブジェクト、収束設定、任意の初期密度行列。戻り値: 収束済み SCF オブジェクト。目的: 既定条件で SCF を実行し、失敗時は緩和条件とレベルシフトで一度再試行する。呼出元: `gui.build_app`。

- `optimize.py`

	- `OptimizationResult`

		目的: 最終 Mole、GPU 情報、エネルギー・座標履歴、収束状態、所要時間、再計算用密度行列を保持する結果コンテナ。

	- `run_geometry_optimization(mol, functional_key: str, defaults: dict, try_gpu: bool = True) -> OptimizationResult`

		引数: 初期 Mole、手法キー、設定、GPU 試行フラグ。戻り値: 最適化結果。目的: geomeTRIC による構造最適化と履歴記録を行う。技術選定: 内部座標を使う geomeTRIC を採用し、有機分子の収束性を優先する。呼出先: `pyscf_backend.engine.build_scf`; 呼出元: `gui.build_app`。

	- `_to_numpy(arr) -> numpy.ndarray` / `_make_callback(result: OptimizationResult) -> callable`

		引数: NumPy/CuPy 配列、または結果コンテナ。戻り値: CPU 配列、または geomeTRIC コールバック。目的: GPU 配列の互換変換と、各最適化点のエネルギー・座標記録を行う内部補助関数。呼出元: `run_geometry_optimization`。

- `freq.py`

	- `FrequencyResult`

		目的: 振動数、正規モード、虚振動数、熱力学量、警告、所要時間を保持する結果コンテナ。

	- `run_frequency_analysis(mf, defaults: dict) -> FrequencyResult`

		引数: 収束済み CPU SCF、周波数設定。戻り値: 振動数解析結果。目的: Hessian、調和振動数、ZPE と自由エネルギーを計算する。技術選定: GPU Hessian は十分に検証されていないため CPU PySCF を用いる。呼出元: `gui.build_app`。

	- `_get(d: dict, *keys: str, default = None) -> object`

		引数: PySCF の結果辞書、候補キー、既定値。戻り値: 最初に見つかった値または既定値。目的: PySCF の版により変わる結果キーを吸収する内部補助関数。呼出元: `run_frequency_analysis`。

- `analysis_pyscf.py`

	収束済みの PySCF の SCF オブジェクトから、軌道と電荷の情報を取り出す。描画にもウィジェットにも依存しない（描画は `visualizer_pyscf.py`）。

	- `DEGENERACY_TOLERANCE_HARTREE` / `HARTREE_TO_EV` / `OrbitalChoices(options, default_index, open_shell)`

		目的: 軌道エネルギーが縮退しているとみなす差（既定 1e-4 Hartree）、Hartree から eV への換算係数、軌道の選択肢の戻り値（表示名と軌道番号の組のリスト、最初に選ぶ軌道番号、開殻かどうか）を定義する。

	- `valence_space_size(mol) -> tuple[int, int]`

		引数: Mole。戻り値: 分子全体の（内殻軌道の数, 価電子殻の軌道の数）。目的: 「各原子の最外殻だけからできる軌道」の数を、原子ごとの値の合計で数える（H・He は 1s の 1 軌道、そのほかは最外殻の s と p の 4 軌道。Ga〜Kr・In〜Xe の (n-1)d 軌道は内殻とみなす）。呼出先: `_atom_symbols`, `_core_and_valence_orbital_counts`; 呼出元: `orbital_choices`。

	- `orbital_choices(mol, mf, degeneracy_tolerance: float = DEGENERACY_TOLERANCE_HARTREE) -> OrbitalChoices`

		引数: Mole、収束済み SCF オブジェクト、縮退とみなすエネルギー差。戻り値: ドロップダウン用の選択肢、既定の軌道番号、開殻かどうか。目的: 軌道 0 番から「内殻軌道数＋価電子殻の軌道数」番目まで（電子が入っているすべての軌道を含む）を一覧にし、表示名を「軌道n番」とする。閉殻は HOMO・LUMO に「(HOMO)」「(LUMO)」を付け（縮退する軌道すべてに付ける）、開殻は電子が 1 個だけ入っている軌道に「(SOMO)」を付ける。表示名の末尾に軌道エネルギーを eV で併記し（例: 「軌道4番(HOMO)  -13.61 eV」。開殻は α 軌道のエネルギー）、選択肢はエネルギーの低い軌道ほど下に並べる（軌道番号の大きい順）。既定は、電子が入っている（α スピンの）軌道のうち最も高いもの。技術選定: 開殻（UHF/UKS）の `mo_occ`・`mo_energy` は 2 行の配列で保持されるため、α スピンの軌道を基準にする。最外殻の空軌道は軌道の数で近似する。呼出先: `_occupations`, `valence_space_size`; 呼出元: `gui.build_app`。

	- `_core_and_valence_orbital_counts(symbol: str) -> tuple[int, int]` / `_atom_symbols(mol) -> list[str]` / `_occupations(mf) -> tuple[numpy.ndarray, numpy.ndarray, numpy.ndarray]`

		引数: 元素記号、Mole、SCF オブジェクト。戻り値: 1 原子の内殻・価電子殻の軌道数、元素記号のリスト、軌道ごとの総電子数・α 電子数・α 軌道エネルギー。目的: 軌道の数え上げと、閉殻・開殻（ROHF を含む）の配列形状の違いを吸収する内部補助関数。呼出元: `valence_space_size`, `orbital_choices`。

	- `compute_mulliken_charges(mol, mf) -> list[tuple[str, float]]`

		引数: Mole、SCF。戻り値: 元素記号と Mulliken 電荷。目的: 原子電荷表と色分け表示の基礎データを得る（v0.2.1 で `visualizer_pyscf.py` から移した）。呼出元: `gui.build_app`。

- `pipeline.py`

	PySCF 版の計算の流れ。検証済みの構造 → 遷移金属の確認 → 構造最適化（GPU4PySCF・CPU を自動で切替）→ 最終構造での CPU 上の SCF 再計算 → 任意の振動数解析 → 出力ファイル（xyz・molden）の書出し。画面（ipywidgets）にも、アップロードされたファイルの扱いにも依存せず、進捗は `log` 関数（既定は `print`）で受け渡す。例外は捕まえずに送出し、利用者向けの文面への変換は GUI が行う（v0.2.1 で `gui.py` から分離した）。

	- `CalculationSettings(charge: int, multiplicity: int, functional_key: str, basis_key: str, do_frequency: bool = True, try_gpu: bool | None = None)`

		目的: 利用者が指定する計算条件を保持する。`try_gpu` が `None` のときは、GPU ランタイムかどうかを自動で判定する。

	- `CalculationResult(structure, opt_result, final_mol, mf_final, freq_result, final_symbols, final_coords, out_dir, final_xyz_path, traj_xyz_path, molden_path, total_seconds)`

		目的: 計算結果（最適化結果、最終構造の Mole、CPU で収束させた SCF、振動数結果）と、書き出したファイルの場所を保持する。画面表示・ダウンロードにそのまま使う。

	- `run_calculation(structure, settings: CalculationSettings, defaults: dict, log = print) -> CalculationResult`

		引数: 読込みと入力検証が済んだ構造、計算条件、`config/defaults.yaml` の辞書、ログ出力関数。戻り値: 計算結果。目的: 上記の流れを最初から最後まで実行し、進捗・注意・所要時間を `log` へ出す。例外: 遷移金属を含む構造は `io_reader.StructureError`、SCF 不収束は `engine.SCFConvergenceError`、構造最適化の不収束は `RuntimeError`。技術選定: 計算の流れを画面から分け、PySCF や Colab なしで、段階の呼出し順序と受渡しを単体テストできるようにする。呼出先: `pyscf_backend.engine.gpu_runtime_detected`, `contains_transition_metal`, `build_mole`, `build_scf`, `run_scf`, `pyscf_backend.optimize.run_geometry_optimization`, `pyscf_backend.freq.run_frequency_analysis`, `common.writer_xyz.write_optimization_outputs`, `pyscf_backend.writer_molden.write_molden`; 呼出元: `gui.build_app`。

- `visualizer_pyscf.py`

	PySCF の Mole/SCF に依存する軌道・Mulliken 電荷の可視化（3D 描画と HTML 表）。軌道番号や電荷の値を求める解析は `analysis_pyscf.py` が担当する。

	- `render_orbital(mol, mf, orbital_index: int, isoval_fraction: float = 0.12, width: int = 500, height: int = 400) -> py3Dmol.view`

		引数: Mole、SCF、軌道番号、等値面比率、サイズ。戻り値: 軌道の正負等値面を含む 3D ビュー。目的: MO を可視化する。技術選定: PySCF cube 出力を py3Dmol へ渡す。呼出先: `_mo_coeff_for_cube`, `_max_abs_from_cube_file`; 呼出元: `gui.build_app`。

	- `atomic_charges_table_html(charges) -> str` / `render_charges(mol, charges, show_labels: bool = True, width: int = 500, height: int = 400) -> py3Dmol.view`

		引数: 電荷、後者はラベル表示とサイズ。戻り値: HTML 表／電荷を色分けした 3D ビュー。目的: Mulliken 電荷を数値と分子上の色で示す。呼出先: `add_atom_charge_labels`, `add_atom_charge_spheres`; 呼出元: `gui.build_app`。

	- `_mo_coeff_for_cube(mf, orbital_index: int) -> numpy.ndarray` / `_max_abs_from_cube_file(cube_path: str) -> float` / `_charge_gradient_color(charge: float, max_abs_charge: float) -> str`

		引数: SCF と軌道番号、cube パス、電荷と最大絶対電荷。戻り値: cube 出力用係数、最大絶対値、CSS 色。目的: 軌道等値面のスケールと電荷グラデーションを決める内部補助関数。呼出元: `render_orbital`, `add_atom_charge_spheres`。 `_mo_coeff_for_cube` は、開殻（UHF/UKS）で 3 次元（またはα・βの組）になる軌道係数から、α スピンの軌道を取り出す。
	- `add_atom_charge_labels(view, mol, charges, font_size: int = 12) -> None` / `add_atom_charge_spheres(view, mol, charges, opacity: float = 0.85, size_variation: float = 0.2) -> None`

		引数: py3Dmol ビュー、Mole、電荷、および描画パラメータ。戻り値: なし。目的: 既存ビューへ数値ラベルまたは電荷色の球を追加する。呼出先: `_charge_gradient_color`; 呼出元: `render_charges`。

- `writer_molden.py`

	- `write_molden(mf, filepath: str) -> None`

		引数: 収束済み CPU SCF、出力先。戻り値: なし。目的: 構造と分子軌道を Molden ファイルへ保存する。技術選定: PySCF の版差を吸収するため高水準 API を順に試し、最後に低水準 API へフォールバックする。呼出元: `gui.build_app`。

### uma_backend

FAIR-Chem/UMA を計算エンジンとする機械学習ポテンシャル用パッケージ。PySCF の電子状態機能には依存せず、ASE の Atoms・最適化器を利用する。

- `README.md`

	UMA の利用条件、Hugging Face のアクセス、実行上の注意を補足する文書。

- `__init__.py`

	`common.config` の `PROJECT_ROOT`・`CONFIG_DIR`・`load_yaml` と `common.version.__version__` を、このパッケージの名前でも使えるようにした別名（`pyscf_backend` には依存しない）。独自の関数は持たない。呼出元: `gui_uma.build_app`。

- `uma_engine.py`

	UMA（fairchem-core）で計算するための土台。計算デバイスの判定、学習済みモデルの読込み、ASE の Atoms・Calculator の構築を行う。Hugging Face の認証は `uma_hf.py` に分けた（v0.2.1）。

	- `get_device() -> str` / `describe_device(device: str) -> str`

		引数: 後者はデバイス名。戻り値: `cuda`/`cpu` と表示用説明。目的: 推論デバイスを選び利用者へ性能上の注意を示す。呼出元: `gui_uma.build_app`。

	- `load_predictor(model_name: str, device: str) -> object`

		引数: FAIR-Chem モデル名、デバイス。戻り値: 読込み済み予測器。目的: UMA 学習済みモデルを取得・初期化する。技術選定: `fairchem.core.pretrained_mlip` の公開 API を使う。ゲート付きモデルの拒否は `uma_hf.explain_hf_error` で利用者向けの文面にし、`uma_hf.UmaSetupError` として送出する（再エクスポートはしない）。呼出先: `uma_backend.uma_hf.UmaSetupError`, `uma_backend.uma_hf.explain_hf_error`; 呼出元: `gui_uma.build_app`。

	- `clear_predictor_cache() -> None`, `make_calculator(predictor, task_name: str = "omol") -> object`, `build_atoms(structure, charge: int, multiplicity: int) -> ase.Atoms`

		引数: 予測器・タスク名、または共通構造・電荷・多重度。戻り値: キャッシュ削除はなし、後者は FAIR-Chem Calculator／ASE Atoms。目的: UMA 計算器とその入力を組み立てる。呼出元: `gui_uma.build_app`。

- `uma_optimize.py`

	- `OptimizationResult`

		目的: UMA 最適化の元素、座標・エネルギー・最大力履歴、最終 Atoms、収束状態、所要時間を保持するコンテナ。`final_fmax` プロパティは最終最大力[eV/Å]を返す。

	- `run_geometry_optimization(atoms: ase.Atoms, calculator, opt_cfg: dict, progress = None) -> OptimizationResult`

		引数: 初期 Atoms、計算器、最適化設定、任意の進捗コールバック。戻り値: 最適化結果。目的: LBFGS/BFGS/FIRE の設定された ASE 最適化を実行し、GUI 用の履歴を記録する。技術選定: ASE 最適化器を用いて UMA Calculator と直結する。呼出元: `gui_uma.build_app`。

- `uma_freq.py`

	- `compute_hessian_fd(forces_fn, positions, delta: float = 0.01, progress = None) -> numpy.ndarray`

		引数: 座標から力を返す関数、平衡座標、変位幅[Å]、任意の進捗コールバック。戻り値: Hessian。目的: 力の有限差分から振動数解析の入力を作る。技術選定: UMA は解析 Hessian を返さないため数値微分を用いる。呼出元: `run_frequency_analysis`。

	- `harmonic_analysis(masses, positions, hessian, rank_tol: float = 1e-8) -> tuple[list[float], numpy.ndarray]`

		引数: 原子質量、座標、Hessian、ランク判定閾値。戻り値: 振動数[cm⁻¹]と正規モード。目的: 並進・回転を除いた振動モードを得る。呼出元: `run_frequency_analysis`。

	- `FrequencyResult`

		目的: 振動数、正規モード、虚振動数、警告、所要時間を保持するコンテナ。

	- `run_frequency_analysis(atoms, calculator, freq_cfg: dict, progress = None) -> FrequencyResult`

		引数: 最終 Atoms、UMA 計算器、周波数設定、任意の進捗コールバック。戻り値: 振動数結果。目的: 有限差分 Hessian と調和解析を実行し、虚振動の注意を作る。呼出先: `compute_hessian_fd`, `harmonic_analysis`; 呼出元: `gui_uma.build_app`。

- `uma_hf.py`

	UMA の学習済みモデルを取得するための Hugging Face のトークン管理とアクセス権の確認（v0.2.1 で `uma_engine.py` から分けた）。トークンは環境変数 `HF_TOKEN` だけを見る。

	- `MODEL_REPO_ID` / `HF_TOKEN_ENV` / `LICENSE_FILENAME`

		目的: UMA のリポジトリ名、トークンを受け渡す環境変数名、アクセス確認に取得する小さなファイル名を定義する。

	- `UmaSetupError(RuntimeError)`

		目的: Hugging Face 認証、アクセス権、ライブラリ未導入など、UMA を使うための準備の問題に関する利用者向け例外。`uma_engine.py` からは再エクスポートせず、利用側は `uma_hf.UmaSetupError` と書く。呼出元: `check_model_access`, `login_with_token`, `login_from_environment`, `uma_engine.load_predictor`, `gui_uma.build_app`, `ColabApp_UMA.ipynb`。

	- `login_with_token(token: str) -> None` / `login_from_environment() -> None` / `has_hf_token() -> bool`

		引数: 前者は Hugging Face トークン、他はなし。戻り値: ログイン処理はなし、存在確認は真偽値。目的: トークンをモジュール状態へ保持せず認証する。技術選定: 環境変数 `HF_TOKEN` を利用してノートブック保存時の秘匿性を保つ。呼出先: `login_from_environment` は `login_with_token`; 呼出元: `check_model_access`, `ColabApp_UMA.ipynb`。

	- `explain_hf_error(error: Exception) -> str`

		引数: Hugging Face 関連の例外。戻り値: 利用者向けの日本語メッセージ。目的: ゲート付きモデルへの未同意・認証エラー、接続エラー、その他を区別して案内する。呼出元: `check_model_access`, `uma_engine.load_predictor`。

	- `check_model_access() -> str`

		引数: なし。戻り値: 取得した LICENSE ファイルのパス。目的: UMA のゲート付きモデルへのアクセス権を、モデル本体を取得する前に確認する。呼出先: `has_hf_token`, `explain_hf_error`; 呼出元: `gui_uma.build_app`, `ColabApp_UMA.ipynb`。

- `uma_notice.py`

	- `notice_text() -> str`

		引数: なし。戻り値: UMA のモデルカード・論文・利用通知を含むテキスト。目的: 一次情報へのリンクと必要な引用を一箇所で管理する。呼出元: `ColabApp_UMA.ipynb`, `uma_backend.uma_report.build_log_text`。

- `uma_pipeline.py`

	UMA 版の計算の流れ。検証済みの構造 → Hugging Face のアクセス権の確認 → モデルの読込み（デバイスの判定）→ 構造最適化 → 任意の振動数解析 → 出力ファイル（xyz・計算ログ）の書出し。画面（ipywidgets）にも、アップロードされたファイルの扱いにも依存せず、進捗は `log` 関数（既定は `print`）で受け渡す。例外は捕まえずに送出し、利用者向けの文面への変換は GUI が行う。PySCF 版の `pyscf_backend/pipeline.py` とは独立しており（`uma_backend` は `pyscf_backend` に依存しない）、エンジンごとに別々に変えていける（v0.2.1 で `gui_uma.py` から分離した）。

	- `CalculationSettings(charge: int, multiplicity: int, model_key: str, do_frequency: bool = True, input_filename: str = "")`

		目的: 利用者が指定する計算条件を保持する。`input_filename` は計算ログに記載する。

	- `CalculationResult(structure, opt_result, freq_result, final_symbols, final_coords, device_label, out_dir, final_xyz_path, traj_xyz_path, log_path, total_seconds)`

		目的: 計算結果（最適化結果、振動数結果、最終構造、デバイスの説明）と、書き出したファイルの場所を保持する。画面表示・ダウンロードにそのまま使う。

	- `run_calculation(structure, settings: CalculationSettings, defaults: dict, log = print) -> CalculationResult`

		引数: 読込みと入力検証が済んだ構造、計算条件、`config/uma_defaults.yaml` の辞書、ログ出力関数。戻り値: 計算結果。目的: 上記の流れを最初から最後まで実行し、進捗（最適化の各ステップ、Hessian 計算の進み具合）・注意（CPU での低速、収束しなかった場合、原子数が多い場合）・所要時間を `log` へ出す。例外: トークン・アクセス権・ライブラリ未導入は `uma_hf.UmaSetupError`、ライブラリを読み込めない場合は `ImportError`、設定の誤りは `ValueError`。技術選定: 計算の流れを画面から分け、UMA・fairchem・Colab なしで、段階の呼出し順序と受渡しを単体テストできるようにする。呼出先: `uma_backend.uma_hf.check_model_access`, `uma_backend.uma_engine.get_device`, `describe_device`, `load_predictor`, `make_calculator`, `build_atoms`, `uma_backend.uma_optimize.run_geometry_optimization`, `uma_backend.uma_freq.run_frequency_analysis`, `common.writer_xyz.write_optimization_outputs`, `uma_backend.uma_report.build_log_text`; 呼出元: `gui_uma.build_app`。

- `uma_report.py`

	- `build_log_text(*, version: str, model_key: str, task_name: str, device_label: str, input_filename: str, charge: int, multiplicity: int, opt_result, freq_result = None, total_seconds: float | None = None) -> str`

		引数: バージョン、計算条件、入力名、電荷・多重度、最適化結果、任意の振動数結果・合計時間。戻り値: UTF-8 テキストログ。目的: 再現に必要な条件、履歴、振動数、UMA 通知をひとつの出力にまとめる。呼出先: `common.energy_plot.relative_energies_kcal`, `uma_backend.uma_notice.notice_text`; 呼出元: `gui_uma.build_app`。

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

`main`ブランチに`AGENTS.md`を入れないための、gitフック(シェルスクリプト)。全ブランチで追跡する。使うには、クローンごとに
`git config core.hooksPath .githooks`と`chmod +x .githooks/*`が必要(「`AGENTS.md`のGit管理」を参照)。

- `check-agents.sh`

	現在のブランチが`main`で、`AGENTS.md`が追跡されている(git のインデックスに入っている)ときは、メッセージを出して終了コード1で終わる。それ以外は0。`pre-commit`・`pre-merge-commit`が呼び出す。

- `pre-commit` / `pre-merge-commit`

	`check-agents.sh`を呼び出すだけのスクリプト。通常のコミットと、マージのコミットの前に、それぞれ実行される。

- `pre-push`

	pushされる参照のうち、`refs/heads/main`・`refs/tags/*`の指すコミットに`AGENTS.md`が含まれていれば、終了コード1でpushを中止する。削除のpushは対象外。

### プロジェクト内呼出先一覧

以下は標準ライブラリおよび外部ライブラリを除く、実装モジュール間の直接呼出しを網羅した一覧である。各モジュール内の private 関数、GUI のイベント処理、クラスのメソッド呼出しも含む。

- `gui.build_app`

	`pyscf_backend.load_yaml`; `common.gui_parts.ChargeInput`, `MultiplicityInput`; `common.gui_parts.StructureFileInput.read`; `common.gui_parts.EnergyStructureViewer.show`; `common.gui_parts.VibrationViewer.setup`; `common.gui_parts.DownloadPanel.show`; `common.gui_output.default_download_stem`, `xyz_download_items`; `common.gui_input.load_uploaded_structure`; `pyscf_backend.pipeline.CalculationSettings`, `run_calculation`; `pyscf_backend.analysis_pyscf.orbital_choices`, `compute_mulliken_charges`; `pyscf_backend.visualizer_pyscf.render_orbital`, `atomic_charges_table_html`, `render_charges` を呼び出す。`pyscf_backend.engine.SCFConvergenceError` と `common.io_reader.StructureError` は、例外の変換に使う。

- `gui_uma.build_app`

	`uma_backend.load_yaml`; `common.gui_parts.dropdown_from_list`, `StructureFileInput.read`, `EnergyStructureViewer.show`, `VibrationViewer.setup`, `DownloadPanel.show`, `ChargeInput`, `MultiplicityInput`; `common.gui_output.default_download_stem`, `xyz_download_items`; `common.gui_input.load_uploaded_structure`; `uma_backend.uma_pipeline.CalculationSettings`, `run_calculation` を呼び出す。`uma_backend.uma_hf.UmaSetupError` と `common.io_reader.StructureError` は、例外の変換に使う。

- `common.colab_widgets`

	`build_drop_zone_html` は `check_safe_id` を呼び出す。これ以外のプロジェクト内モジュールは呼び出さない。

- `common.energy_plot`

	`nice_ticks` は `_nice_step` を、`build_energy_plot_html` は `relative_energies_kcal`, `nice_ticks`, `_format_tick`, `common.colab_widgets.check_safe_id` を呼び出す。

- `common.config`

	プロジェクト内の別関数を呼び出さない。

- `common.gui_input`

	`extract_uploaded_file` は `common.io_reader.StructureError` を利用する。`load_uploaded_structure` は `common.io_reader.read_structure`, `validate_structure`, `validate_charge_and_multiplicity` を呼び出す。`parse_charge` は `ChargeInputError` を送出する。`format_charge` などの他の関数はプロジェクト内処理を呼び出さない。

- `common.gui_output`

	各関数はプロジェクト内の別関数を呼び出さない。

- `common.gui_parts`

	`StructureFileInput.__init__` は `common.colab_widgets.is_colab`, `register_callback`, `build_drop_zone_html` を、`_on_file_dropped` は `parse_dropped_payload` を、`read` は `common.gui_input.extract_uploaded_file` を呼び出す。`EnergyStructureViewer.__init__` は `register_callback` を、`show` は `_draw_energy_plot` と `_show_structure_at_step` を、`_show_structure_at_step` は `common.plot_common.render_single_structure` を、`_draw_energy_plot` は `build_energy_plot_html` を、スライダー／SVG のイベント処理はこれらを再呼出しする。`VibrationViewer._on_button_clicked` は `common.plot_common.render_vibration` を、`DownloadPanel.show` の生成ハンドラは `common.gui_output.sanitize_filename_stem` を呼び出す。`ChargeInput.__init__` は `common.gui_input.format_charge` を、`_on_text_changed` は `parse_charge` と `format_charge` を、`_step` は `format_charge` を呼び出す。

- `common.io_reader`

	`read_structure` は拡張子に応じて `read_xyz` または `_read_with_ase` を呼び出す。その他の関数はプロジェクト内関数を呼び出さない。

- `common.plot_common`

	`render_vibration` は `common.writer_xyz.multiframe_xyz_string` を呼び出す。その他の関数はプロジェクト内関数を呼び出さない。

- `common.writer_xyz`

	`write_final_structure`, `write_trajectory`, `xyz_string`, `multiframe_xyz_string` はいずれも `_format_xyz_block` を呼び出す。

- `pyscf_backend.engine` `write_optimization_outputs` は `write_final_structure` と `write_trajectory` を呼び出す。

	`_load_functional` と `_load_basis` は `pyscf_backend.load_yaml`（`common.config.load_yaml` の別名）を、`build_mole` は `_load_basis` を、`build_scf` は `_load_functional` と `_try_import_gpu4pyscf` を呼び出す。`run_scf` はプロジェクト内の別関数を呼び出さない。

- `pyscf_backend.optimize`

	`run_geometry_optimization` は `pyscf_backend.engine.build_scf`, `_make_callback`, `_to_numpy` を呼び出す。`_make_callback` が返す callback は `OptimizationResult` の履歴へ記録する。その他の関数はプロジェクト内関数を呼び出さない。

- `pyscf_backend.freq`

	`run_frequency_analysis` は結果辞書の版差を吸収するため `_get` を呼び出す。その他の関数はプロジェクト内関数を呼び出さない。

- `pyscf_backend.analysis_pyscf`

	`orbital_choices` は `_occupations` と `valence_space_size` を、`valence_space_size` は `_atom_symbols` と `_core_and_valence_orbital_counts` を呼び出す。その他の関数はプロジェクト内関数を呼び出さない。

- `pyscf_backend.pipeline`

	`run_calculation` は、`engine.gpu_runtime_detected`, `engine.contains_transition_metal`, `engine.build_mole`, `engine.build_scf`, `engine.run_scf`, `optimize.run_geometry_optimization`, `freq.run_frequency_analysis`, `common.writer_xyz.write_optimization_outputs`, `writer_molden.write_molden` を呼び出す。

- `pyscf_backend.visualizer_pyscf`

	`render_orbital` は `_mo_coeff_for_cube` と `_max_abs_from_cube_file` を、`add_atom_charge_spheres` は `_charge_gradient_color` を、`render_charges` は `add_atom_charge_labels` と `add_atom_charge_spheres` を呼び出す。その他の関数はプロジェクト内関数を呼び出さない。

- `pyscf_backend.writer_molden`

	プロジェクト内の別関数を呼び出さない。

- `uma_backend.uma_engine`

	`load_predictor` は `uma_hf.UmaSetupError` と、失敗時に `uma_hf.explain_hf_error` を呼び出す。その他の関数はプロジェクト内関数を呼び出さない。

- `uma_backend.uma_hf`

	`login_from_environment` は `login_with_token` を、`check_model_access` は `has_hf_token` と、失敗時に `explain_hf_error` を呼び出す。

- `uma_backend.uma_freq`

	`run_frequency_analysis` は内部の `forces_fn` を作り、`compute_hessian_fd` と `harmonic_analysis` を呼び出す。その他の関数はプロジェクト内関数を呼び出さない。

- `uma_backend.uma_notice`

	プロジェクト内の別関数を呼び出さない。

- `uma_backend.uma_optimize`

	`run_geometry_optimization` は内部の `record` を最適化器のコールバックとして使い、`OptimizationResult` に履歴を記録する。その他の関数はプロジェクト内関数を呼び出さない。

- `uma_backend.uma_pipeline`

	`run_calculation` は、`uma_hf.check_model_access`, `uma_engine.get_device`, `describe_device`, `load_predictor`, `make_calculator`, `build_atoms`, `uma_optimize.run_geometry_optimization`, `uma_freq.run_frequency_analysis`, `common.writer_xyz.write_optimization_outputs`, `uma_report.build_log_text` を呼び出す。

- `uma_backend.uma_report`

	`build_log_text` は `uma_backend.uma_notice.notice_text` を呼び出す。

### tests

テストは `python -m unittest discover -s tests -v` または pytest で実行する。外部サービス・GPU・実モデルダウンロードを必要とする部分は、フェイク環境または小さな ASE モデルで境界を検証する。以下は各テストモジュールが検証するプロジェクト内の関数・クラス・ファイルの完全一覧である。

- `fake_gui_env.py`

	`fake_gui_env(colab: bool = True)`、`_build_ipywidgets`、`_build_ipython_display`、`_Env` は、`test_gui_parts.py` で `common.gui_parts` をブラウザや Colab 接続なしで検証するための代用品（Text・IntText・Button・Dropdown などの代用ウィジェットを含む）を提供する。

- `test_analysis_pyscf.py`

	対象: `pyscf_backend.analysis_pyscf.valence_space_size`, `orbital_choices`, `compute_mulliken_charges`。PySCF を実行せず、必要な属性だけを持つ代用の SCF・分子オブジェクトで、価電子殻・内殻の軌道数の数え上げ、閉殻の HOMO/LUMO 表示名と縮退、開殻（α・β の 2 行配列、2 つの配列の組、ROHF）の SOMO 表示名と既定の軌道、エネルギー（eV）の併記と換算、リストの並び順（エネルギーの低い軌道が下）、軌道数の上限、元素と電荷の対応を検証する。

- `test_colab_widgets.py`

	対象: `common.colab_widgets.parse_dropped_payload`, `build_drop_zone_html`, `check_safe_id`。許可拡張子、Base64、サイズ制限、ディレクトリ部分の除去、HTML 識別子の安全性を検証する。

- `test_common_config.py`

	対象: `common.config.load_yaml`, `CONFIG_DIR`, `PROJECT_ROOT`。`config/` の場所、YAML の読込み、存在しないファイルのエラー、`pyscf_backend`・`uma_backend` が同じ関数・同じ場所を使っていること（別名）を検証する。

- `test_energy_plot.py`

	対象: `common.energy_plot.relative_energies_kcal`, `nice_ticks`, `build_energy_plot_html`, `HARTREE_TO_KCAL_MOL`。最後の相対エネルギー基準、目盛り、SVG の点・選択マーカー・ツールチップ・クリックコールバック、識別子の安全性、`colab_widgets` との分離を検証する。

- `test_engine.py`

	対象: `pyscf_backend.engine.contains_transition_metal`, `gpu_runtime_detected`。遷移金属の判定（各周期の d ブロック元素と、隣接する主族元素の区別）と、`subprocess.run` を差し替え、`nvidia-smi` の成功・失敗・コマンド不在・タイムアウトで GPU 有無を正しく判定することを検証する（Mole・SCF の構築と実行は PySCF が必要なため、Colab 実機で確認する）。

- `test_githooks.py`

	対象: `.githooks/`の4つのファイル。実行権限とシバン行の確認に加え、一時的なgitリポジトリ(利用者のgit設定の影響を受けないよう、`HOME`を差し替える)で、`main`上で`AGENTS.md`を追跡したコミットの拒否、`develop`上のコミットの許可、`develop`→`main`のマージ(`--no-ff --no-commit`)が`git rm --cached`の後にだけ成功すること、自動コミットされるマージの拒否、`main`・注釈付きタグのpushの中止、`develop`のpushの許可、削除のpushが妨げられないことを検証する。gitが使えない環境では、動作の検証だけスキップする。

- `test_gui_input.py`

	対象: `common.gui_input.extract_uploaded_file`, `load_uploaded_structure`, `format_charge`, `parse_charge`, `ChargeInputError`。ipywidgets 7/8 とドロップ入力の優先順位、構造の読込みと検証の順序・一時ファイルの拡張子と後始末、電荷の正負の表示・全角数字・Unicode のマイナス・空白・無効値を検証する。`load_uploaded_structure` は `io_reader` の関数を差し替え、受け渡しだけを確認する。 `read_uploaded_structure`（一時ファイルの拡張子・後始末・検証をしないこと）と `describe_structure` も検証する。

- `test_gui_output.py`

	対象: `common.gui_output.sanitize_filename_stem`, `default_download_stem`, `xyz_download_items`。ファイル名の禁止文字除去、日本語名、既定の結果名、ダウンロード項目の形を検証する。

- `test_gui_parts.py`

	対象: `common.gui_parts.dropdown_from_list`; `StructureFileInput.__init__`, `_on_file_dropped`, `_on_upload_changed`, `read`; `EnergyStructureViewer.__init__`, `show`, `_show_structure_at_step`, `_draw_energy_plot`, `_on_slider_changed`, `_on_plot_clicked`; `VibrationViewer.__init__`, `setup`, `_on_button_clicked`; `DownloadPanel.__init__`, `show`; `ChargeInput.__init__`, `_on_text_changed`, `_step`; `MultiplicityInput.__init__`, `value`。Colab／非 Colab 入力、SVG コールバック、エネルギーと座標の対応、スライダー同期、描画失敗表示、振動モード、ダウンロード名と再描画、電荷入力の整形・無効値の巻き戻し・±1 ボタン、多重度入力の値の取得を検証する。 受け取った構造の自動表示（ドロップ・ボタン、概要、読み込めない内容の説明、表示の失敗がファイルの受取りを妨げないこと）、`EnergyStructureViewer`・`VibrationViewer`・`DownloadPanel` の `reset`、`VibrationViewer.setup` による前回のアニメーションの消去も検証する。

- `test_io_reader.py`

	対象: `common.io_reader.read_xyz`, `read_structure`, `validate_structure`, `validate_charge_and_multiplicity`, `Structure`, `StructureError`。XYZ の読込み、元素記号正規化、異常入力、原子重なり、電荷・多重度の整合、拡張子振り分けを検証する。

- `test_config.py`

	対象: `pyscf_backend.load_yaml` と `config/purposes.yaml`, `functionals.yaml`, `basis_sets.yaml`, `defaults.yaml`。PySCF 用 YAML の必須キー、HF/B3LYP、基底関数、既定値を検証する。

- `test_notebooks_hidden_code.py`

	対象: `ColabApp.ipynb`, `ColabApp_UMA.ipynb`。すべてのコードセルが `cellView: form` と先頭行の `#@title 題名` を持ち（コード非表示）、題名が重複せず、セル ID が保持されていることを検証する。

- `test_pipeline.py`

	対象: `pyscf_backend.pipeline.CalculationSettings`, `CalculationResult`, `run_calculation`。`engine`・`optimize`・`freq`・`writer_molden` を代用の関数に差し替え、段階の呼出し順序と引数（再計算は常に CPU、最適化時の密度行列を初期値に渡す）、振動数計算の有無、GPU の自動判定と明示指定、原子数の注意の閾値、遷移金属の拒否（計算前）、段階の例外がそのまま送出されること、出力ファイルの名前と中身、ログの内容を検証する。

- `test_readme.py`

	対象: `README.md`, `pyscf_backend.__version__`, `uma_backend.__version__`。両パッケージの版数と README 冒頭の表示、一対のコードフェンス、相対リンク、バッククォートで記載されたファイル、両 Colab ノートブックへのリンク、廃止済み `build_notebook.py` の不在を検証する。

- `test_requirements.py`

	対象: `requirements.txt`, `requirements-uma.txt`。PySCF 用／UMA 用の必須パッケージ、PySCF 専用パッケージの UMA 側からの除外、`torch` と `ipywidgets` を requirements で固定しない方針を検証する。`plotly` と `kaleido` は v0.2.1 で PySCF 用 requirements からも外したため、必須パッケージの検証対象に含めない。

- `test_uma_config.py`

	対象: `uma_backend.load_yaml` と `config/uma_defaults.yaml`, `uma_models.yaml`。UMA の GUI・タスク・最適化・振動数・検証設定、モデルキーの一意性と非推奨モデルの除外、存在しない YAML のエラーを検証する。

- `test_uma_engine.py`

	対象: `uma_backend.uma_engine.describe_device`, `load_predictor`, `clear_predictor_cache`。CPU 警告、`fairchem` 未導入時の準備エラー、ゲート付きモデルの拒否が `uma_hf.UmaSetupError` になること、他の例外は包まないこと、同じモデル・デバイスは 1 回だけ読み込むことを、代用の `fairchem` で検証する。認証関連の名前が `uma_engine` に残っていない（再エクスポートされていない）ことも検証する。

- `test_uma_hf.py`

	対象: `uma_backend.uma_hf.login_with_token`, `login_from_environment`, `has_hf_token`, `explain_hf_error`, `check_model_access`, `UmaSetupError`。Hugging Face トークンの空値・環境変数処理・非保持、ゲート付きモデル・HTTP エラーの説明を検証する。

- `test_uma_freq.py`

	対象: `uma_backend.uma_freq.compute_hessian_fd`, `harmonic_analysis`, `FrequencyResult`。二原子・直線／非直線三原子・単原子の有限差分 Hessian、質量依存性、負の曲率、並進・回転除去、回転不変性、進捗通知を検証する。ASE が入っている環境では、さらに、`run_frequency_analysis`の結果を、ASE の`Vibrations`(EMT で緩和した Cu₂・Cu₃・Cu₄。ゼロ付近の並進・回転の値を除き、絶対値の大きい 3N-6 個[直線分子は 3N-5 個]と比較)と、`harmonic_analysis`の結果を、ASE の`VibrationsData.from_2d`(バネのモデルの Hessian)と、照合する(ASE が入っていない環境では、この部分だけスキップ。ASE の返す値を比較用にそろえる補助関数は、ASE なしでも検証する)。

- `test_uma_pipeline.py`

	対象: `uma_backend.uma_pipeline.CalculationSettings`, `CalculationResult`, `run_calculation`。`uma_hf`・`uma_engine`・`uma_optimize`・`uma_freq` を代用の関数に差し替え、段階の呼出し順序と引数（タスク名は設定ファイルから）、振動数計算の有無と、最終構造に置いた複製への実行、デバイスごとの注意（CPU での低速）、収束しなかった場合の注意、原子数の注意の閾値、Hessian 進捗の報告間隔、アクセス権の確認が最初に行われること、段階の例外がそのまま送出されること、出力ファイルの名前と中身、計算ログへ渡す内容を検証する。

- `test_uma_notebook.py`

	対象: `ColabApp_UMA.ipynb` と `uma_backend.uma_notice.notice_text` が示す一次情報。ノートブックのメタデータ、セル ID、保存出力、トークン非保存、トークン入力セルの順序、ライセンス案内と引用の位置・内容を検証する。

- `test_uma_notice_report.py`

	対象: `uma_backend.uma_notice.notice_text`, `uma_backend.uma_report.build_log_text`, `uma_backend.uma_optimize.OptimizationResult`, `uma_backend.uma_freq.FrequencyResult`。UMA の一次情報・引用、計算条件、履歴、未収束表示、振動数、通知、秘匿情報を含まないログを検証する。

- `test_uma_optimize.py`

	対象: `uma_backend.uma_optimize.run_geometry_optimization`, `OptimizationResult.final_fmax`。ASE EMT を使い、対応する最適化器の選択、収束・未収束、エネルギーの eV→Hartree 変換、重複しない履歴、入力 Atoms 非変更、進捗通知を検証する。

- `test_version_sync.py`

	対象: `common.version.__version__`, `pyscf_backend.__version__`, `uma_backend.__version__`。両パッケージの値が `common.version` の値と一致し、`major.minor.patch` 形式のリリース番号であることを検証する。

- `test_visualizer.py`

	対象: `pyscf_backend.visualizer_pyscf._max_abs_from_cube_file`, `atomic_charges_table_html`, `_charge_gradient_color`。PySCF を実行せず、cube 値の読取り、電荷表 HTML、正・中性・負の電荷色を検証する。 開殻（UHF/UKS）の 3 次元の軌道係数からα軌道を取り出す `_mo_coeff_for_cube` も検証する。

- `test_writer_xyz.py`

	対象: `common.writer_xyz.xyz_string`, `multiframe_xyz_string`, `write_final_structure`, `write_trajectory`, `write_optimization_outputs`。XYZ の形式、コメント、フレーム数、標準のファイル名と書出し先、最終構造がトラジェクトリの最終フレームと別でもよいことを検証する。

### references

外部プロジェクト ColabReaction の notebook、利用者マニュアル、ライセンスの参照コピー。アプリケーションの実行時依存ではなく、UI・操作設計の比較資料としてのみ保管する。
