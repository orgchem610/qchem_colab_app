"""
uma_backend: 機械学習ポテンシャルUMAを計算エンジンとする構造最適化・振動数解析のコアパッケージ

このパッケージは、ColabApp_UMA.ipynb(+ ルート直下の gui/uma_calc.py)から呼び出される、
UMA(ASE + fairchem-core)に固有の処理をまとめたものです。

【依存関係の方針】(README.md「将来的な構成: UMA利用版」「パッケージ構成」参照)
    - 計算エンジンに依存しない共通部品は、common_backend/ から使う。
    - PySCF専用の qchem_colab_app/pyscf_backend/ には一切依存しない(PySCFがインストールされていない
      UMA用の環境でも動くようにするため)。設定ファイルの読み込み関数とバージョン番号は、
      common_backend/ にある共通のもの(config.py・version.py)を、このパッケージの
      名前でも使えるようにしている。
    - 設定ファイルは、PySCF版と同じ config/ ディレクトリに、uma_ で始まる
      別名のファイルとして置いている(PySCF版の設定には影響しない)。

【バージョン番号】
    __version__ はリポジトリ全体のリリース番号(Gitタグ)で、common_backend/version.py に1か所だけ
    書いてあります。更新するときは、そのファイルを編集してください。
"""

from qchem_colab_app.common_backend.config import CONFIG_DIR, PROJECT_ROOT, load_yaml  # noqa: F401
from qchem_colab_app.common_backend.version import __version__  # noqa: F401
