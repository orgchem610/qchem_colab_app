"""
qchem_colab_app.pyscf_backend
-----------------------------
PySCFを計算エンジンとする、ab initio計算(構造最適化・振動数解析・分子軌道・原子電荷)のパッケージ。
uma_backend とは、お互いをimportしない。画面(ipywidgets)・ColabのJavaScript連携には依存しない。

このファイルは説明だけで、何もimportしない(他のモジュールの名前を別名として公開しない)。
config/ のYAMLの読み込みは common_backend.config_loader、バージョンは common_backend.version を、
使う側が直接importする。
"""
