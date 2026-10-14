# qchem_colab_app

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/orgchem610/qchem_colab_app/blob/main/ColabApp.ipynb) PySCF版
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/orgchem610/qchem_colab_app/blob/main/ColabApp_UMA.ipynb) UMA版

**GitHubリポジトリ: https://github.com/orgchem610/qchem_colab_app**
(今後、コードの変更・バージョン管理はこのリポジトリで一元管理します)

Google Colab上で動作する計算化学プロトタイプです。Gaussian等のライセンスソフトを
利用できない方(高校生等)でも、ブラウザだけで構造最適化・振動数解析を実行できることを
最終目標にしています。将来的には、本ツールで最適化した構造を
[ColabReaction](https://github.com/BILAB/ColabReaction) にそのまま渡し、
反応経路探索・TS(遷移状態)最適化へシームレスにつなげることを目指しています。

**現在のバージョンは v0.2.0 です。** 2つのノートブックで構成されています。

| ノートブック | 計算エンジン | 特徴 |
|---|---|---|
| `ColabApp.ipynb`(PySCF版) | PySCF(計算手法 HF・B3LYP、基底関数 3-21G・6-31G・6-31G*・6-31G**) | 量子化学計算。分子軌道・原子電荷・molden出力に対応。GPUランタイムでは、GPU4PySCFを自動で使用 |
| `ColabApp_UMA.ipynb`(UMA版) | 機械学習ポテンシャル[UMA](https://huggingface.co/facebook/UMA)(ASE + fairchem-core) | 高速。T4 GPUを前提。**結果は機械学習による予測値で、量子化学計算そのものの値ではありません。** Hugging Faceのアクセス申請とトークンが必要 |

2つのノートブックは独立しており、お互いに影響しません(`uma_app/`は、PySCF専用の`qcapp/`に依存しません)。
PySCF版の対応範囲は、`config/` 以下のYAMLファイルを編集するだけで順次拡張していく設計になっており、
実際にB3LYPと6-31G系列の追加は`engine.py`等のコードを一切変更せず、設定ファイルの
追記のみで行えました(詳細は下記「拡張のしかた」参照)。

## できること

### PySCF版(`ColabApp.ipynb`)

- 初期構造のアップロード: `.xyz`(自前パーサー)に加え、`.com`/`.gjf`(Gaussian入力)・
  `.pdb`はASE経由で読み込み可能(`.mol`/`.sdf`は未対応。理由は下記参照)。
  入力欄へのファイルの**ドラッグ&ドロップ**にも対応(「ファイルを選択」ボタンでも選べます)
- エネルギー収束グラフ: グラフ上の点を**クリック**すると、対応する構造とエネルギーを表示
  (ColabReactionを参考に実装。クリックが効かない環境向けに、スライダーでも同じ操作ができます)
- 電荷・スピン多重度を指定(スピン多重度・電荷の組み合わせが化学的に妥当かを自動チェック)。
  電荷は、正の値を「+1」の形で表示し、入力は「1」でも「+1」でも構いません(「−1」「+1」のボタンもあります。UMA版と共通)
- 構造最適化: 計算手法(HF, B3LYP)× 基底関数(3-21G, 6-31G, 6-31G*, 6-31G**)の
  組み合わせで実行可能。B3LYPは"b3lypg"(Gaussianと同じVWN3版の相関汎関数)を
  明示的に指定しており、Gaussianと同じ定義のB3LYPになるようにしている
- 振動数解析(既定でON。ZPE・自由エネルギーの概算値も出力、虚振動があれば警告)
- 可視化: エネルギー収束グラフ、振動アニメーション、
  分子軌道(HOMO/LUMO周辺)、原子電荷の可視化(球の色はMulliken電荷基準のグラデーション:
  正電荷=青・中性付近=緑・負電荷=赤。数値ラベルの表示有無はチェックボックスで切り替え可能)
  (すべてノートブック内、py3Dmol / 自前のSVGグラフ)。最適化の軌跡アニメーションは、
  グラフの点から各ステップの構造を見られるようになったため、v0.1.17で廃止しました
  (多フレームの`.xyz`としてダウンロードすることはできます)
- 出力ファイル: 最終構造(`.xyz`, ColabReactionにそのままアップロード可能)、
  最適化トラジェクトリ(多フレーム`.xyz`)、`.molden`(構造+分子軌道。GaussView /
  Avogadro / Multiwfn 等で開けます。MacMolPlt向けにデカルト型基底関数(6D/10F)で
  出力しています)。ダウンロード時にファイル名を自由に指定可能(既定値は、UMA版と同じ「入力ファイル名_result」)
- GPUランタイムが検出された場合は、GPU4PySCFを自動で使用し(GUIにチェックボックスはありません)、
  利用できない場合は自動的にCPUにフォールバック

### UMA版(`ColabApp_UMA.ipynb`)

詳細は、下記「UMA版」の節を参照してください。

## できないこと・既知の制約(v0.2.0時点)

### PySCF版

- `.mol` / `.sdf` 形式の読み込みは未対応です。ASEはこれらのMDL系フォーマットに
  標準対応しておらず(結合次数の情報を持つ形式のため、座標主体のASEの守備範囲外)、
  対応するにはRDKit等の追加ライブラリが必要になります(下記「依存ライブラリの
  増減」参照)。今回は「極端にライブラリが増えなければ対応する」という方針のもと、
  ASE1つの追加で済む`.com`/`.gjf`/`.pdb`のみ対応しました。
- 遷移金属元素を含む構造はアップロード時にエラーとして弾かれます(ECP付き基底が
  未実装のため)
- TS(遷移状態)構造最適化は未実装です(`config/purposes.yaml` にプレースホルダとして
  記載していますが、実装はこれからです)
- B3LYP・大きめの基底関数(6-31G**等)は、HF・3-21Gに比べて1ステップあたりの
  計算コストが増えます(B3LYPは数値積分グリッドの評価が追加でかかり、基底関数が
  増えれば行列サイズも増えるため)。66原子程度のHF/3-21Gで振動数計算がColabの
  セッション中に終わらなかった実績があるため、大きな分子でB3LYP・6-31G**等を
  使う場合は、まず振動数計算をオフにして構造最適化のみで所要時間を確認する、
  基底関数を小さいものから試す、といった進め方を推奨します。

### UMA版

- TS(遷移状態)探索、座標を固定した最適化(スキャン)は未実装です。
- 構造ファイルの読み込みは`common/io_reader.py`を共有しているため、**H〜Xe**の元素のみ対応です。
- 分子軌道・原子電荷・moldenの出力はありません。UMAが返すのはエネルギー・力・応力であり、
  電子状態(波動関数・原子電荷)は出力しないためです。
  (これらが必要な場合の運用は、下記「今後の予定・検討中の事項」を参照してください)

### 開発・動作確認の進め方について

コードの作成・単体テストは、ネットワークに接続できないサンドボックスで行っているため、
PySCF・fairchem・Google Colab実機を使った動作は、そこでは確認できません。
Colab上での動作(PySCFの呼び出し、UMAの推論、ドラッグ&ドロップ・グラフのクリックの
JavaScript連携など)は、リリース前にColab実機で確認してから、タグを打つ運用にしています。
単体テストで確認できる範囲は`tests/`にあります(実行方法は下記「ディレクトリ構成」参照)。

## ディレクトリ構成

```
qchem_colab_app/
├── ColabApp.ipynb              # PySCF版ノートブック(Setup Section / Execution Section)
├── ColabApp_UMA.ipynb           # UMA版ノートブック(ランタイム 2026.07・T4 GPUが記録済み)
├── README.md                     # 本ファイル
├── THIRD_PARTY_NOTICES.md         # UMA版が利用する外部ソフトウェア・データのライセンスへのリンク
├── requirements.txt               # PySCF版の依存パッケージのバージョン指定(初回インストール用の目安)
├── requirements-uma.txt            # UMA版の依存パッケージ(PySCFは使わない)
├── requirements-lock.txt           # Colab実行時に自動生成される「動作確認済み」の正確な記録
├── requirements-uma-lock.txt        #   (どちらも、依存関係が安定するまで当面はGit管理対象外)
├── .gitignore
├── config/
│   ├── purposes.yaml         # 計算目的の選択肢(現在: 構造最適化のみ)
│   ├── functionals.yaml      # 計算手法の選択肢(HF, B3LYP)
│   ├── basis_sets.yaml       # 基底関数の選択肢(3-21G, 6-31G, 6-31G*, 6-31G**)
│   ├── defaults.yaml         # 電荷・多重度・収束条件などの既定値(PySCF版)
│   ├── uma_defaults.yaml     # UMA版の既定値(最適化の収束条件・振動数計算の刻み幅など)
│   └── uma_models.yaml       # UMA版で選べるモデルの一覧
├── common/                    # 計算エンジンに依存しない共通モジュール(PySCF版・UMA版の両方が使う)
│   ├── io_reader.py             # 構造ファイルの読み込み・入力バリデーション
│   ├── writer_xyz.py             # xyz出力(単一構造・多フレーム)
│   ├── plot_common.py             # 構造・振動アニメーションの3D表示(py3Dmol)
│   ├── colab_widgets.py            # ブラウザ側JavaScript ↔ Colabのコールバック(ドロップ領域・クリックできるSVGグラフ)
│   ├── gui_helpers.py               # GUI用の補助関数(アップロードされたファイルの取り出し・ダウンロード名・電荷の表示と読み取り)
│   └── gui_parts.py                  # GUI共通の画面部品(ファイル入力・グラフ+構造表示・振動・ダウンロード・電荷入力)
├── qcapp/                     # PySCFを計算エンジンとするab initio計算専用(uma_appからは呼ばない)
│   ├── __init__.py               # バージョン番号, config/読み込み共通関数
│   ├── engine.py                  # Mole構築・SCF実行(GPU4PySCF自動フォールバック含む)
│   ├── optimize.py                 # geomeTRICによる構造最適化
│   ├── freq.py                      # Hessian・振動数解析
│   ├── writer_molden.py              # moldenファイル出力
│   ├── visualizer_pyscf.py            # 分子軌道・原子電荷等、PySCF固有の可視化
│   └── visualizer.py                   # common+pyscf固有の可視化をまとめたファサード(gui.py用)
├── uma_app/                   # UMA(機械学習ポテンシャル)専用(qcappには依存しない)
│   ├── __init__.py               # バージョン番号, config/読み込み共通関数
│   ├── uma_engine.py              # Hugging Faceのトークン・アクセス確認、モデルの読み込み、ASEのAtoms/Calculator
│   ├── uma_optimize.py             # ASE(LBFGS等)+UMAによる構造最適化
│   ├── uma_freq.py                  # 数値Hessianによる振動数解析(並進・回転を除去)
│   ├── uma_notice.py                  # UMAのライセンス・引用の一次情報へのリンク
│   ├── uma_report.py                   # 計算ログの組み立て
│   └── README.md                        # UMA版の詳細・トラブルシューティング
├── gui.py                     # PySCF版のGUI組み立て(ipywidgets)
├── gui_uma.py                  # UMA版のGUI組み立て(ipywidgets)
└── tests/
    ├── test_io_reader.py / test_config.py / test_visualizer.py   # 入力・設定・可視化(PySCF非依存部分)
    ├── test_colab_widgets.py       # ドロップ領域・クリックできるグラフ(JavaScriptを含むHTMLの生成)
    ├── test_gui_helpers.py          # ファイルの取り出し・ダウンロード名・電荷の表示と読み取り
    ├── test_gui_parts.py             # 共通の画面部品(電荷入力を含む。ipywidgets・Colabの代用品を使用)
    ├── test_notebooks_hidden_code.py  # 両ノートブックのコードセルが、既定でコード非表示になっているか
    ├── fake_gui_env.py                # test_gui_parts.py用の、ipywidgets・Colabの代用品
    ├── test_uma_*.py                   # UMA版(振動数の数値計算・最適化・ログ・設定・ノートブックの構成など)
    ├── test_requirements.py             # requirements*.txtの方針(ipywidgetsを指定しない、など)
    └── test_version_sync.py / test_readme.py   # バージョン番号の一致・本ファイルとの整合
```

テストは、次のコマンドで実行できます(ASEが入っていない環境では、ASEを使う一部のテストはスキップされます)。

```
python3 -m unittest discover -s tests -p "test_*.py"
```

### `common`/`qcapp`/`uma_app`という3つのトップレベルパッケージに分けた理由

「PySCF版・UMA版の両方から呼び出せる汎用的なコード」と「各計算エンジンに固有のコード」を
物理的に分離しておくための整理です。`common/`は引数がプレーンな
Pythonの値(元素記号・座標・エネルギーの数列等)で完結しており、PySCF版・UMA版の
どちらからもそのままimportして再利用しています。`qcapp/`(=PySCF専用)は
PySCFのMole/SCFオブジェクトに直接依存しており、UMA版では使えません。`uma_app/`
(=UMA専用)は`qcapp`を一切importしません(PySCFがインストールされていない環境でも
動くようにするため)。
`common`・`qcapp`・`uma_app`はいずれもリポジトリ直下の対等な(どれが親でも子でもない)
パッケージとして置いています。`qcapp/visualizer.py`は、この分割前と同じ
`visualizer.関数名(...)`という呼び方を`gui.py`側で変えずに済むよう、
`common`と`qcapp`固有の可視化関数をまとめて再エクスポートするだけの
薄いファサードです。

GUIの画面部品も、同じ考え方で整理しています。構造ファイルの入力・エネルギーグラフと構造表示・
振動アニメーション・ダウンロードは、PySCF版とUMA版で同じ動作のため、`common/gui_parts.py`に
共通の部品として切り出しました(v0.2.0)。各部品は、計算エンジンのモジュールをimportせず、
エネルギー・座標・振動数などのプレーンな値だけを受け取ります。エンジンごとに違う部分
(構造表示の見出しに足す情報など)は、部品に関数を渡して差し替えます。

(以前のバージョンでは`common/`を`qcapp/`の中に入れる構成でお渡ししましたが、
「`common`は`qcapp`専用の一部ではなく、`qcapp`と`uma_app`が対等に依存する
共通基盤である」という位置づけをより素直に表せるよう、上記の構成に修正しました)

### `gui.py`/`gui_uma.py`をルート直下に置いている理由(設計意図)

`gui.py`は「`qcapp`パッケージが提供する部品(入出力・計算・可視化)を
1つのColabアプリの画面として組み立てる」役割に特化した、**アプリの
組み立て役(エントリーポイント)**であり、`qcapp`パッケージ自体が提供する
再利用可能な部品(ライブラリ)とは性質が異なるため、意図的にパッケージの
外に置いています。UMA版の`gui_uma.py`も同じ考え方です。`gui.py`は`qcapp`と
`common`から、`gui_uma.py`は`uma_app`と`common`から、それぞれ必要な部品を
自由に組み合わせています。仮に`gui.py`を`qcapp`の中に、`gui_uma.py`を
`uma_app`の中に入れてしまうと、例えば`gui_uma.py`(`uma_app`側)が
`common`の関数を再利用する際に「`uma_app`パッケージの中から`common`
パッケージを参照する」という向きの依存が生まれます。これ自体は`common`が
独立したトップレベルパッケージである今の構成なら実は問題にはなりませんが、
「アプリの組み立て役」と「再利用可能な部品」という役割の違いを分かりやすく
保つため、`gui.py`/`gui_uma.py`はルート直下に置くことにしています。

## 使い方

Colab上での具体的な操作手順は、各ノートブック内のMarkdownセルに詳しく
書いてあります。ノートブックを開き、上から順にセルを実行してください
(各セルのコードは、既定では折りたたまれ、題名だけが表示されます。内容を確認したい場合は、
題名の左の矢印や「コードを表示」をクリックすると開けます。ColabReactionと同じ方式です)
(UMA版は、メニューの「ランタイム」→「すべてのセルを実行」で、操作画面が表示されるまで
自動で進みます)。初めてJupyter/Colabを使う方向けの手順は、本リポジトリを共有した際の
メッセージもあわせてご確認ください。

### ランタイム設定を毎回選び直さずに済ませる方法

「ハードウェアアクセラレータ(GPU/CPU)」と「ランタイムバージョン」の選択は、
どちらも`.ipynb`ファイル自体のメタデータとして保存されます(Colabが書き込みます)。

```json
"metadata": {
  "accelerator": "GPU",
  "colab": {
    "gpuType": "T4",
    "runtime_attributes": { "runtime_version": "2026.07" }
  }
}
```

`ColabApp_UMA.ipynb`は、UMAがGPUで高速に動作するため、**T4 GPU・ランタイムバージョン 2026.07**
を記録しています(ノートブック冒頭に、現在の環境が想定どおりかを確認するセルもあります)。
一方、PySCF版の`ColabApp.ipynb`は、このリポジトリを高校生等の不特定多数に公開する用途を考えると、
常にGPUを要求する設定にしてしまうと、GPUを使う必要のない小さな分子のテストでも
共有の限られたGPU割り当てを消費してしまうため、「ハードウェアアクセラレータ: なし(CPU)」の
ままにしておき、GPUで検証したいときだけ手動で切り替える運用を推奨します
(GPUランタイムに切り替えれば、GPU4PySCFを自動で使用します)。

## UMA版(`ColabApp_UMA.ipynb`)

機械学習ポテンシャル**UMA**(Meta FAIR Chemistry)を計算エンジンとして、構造最適化と振動数解析を
高速に行うノートブックです。**結果は機械学習による予測値であり、量子化学計算そのものの値では
ありません。** 構成・設計上の判断・トラブルシューティングの詳細は、
[`uma_app/README.md`](uma_app/README.md)にあります。

### できること

- 構造ファイル(`.xyz`/`.com`/`.gjf`/`.pdb`)のドラッグ&ドロップ(または選択)、UMAモデル
  (`uma-s-1p2p1`(既定)、`uma-m-1p1`)・電荷・スピン多重度の指定。電荷は、正の値を「+1」の形で表示し、
  入力は「1」でも「+1」でも構いません(「−1」「+1」のボタンもあります)
- 構造最適化(ASEのLBFGS。収束条件は力の最大値 ≤ 0.01 eV/Å、最大500ステップ。`config/uma_defaults.yaml`で変更可)。
  最大ステップ数までに収束しなかった場合も、途中経過の構造を表示します
- 振動数解析(任意): 力の中心差分で数値Hessianを作り、並進・回転を除いた3N−6個(直線分子は3N−5個)の
  振動モードを求めます。虚振動があれば警告し、ゼロ点エネルギーも出力します
- 可視化: エネルギー収束グラフ(点のクリックでその構造を表示)、振動アニメーション
- 出力: 最終構造(`.xyz`。ColabReactionやPySCF版にそのまま渡せます)、最適化トラジェクトリ(多フレーム`.xyz`)、
  計算ログ(条件・最適化の履歴・振動数・UMAのライセンスと引用へのリンク)。
  ダウンロードするファイル名の既定値は「入力ファイル名_result」です

### 使い方

1. (初回のみ)ノートブックの「事前準備」に従い、Hugging Faceのアカウント作成・UMAへのアクセス申請・
   アクセストークンの発行を行います。Colabの「シークレット」に`HF_TOKEN`として保存しておくと、入力も不要になります。
2. メニューの「ランタイム」→「すべてのセルを実行」を押します。
3. シークレットに保存していない場合は、「2. Hugging Faceのトークンを入力し、UMAへのアクセスを確認する」の
   セルに入力欄が表示されます。トークンを貼り付けてEnterキーを押してください(入力が必要なのは、この1回だけです)。
4. 以降は自動で進みます(初回は、ライブラリのインストールに数分かかります)。最後に操作画面が表示されます。

### Hugging Faceのトークンの扱い

トークンは、ノートブックの「2.」のセル(`getpass`、またはColabのシークレット)で受け取り、
環境変数`HF_TOKEN`(Hugging Face公式の標準の受け渡し方法)にだけ設定します。セルの変数には残さず、
画面・ログ・保存されるノートブックにも書き込みません。`uma_engine.login_from_environment()`が
環境変数を読み取ってログインするため、入力セルの作りを変えても、`uma_app`や`gui_uma.py`を
変更する必要はありません(疎結合)。トークンの入力欄をGUI(ipywidgets)に置く方式は、
入力値がウィジェットの状態として保持され、保存されるノートブックに残りうるため採用していません。

### UMAのライセンスと引用について

UMAの利用にあたっては、次の一次情報をご確認ください(ノートブックの冒頭にも、同じ内容を掲載しています)。

- ライセンス(FAIR Chemistry License v1): https://huggingface.co/facebook/UMA/blob/main/LICENSE
- Acceptable Use Policy・モデルカード: https://huggingface.co/facebook/UMA
- 引用: UMAを利用した成果を発表する場合は、以下の論文を引用してください(モデルカードの記載)。
  Wood, B. M. et al. *UMA: A Family of Universal Models for Atoms.* arXiv:2506.23971 (2025).
  https://arxiv.org/abs/2506.23971
- fairchem(コード、MITライセンス): https://github.com/facebookresearch/fairchem

そのほかのライブラリのライセンスは、[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)を参照してください。

## 今後の予定・検討中の事項

- **UMA版のTS(遷移状態)探索**: 未実装。`Sella`(外部パッケージ)またはASE組み込みのDimer法のどちらで実装するかは未定です
  (どちらを選んでも、新しいコードが必要です)。
- **座標を固定した構造最適化(スキャン)**: ColabReactionの`ColabReaction.ipynb`には実装がなかったため、
  必要になった時点で、UMA版・PySCF版のそれぞれについて検討します。
- **UMA版で分子軌道・原子電荷を見たい場合**: UMAは電子状態を出力しないため、現時点では、UMA版の最終構造(`.xyz`)を
  PySCF版に読み込ませて確認する運用が可能です。UMA版の画面から、UMAで最適化した構造に対してPySCFで
  一点計算を行う追加機能は、案として検討中です(PySCFのインストールとCPUの計算時間が必要になり、
  UMAとは別のレベルの電子状態になります)。
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
2. バックエンド側に `key` → 処理関数 の対応表を1箇所だけ持つ(例: `qcapp/dispatch.py`の`_HANDLERS`辞書)。
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

`qcapp/__init__.py` と `uma_app/__init__.py` の `__version__` は、**リポジトリ全体のリリース番号
(Gitタグ)と同じ値**にします。過去に、タグはv0.1.16なのに `__version__` が0.1.12のままだった
更新漏れがあったため、新しいタグを打つ前に、次の3点を確認してください。

1. 2つの `__version__` を、新しいバージョンに更新する(`tests/test_version_sync.py` が、2つの値の
   一致を検査します)
2. 本ファイル冒頭の「現在のバージョン」を更新する(`tests/test_readme.py` が、`__version__` との
   一致を検査します)
3. テストが通ることを確認する(`python3 -m unittest discover -s tests -p "test_*.py"`)

### ロールバックの方法

- 「最新版に不具合があった場合にすぐ前の版へ戻す」には、
  `git checkout v0.1.1` のようにタグを指定してチェックアウトするか、
  問題のコミットを `git revert <コミットID>` で打ち消してください。
- **`requirements-lock.txt`について(現在の方針)**: 依存ライブラリの
  組み合わせがまだ頻繁に変わる段階のため、当面は`.gitignore`に加えて
  Git管理から外しています(手元・Colab上には生成されますが、コミットは
  しません)。そのため現時点では「タグを戻す」際に依存バージョンまでは
  一緒に戻りません。依存関係が安定してきたら、動作確認済みの内容を
  改めてコミット対象に戻すことを検討してください。

## トラブルシューティング


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
  `qcapp/optimize.py` の `_make_callback()` 内で、
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
  下記「GUI部品の実装メモ」)。現在のGUIはplotly・kaleidoを使っていないが、
  `common/plot_common.py`の静的PNG出力関数のために`requirements.txt`には残している。
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
  同じセルを追加していません)。`common/gui_parts.py`・`common/gui_helpers.py`は、7.x・8.xの
  どちらでも動くように書いてあります。
- **UMA版のトラブルシューティング**(Hugging Faceのアクセス、`torch`の更新、GPUが使えない、など)は、
  [`uma_app/README.md`](uma_app/README.md)にまとめています。

## GUI部品の実装メモ(ドラッグ&ドロップ・グラフのクリック)

### 現在の方式

ファイルの**ドラッグ&ドロップ**と、エネルギーグラフの**点のクリック**は、どちらも
`common/colab_widgets.py`にある「ブラウザ側のJavaScript → Colabのコールバック → Python」という
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
(`StructureFileInput`、`EnergyStructureViewer`、`VibrationViewer`、`DownloadPanel`、`ChargeInput`)。
電荷の表示・読み取りの関数(`format_charge`、`parse_charge`)は、`common/gui_helpers.py`にあります。
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

## 使用ライブラリ・引用について

本アプリを公開するにあたり、利用しているライブラリのライセンス・引用に関する
表示義務を調査しました。結論として、**いずれのライブラリも「コードを改変せず
依存パッケージとして利用する」範囲では、アプリの画面上に法的な表示義務を課す
ものはありません**でした(Apache-2.0・BSD・MIT等、いずれも許諾的なオープン
ソースライセンスで、著作権表示の保持義務は「そのソフトウェア自身のソース/
バイナリを再配布する場合」に生じるものであり、pip経由で利用しているだけの
本アプリには該当しません)。とはいえ、実際に計算を行っているソフトウェアを
明記することは学術的にも礼儀としても重要なため、以下の通り情報を整理し、
本README内に謝辞として記載することにしました。

| ライブラリ | ライセンス | 備考 |
|---|---|---|
| PySCF | Apache License 2.0 | 計算結果を論文等で使用する場合は本体の引用を推奨(PySCFの公式サイト参照) |
| geomeTRIC | BSD 3-Clause | ログに表示される引用依頼(Wang, L.-P.; Song, C.C. (2016) *J. Chem. Phys.* 144, 214108)は法的義務ではなく開発者からのお願いですが、実際に構造最適化アルゴリズムを使わせてもらっているため、研究等で使う場合は引用を推奨します |
| GPU4PySCF | PySCF本体と同じApache-2.0系列と見られます(個別のライセンス文言までは今回未確認) | |
| ASE | GNU LGPL 2.1 | ライブラリとして(改変せず)利用する分にはアプリ側のライセンスに影響しません |
| ipywidgets / plotly / py3Dmol / kaleido | いずれもBSD/MIT系の許諾的ライセンス | |
| fairchem-core(UMA版) | MIT License | https://github.com/facebookresearch/fairchem |
| UMAの学習済みモデル(UMA版) | FAIR Chemistry License v1 | ライセンス全文: https://huggingface.co/facebook/UMA/blob/main/LICENSE |

**アプリ内の対応**: `README.md`にこの謝辞表を追加しました。あわせて、`ColabApp.ipynb`
の冒頭のMarkdownセルにも簡潔な謝辞を追記することを推奨します(次回のセル修正時に
反映します)。UMA(学習済みモデル)のライセンス・引用については、一次情報へのリンクを、
下記「UMA版」の節と`THIRD_PARTY_NOTICES.md`に掲載しています。
