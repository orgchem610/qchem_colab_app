"""
qchem_colab_app
---------------
Colab用の量子化学計算アプリの、最上位パッケージ(名前空間)。

プロジェクト固有の名前のパッケージを1つだけ置き、その下に各パッケージを入れている。
`gui`・`common_backend` のような短い名前を、他のライブラリの同名のモジュールとの衝突
(どちらが優先されるかで、片方が壊れる)なしで使うため。

    gui/             画面(ipywidgets・ColabのJavaScript連携・3D表示・SVGグラフ。共通の部品と、各画面)
    common_backend/  バックエンドの共通部品(設定・バージョン・構造の読み込み・xyz出力・エネルギーの換算)
    pyscf_backend/   PySCF版の計算
    uma_backend/     UMA(機械学習ポテンシャル)版の計算

依存の向き(一方向): gui → pyscf_backend・uma_backend → common_backend
(pyscf_backend と uma_backend は、お互いをimportしない)。tests/test_package_layering.py で検査している。

このファイルでは、何もimportしない(パッケージを読み込んだだけで、重いライブラリが読み込まれないようにするため)。
"""
