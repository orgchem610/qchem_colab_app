# サードパーティのライセンス(UMA版 ColabApp_UMA.ipynb)

UMA版が利用する外部のソフトウェア・データと、そのライセンス等の一次情報へのリンクです。
(確認日: 2026-10-10。最新の内容は、各リンク先をご確認ください。)

| 名称 | 用途 | ライセンス | 一次情報 |
|---|---|---|---|
| UMAの学習済みモデル(Hugging Face `facebook/UMA`) | 計算エンジン本体(重み) | FAIR Chemistry License v1 | https://huggingface.co/facebook/UMA/blob/main/LICENSE |
| fairchem-core | UMAの推論(コード) | MIT License | https://github.com/facebookresearch/fairchem |

## UMAについて

- Acceptable Use Policy・モデルカード: https://huggingface.co/facebook/UMA
- 引用: UMAを利用した成果を発表する場合は、以下の論文を引用してください(モデルカードの記載)。
  Wood, B. M. et al. *UMA: A Family of Universal Models for Atoms.* arXiv:2506.23971 (2025).
  https://arxiv.org/abs/2506.23971
- このリポジトリは、UMAの学習済みモデルを同梱も再配布もしません。各利用者が、ご自身のHugging Faceの
  アカウントでアクセスを申請し、Colab上で直接ダウンロードします(`uma_backend/uma_engine.py`)。

## そのほかのライブラリ

ASE、huggingface_hub、py3Dmol、PyYAMLなど、このリポジトリが利用するそのほかのライブラリの
ライセンスは、それぞれの配布元をご確認ください。
