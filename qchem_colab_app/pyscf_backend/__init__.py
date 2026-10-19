"""
pyscf_backend: PySCFを計算エンジンとするab initio量子化学計算のコアパッケージ

このパッケージは、ColabApp.ipynb から呼び出される、PySCFに固有の実処理を
まとめたものです。ノートブック自体にはロジックを書かず、ここに切り出すことで
    - 過去バージョンとの差分をGitで追いやすくする
    - 単体でのテスト・デバッグをしやすくする
    - 計算手法・基底関数の追加を設定ファイル(config/*.yaml)の編集だけで
      完結させる(ただし、構造最適化以外の新しい「計算目的」自体の追加には
      新しいコードが必要。詳細はREADME.md参照)
ことを狙っています。

計算エンジン(PySCF)に依存しない汎用コード(構造の読み込み・検証・xyz出力・
可視化の基本部分)は、このパッケージの外、`qchem_colab_app/common_backend/`パッケージに
分離しています(将来追加予定のUMA版アプリとも共有するため)。

バージョン情報・設定ファイルの読み込み:
  __version__ と load_yaml は、common_backend/ にある共通のものを、このパッケージの名前でも
  使えるようにした別名です(common_backend/version.py・common_backend/config.py)。
"""

from qchem_colab_app.common_backend.config import CONFIG_DIR, PROJECT_ROOT, load_yaml  # noqa: F401
from qchem_colab_app.common_backend.version import __version__  # noqa: F401
