"""
qchem_colab_app.pyscf_backend
-----------------------------
PySCFを計算エンジンとする、ab initio計算(構造最適化・振動数解析・分子軌道・原子電荷)のパッケージ。
uma_backend とは、お互いをimportしない。画面(ipywidgets)・ColabのJavaScript連携には依存しない。

config/ のYAMLの読み込み(load_yaml・PROJECT_ROOT・CONFIG_DIR)と __version__ は、common_backend の
config_loader・version を、このパッケージの名前でも使えるようにした別名(独自の関数は持たない)。
"""

from qchem_colab_app.common_backend.config_loader import CONFIG_DIR, PROJECT_ROOT, load_yaml  # noqa: F401
from qchem_colab_app.common_backend.version import __version__  # noqa: F401
