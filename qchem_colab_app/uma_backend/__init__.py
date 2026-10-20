"""
qchem_colab_app.uma_backend
---------------------------
UMA(機械学習ポテンシャル)を計算エンジンとする、構造最適化・振動数解析のパッケージ。
pyscf_backend には依存しない(PySCFがインストールされていない環境でも動くようにするため)。
画面(ipywidgets)・ColabのJavaScript連携には依存しない。

このファイルは説明だけで、何もimportしない(他のモジュールの名前を別名として公開しない)。
config/ のYAMLの読み込みは common_backend.config_loader、バージョンは common_backend.version を、
使う側が直接importする。
"""
