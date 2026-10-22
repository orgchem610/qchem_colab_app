"""
qchem_colab_app.gui
-------------------
画面の層。ノートブックは、このパッケージの画面(pyscf_calc・uma_calc)を呼び出す。

    共通の画面部品(計算エンジンのパッケージをimportしない):
        parts.py          複合部品(構造ファイルの入力・エネルギーグラフと構造表示・振動・ダウンロード・電荷・スピン多重度)
        inputs.py         入力まわりの関数(アップロードされたファイルの取り出し・読み込みと検証・電荷の表示と読み取り)
        outputs.py        出力まわりの関数(ダウンロード名・ダウンロード項目)
        colab_widgets.py  ブラウザ側JavaScript ↔ Colabのコールバック(ドロップ領域・コールバック登録)
        energy_plot.py    クリックできるエネルギー収束グラフ(SVG)
        plot_common.py    構造・振動アニメーションの3D表示(py3Dmol)
    各画面(計算エンジンのパッケージを呼び出す):
        pyscf_calc.py     PySCF版の画面
        uma_calc.py       UMA版の画面
    (将来)builder.py      インプットファイル作成の画面

このファイルでは、何もimportしない(パッケージを読み込んだだけで、ipywidgetsが必要にならないようにするため)。
"""
