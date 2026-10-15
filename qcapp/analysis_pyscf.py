"""
qcapp.analysis_pyscf
--------------------
収束済みのPySCFのSCFオブジェクト(mf)から、軌道・電荷の「情報」を取り出す関数群。

ここに置く関数は、描画(py3Dmol)にもウィジェット(ipywidgets)にも依存しない。
結果を3Dや表で表示する関数は、役割が違うため qcapp/visualizer_pyscf.py にある。
(PySCFのMole/SCFそのものに依存するため、common/ ではなく qcapp/ に置いている。)
"""

import numpy as np


def get_homo_lumo_indices(mf):
    """収束済みSCFオブジェクトからHOMO/LUMOの軌道インデックスを求める(閉殻を想定)。"""
    mo_occ = mf.mo_occ
    if isinstance(mo_occ, (tuple, list)):
        mo_occ = mo_occ[0]  # UHFの場合はひとまずalphaチャンネルを使う
    occ_indices = np.nonzero(np.asarray(mo_occ) > 0)[0]
    homo_idx = int(occ_indices[-1]) if len(occ_indices) else 0
    lumo_idx = homo_idx + 1
    return homo_idx, lumo_idx


def homo_lumo_window(mf, half_width=2):
    """HOMOを中心に前後 half_width 個ずつの軌道インデックスとラベルを作る。

    戻り値は ([(ラベル, 軌道番号), ...], HOMOの軌道番号)。分子軌道のドロップダウンの
    選択肢として、そのまま使える形にしてある。
    """
    homo_idx, lumo_idx = get_homo_lumo_indices(mf)
    n_mo = mf.mo_energy.shape[-1] if hasattr(mf.mo_energy, "shape") else len(mf.mo_energy)

    options = []
    for i in range(homo_idx - half_width + 1, lumo_idx + half_width):
        if i < 0 or i >= n_mo:
            continue
        if i == homo_idx:
            label = f"HOMO (軌道{i}番)"
        elif i == lumo_idx:
            label = f"LUMO (軌道{i}番)"
        elif i < homo_idx:
            label = f"HOMO-{homo_idx - i} (軌道{i}番)"
        else:
            label = f"LUMO+{i - lumo_idx} (軌道{i}番)"
        options.append((label, i))
    return options, homo_idx


def compute_mulliken_charges(mol, mf):
    """Mulliken電荷を原子ごとに計算する。戻り値は [(元素記号, 電荷), ...]。"""
    _, atomic_charges = mf.mulliken_pop(verbose=0)
    symbols = [mol.atom_symbol(i) for i in range(mol.natm)]
    return list(zip(symbols, [float(c) for c in atomic_charges]))
