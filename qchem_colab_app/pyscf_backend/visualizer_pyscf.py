"""
pyscf_backend.visualizer_pyscf
------------------------------
PySCFのMole/SCFオブジェクトに直接依存する可視化(分子軌道の等値面)。

分子軌道(cubeファイル)は、PySCF固有のデータ構造(Mole・SCFの軌道係数)から作るため、ここに置いている。
HOMO/LUMOの軌道番号やMulliken電荷の値を求める「解析」の関数は、描画とは役割が違うため
qchem_colab_app/pyscf_backend/analysis_pyscf.py に分けてある。

原子電荷の色分け表示・電荷の表は、PySCFのオブジェクトに依存しない(元素記号・座標・電荷の値だけで描ける)ため、
v0.2.2で、画面の層の gui/plot_common.py(render_charges・atomic_charges_table_html など)に移した。
cubeファイルの値の最大絶対値の読み取りも、PySCFに依存しないため、common_backend/cube.py に移した。
"""

import os
import tempfile

import numpy as np

from qchem_colab_app.common_backend import cube


def _mo_coeff_for_cube(mf, orbital_index):
    mo_coeff = mf.mo_coeff
    # 開殻(UHF/UKS)では、αとβの軌道係数をまとめた(2, 基底関数, 軌道)の3次元配列(または2つの配列の
    # 組)になっている。軌道の選択肢(analysis_pyscf.orbital_choices)はαスピンの軌道なので、αを使う。
    if isinstance(mo_coeff, (tuple, list)) or getattr(mo_coeff, "ndim", 2) == 3:
        mo_coeff = mo_coeff[0]
    return mo_coeff[:, orbital_index]


def render_orbital(mol, mf, orbital_index, isoval_fraction=0.12, width=500, height=400):
    """指定した分子軌道(例: HOMO, LUMO)をcubeファイル経由で等値面表示する。

    isoval(等値面の閾値)は固定値ではなく、その軌道自身の格子点上での
    最大絶対値に対する割合(既定12%)として動的に決めている。HOMOとLUMOでは
    振幅の広がり方(ピーク値の大きさ)が異なることが多く、固定のisoval
    (例: 0.02)だとLUMO側が分子全体を覆うように大きく表示されすぎることが
    あったため、この方式に変更した。
    """
    import py3Dmol
    from pyscf.tools import cubegen

    tmpdir = tempfile.mkdtemp()
    cube_path = os.path.join(tmpdir, "orbital.cube")
    grid = cubegen.orbital(mol, cube_path, _mo_coeff_for_cube(mf, orbital_index))
    if grid is not None:
        max_abs = float(np.max(np.abs(np.asarray(grid))))
    else:
        max_abs = cube.max_abs_value(cube_path)
    isoval = max(max_abs * isoval_fraction, 1e-4)

    with open(cube_path, "r", encoding="utf-8") as f:
        cube_data = f.read()

    view = py3Dmol.view(width=width, height=height)
    view.addModel(cube_data, "cube")
    view.setStyle({"stick": {}, "sphere": {"scale": 0.3}})
    view.addVolumetricData(cube_data, "cube", {"isoval": isoval, "color": "blue", "opacity": 0.75})
    view.addVolumetricData(cube_data, "cube", {"isoval": -isoval, "color": "red", "opacity": 0.75})
    view.zoomTo()
    return view
