# サードパーティのライセンス一覧(UMA版 ColabApp_UMA.ipynb)

UMA版が利用する外部のソフトウェア・データのライセンスの一覧です。
**一次情報で確認できたもの**と、**公開前に確認が必要なもの**を分けて記載しています。
(法的な助言ではありません。公開前に、各配布元で最新の内容を確認してください。)

## 一次情報で確認できたもの

| 名称 | 用途 | ライセンス | 確認元(確認日: 2026-10-10) |
|---|---|---|---|
| UMAの学習済みモデル(Hugging Face `facebook/UMA`) | 計算エンジン本体(重み) | FAIR Chemistry License v1(2025-05-14更新) | https://huggingface.co/facebook/UMA/blob/main/LICENSE |
| fairchem-core(コード) | UMAの推論 | MIT License(チェックポイントのライセンスは用途ごとに異なる) | https://github.com/facebookresearch/fairchem |

### UMAの学習済みモデルについて

- このリポジトリは、UMAの重みを**同梱も再配布もしません**。各利用者が、ご自身のHugging Faceアカウントで
  利用条件に同意し、Colab上で直接ダウンロードします(`uma_app/uma_engine.py`)。
- 条文上の主な義務は、①重み等を第三者に配布する場合は同じ契約条件で行い契約書の写しも渡すこと、
  ②研究成果を公表する場合はUMAを使用したことを明記すること、③関連法令とAcceptable Use Policyを守ること、です。
  アプリの画面やソースコードに特定の文言を表示せよという条項は、確認した範囲では見当たりませんでした。
  GUI・ログへの注意書き(`uma_app/uma_notice.py`)は、②③を利用者に伝えるための推奨対応です。
- 引用の依頼(モデルカードより): Wood, B. M. et al. *UMA: A Family of Universal Models for Atoms.*
  arXiv:2506.23971 (2025). https://arxiv.org/abs/2506.23971
- 配布対象外の地域(モデルカードの記載): 包括的な制裁対象の地域、および中国・ロシア・ベラルーシ。
- 契約の「Licensee」は、法的な同意能力のある年齢に達している方とされています。

## 公開前に確認が必要なもの(未確認)

| 名称 | 用途 | メモ |
|---|---|---|
| ASE | 構造の扱い・最適化アルゴリズム | 既存READMEには LGPL-2.1 とあります。配布元で最新の表記を確認してください |
| huggingface_hub | Hugging Faceへのログイン・ファイル取得 | ライセンス未確認 |
| py3Dmol / 3Dmol.js | 3D表示 | ライセンス未確認 |
| PyYAML、ipywidgets | 設定ファイル・GUI | ライセンス未確認 |
