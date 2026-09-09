# qchem_colab_app

**GitHubリポジトリ: https://github.com/orgchem610/qchem_colab_app**
(今後、コードの変更・バージョン管理はこのリポジトリで一元管理します)

Google Colab上で動作する量子化学計算プロトタイプです。Gaussian等のライセンスソフトを
利用できない方(高校生等)でも、ブラウザだけで構造最適化・振動数解析を実行できることを
最終目標にしています。将来的には、本ツールで最適化した構造を
[ColabReaction](https://github.com/BILAB/ColabReaction) にそのまま渡し、
反応経路探索・TS(遷移状態)最適化へシームレスにつなげることを目指しています。

**現在のバージョン(v0.1.1)は、計算手法 HF・基底関数 3-21G のみに対応した
最小プロトタイプです。** これは「まず最小構成で動作と所要時間を確認する」という
方針によるものです。対応範囲は `config/` 以下のYAMLファイルを編集するだけで
順次拡張していく設計になっています(詳細は下記「拡張のしかた」参照)。

## できること(v0.1.1)

- `.xyz` 形式の初期構造をアップロードして読み込み
- 電荷・スピン多重度を指定(スピン多重度・電荷の組み合わせが化学的に妥当かを自動チェック)
- HF/3-21G での構造最適化
- 振動数解析(既定でON。ZPE・自由エネルギーの概算値も出力、虚振動があれば警告)
- 可視化: エネルギー収束グラフ、最適化軌跡アニメーション、振動アニメーション、
  分子軌道(HOMO/LUMO周辺)、電荷密度の等値面表示(すべてノートブック内、py3Dmol / plotly)
- 出力ファイル: 最終構造(`.xyz`, ColabReactionにそのままアップロード可能)、
  最適化トラジェクトリ(多フレーム`.xyz`)、`.molden`(構造+分子軌道。GaussView / MacMolPlt /
  Avogadro / Multiwfn 等で開けます)
- GPU4PySCFが利用可能な場合は自動でGPUを使用し、利用できない場合は自動的にCPUに
  フォールバック

## できないこと・既知の制約(v0.1.1時点)

- HF以外の手法(B3LYP等)、3-21G以外の基底関数には未対応(`config/functionals.yaml`,
  `config/basis_sets.yaml` に追加すれば対応可能な設計にはなっています)
- 遷移金属元素を含む構造はアップロード時にエラーとして弾かれます(ECP付き基底が
  未実装のため)
- TS(遷移状態)構造最適化は未実装です(`config/purposes.yaml` にプレースホルダとして
  記載していますが、実装はこれからです)
- **開発環境の制約により、PySCF・GPU4PySCF等を実際にインストールして動作確認する
  ことができていません**(サンドボックス環境からネットワークへアクセスできないため)。
  pyscf/ase不要な部分(`config/`読み込み、入力バリデーション)は`tests/`で
  実際にテスト済みですが、PySCFを呼び出す部分(`engine.py`/`optimize.py`/`freq.py`)は
  Google Colab上で実際に動かして初めて検証できます。想定される調整点は下記
  「トラブルシューティング」に記載しています。

## ディレクトリ構成

```
qchem_colab_app/
├── ColabApp.ipynb          # ノートブック本体(Setup Section / Execution Section)
├── README.md                # 本ファイル
├── CHANGELOG.md              # バージョンごとの変更履歴
├── requirements.txt          # 依存パッケージのバージョン指定(初回インストール用の目安)
├── requirements-lock.txt     # 初回Colab実行時に自動生成される「動作確認済み」の正確な記録
├── .gitignore
├── config/
│   ├── purposes.yaml         # 計算目的の選択肢(現在: 構造最適化のみ)
│   ├── functionals.yaml      # 計算手法の選択肢(現在: HFのみ)
│   ├── basis_sets.yaml       # 基底関数の選択肢(現在: 3-21Gのみ)
│   └── defaults.yaml         # 電荷・多重度・収束条件などの既定値
├── qcapp/
│   ├── __init__.py           # バージョン番号, config/読み込み共通関数
│   ├── io_reader.py          # .xyz読み込み・入力バリデーション
│   ├── engine.py              # Mole構築・SCF実行(GPU4PySCF自動フォールバック含む)
│   ├── optimize.py            # geomeTRICによる構造最適化
│   ├── freq.py                 # Hessian・振動数解析
│   ├── writer_xyz.py           # xyz出力(単一構造・多フレーム)
│   ├── writer_molden.py        # moldenファイル出力
│   └── visualizer.py            # py3Dmol / plotly ビジュアライザー
├── gui.py                     # ipywidgets によるGUI組み立て
└── tests/
    ├── test_io_reader.py        # 入力読み込み・バリデーションの単体テスト
    └── test_config.py            # 設定ファイルのスキーマテスト
```

## 使い方

Colab上での具体的な操作手順は `ColabApp.ipynb` 内のMarkdownセルに詳しく
書いてあります。ノートブックを開き、上から順にセルを実行してください。
初めてJupyter/Colabを使う方向けの手順は、本リポジトリを共有した際のメッセージも
あわせてご確認ください。

## 拡張のしかた(新しい手法・基底関数を追加する)

コードを変更せず、`config/` 以下のYAMLに1エントリ追加するだけで選択肢が増えます。

例: B3LYPを追加する場合、`config/functionals.yaml` に以下を追記します。

```yaml
- label: "B3LYP"
  key: "b3lyp"
  engine: "dft"
  xc: "b3lyp"
```

例: 6-31G*を追加する場合、`config/basis_sets.yaml` の `main_group` に以下を追記します。

```yaml
- label: "6-31G*"
  key: "6-31g*"
  pyscf_basis: "6-31g*"
  ecp: null
```

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

### CHANGELOG.mdの二重管理を避ける方法

上記の運用にすると、`git merge --no-ff` で作られる合流コミットのメッセージや、
リリース時のタグメッセージそのものが「このバージョンで何が変わったか」の記録になります。
これをそのままGitHubの **Releases** 機能(タグを選んで「Create a new release」から
リリースノートとして貼り付けるだけ)に転記すれば、変更履歴はGitHub上の1箇所
(タグメッセージ・Releaseページ)に集約でき、`CHANGELOG.md`というファイルを
別途手で更新し続ける必要がなくなります。

このプロジェクトでもこの運用に切り替えることを推奨します。`CHANGELOG.md`は
今回はまだ残していますが(過去の記録として)、次にリリースする際("develop"を
"main"にマージしてタグを打つタイミング)にGitHub Releasesへの記録に一本化し、
`CHANGELOG.md`自体は削除する形で問題ないと思います。よろしければ次回の対応時に
削除します。

### ロールバックの方法

- 「最新版に不具合があった場合にすぐ前の版へ戻す」には、
  `git checkout v0.1.1` のようにタグを指定してチェックアウトするか、
  問題のコミットを `git revert <コミットID>` で打ち消してください。
- 依存パッケージのバージョンは、各タグの `requirements-lock.txt` と
  セットでコミットしてください。「タグを戻す」= 「コードと動作確認済みの
  ライブラリバージョンの両方が一緒に戻る」状態を保つことが目的です。

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
  使えなくても、CPU実行として問題なく計算は継続されます。
- **SCFが収束しない**: `engine.run_scf()` がレベルシフト付きで自動的に
  1回リトライしますが、それでも収束しない場合は画面に日本語の原因・対策が
  表示されます。初期構造・電荷・スピン多重度・基底関数の設定を見直してください。

## 将来的な構成: UMA利用版との分離

UMA(ColabReactionが使用している機械学習原子間ポテンシャル)による予備最適化・
振動数プレビュー機能は、この`ColabApp.ipynb`には組み込まず、**同じGitHubリポジトリ内に
別のノートブック(例: `ColabApp_UMA.ipynb`)を新規作成する形**で追加する方針です。
`config/` や `qcapp/` のロジックはリポジトリ単位で共通管理しつつ、Google Colab上では
`https://colab.research.google.com/github/orgchem610/qchem_colab_app/blob/main/ColabApp.ipynb`
(UMAなし版)と
`https://colab.research.google.com/github/orgchem610/qchem_colab_app/blob/main/ColabApp_UMA.ipynb`
(UMA版)という別々のURLで開けるようにします。UMA固有のロジックは
`qcapp/uma_engine.py`(新規)に、UMA版専用のGUI組み立ては`gui.py`を直接いじらず
`gui_uma.py`(新規)に分離し、`gui.py`(UMAなし版)には手を入れない設計とすることで、
1画面に選択肢が増えてごちゃつくことも、コードが複雑に絡み合うことも避けられます。

