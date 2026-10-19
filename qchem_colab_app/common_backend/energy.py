"""
qchem_colab_app.common_backend.energy
-------------------------------------
エネルギーの単位換算と、相対エネルギー。画面にも計算エンジンにも依存しない純粋な関数で、
バックエンド(uma_backend/uma_report.py)と画面(gui/parts.py・gui/energy_plot.py)の
両方が使う。

(v0.2.2で、旧 common/energy_plot.py から分けた。クリックできるSVGグラフと、その目盛りの計算は、
画面の層の gui/energy_plot.py にある。)

    HARTREE_TO_KCAL_MOL     : エネルギーの単位換算(1 Hartree = 627.5094740631 kcal/mol)
    relative_energies_kcal(): 最終点を基準にした相対エネルギー[kcal/mol]
"""

import math

HARTREE_TO_KCAL_MOL = 627.5094740631


def relative_energies_kcal(energies_hartree):
    """最後の点(=最適化後の最安定点)を基準にした相対エネルギー[kcal/mol]のリスト。

    画面の構造表示ラベル(ステップ n: 相対エネルギー ...)・エネルギーグラフ・計算ログで、同じ基準を使う。
    """
    energies = [float(e) for e in energies_hartree]
    if not energies:
        raise ValueError("エネルギーが1点も記録されていないため、グラフを描画できません。")
    if not all(math.isfinite(e) for e in energies):
        raise ValueError("エネルギーに数値でない値(NaN/inf)が含まれているため、グラフを描画できません。")
    reference = energies[-1]
    return [(e - reference) * HARTREE_TO_KCAL_MOL for e in energies]
