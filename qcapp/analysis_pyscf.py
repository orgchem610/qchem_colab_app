"""
qcapp.analysis_pyscf
--------------------
収束済みのPySCFのSCFオブジェクト(mf)から、軌道・電荷の「情報」を取り出す関数群。

ここに置く関数は、描画(py3Dmol)にもウィジェット(ipywidgets)にも依存しない。
結果を3Dや表で表示する関数は、役割が違うため qcapp/visualizer_pyscf.py にある。
(PySCFのMole/SCFそのものに依存するため、common/ ではなく qcapp/ に置いている。)
"""

from collections import namedtuple

import numpy as np

# 軌道エネルギーの差がこの値(Hartree)以内なら、縮退している(同じエネルギー)とみなす
DEGENERACY_TOLERANCE_HARTREE = 1.0e-4

# 原子番号 1〜54(H〜Xe)の元素記号。軌道の数え上げ(valence_space_size)に使う。
_ELEMENT_SYMBOLS = (
    "H", "He",
    "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar",
    "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr",
    "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
    "In", "Sn", "Sb", "Te", "I", "Xe",
)

# 分子軌道の選択肢(orbital_choices の戻り値)
#   options       : [(表示名, 軌道番号), ...]。ドロップダウンの選択肢としてそのまま使える
#   default_index : 最初に選んでおく軌道番号(電子が入っている軌道のうち、最も高いもの)
#   open_shell    : 開殻(電子が1個だけ入っている軌道がある)かどうか
OrbitalChoices = namedtuple("OrbitalChoices", "options default_index open_shell")


def _core_and_valence_orbital_counts(symbol):
    """1原子あたりの(内殻軌道の数, 価電子殻の軌道の数)を返す。

    価電子殻の軌道は、最外殻のs軌道とp軌道(H・Heは1s軌道のみ)。遷移金属(GUIでは
    未対応)は、(n-1)d軌道も価電子殻に含める。Ga〜Kr・In〜Xeの(n-1)d軌道は、内殻とみなす。
    表にない記号は、内殻なし・価電子殻4軌道として扱う。
    """
    try:
        z = _ELEMENT_SYMBOLS.index(str(symbol).strip().capitalize()) + 1
    except ValueError:
        return 0, 4
    if z <= 2:
        return 0, 1          # H, He: 1s
    if z <= 10:
        return 1, 4          # Li〜Ne: 内殻1s、価電子殻2s2p
    if z <= 18:
        return 5, 4          # Na〜Ar: 内殻1s2s2p、価電子殻3s3p
    if z <= 20:
        return 9, 4          # K, Ca: 内殻はArと同じ、価電子殻4s4p
    if z <= 30:
        return 9, 9          # Sc〜Zn(遷移金属): 価電子殻4s3d4p
    if z <= 36:
        return 14, 4         # Ga〜Kr: 3dは内殻、価電子殻4s4p
    if z <= 38:
        return 18, 4         # Rb, Sr: 内殻はKrと同じ、価電子殻5s5p
    if z <= 48:
        return 18, 9         # Y〜Cd(遷移金属): 価電子殻5s4d5p
    return 23, 4             # In〜Xe: 4dは内殻、価電子殻5s5p


def _atom_symbols(mol):
    symbol_of = getattr(mol, "atom_pure_symbol", None) or mol.atom_symbol
    return [symbol_of(i) for i in range(mol.natm)]


def valence_space_size(mol):
    """分子全体の(内殻軌道の数, 価電子殻の軌道の数)を返す。各原子の値の合計。"""
    n_core = n_valence = 0
    for symbol in _atom_symbols(mol):
        core, valence = _core_and_valence_orbital_counts(symbol)
        n_core += core
        n_valence += valence
    return n_core, n_valence


def _occupations(mf):
    """SCF結果から、軌道ごとの(総電子数, αスピンの電子数, αスピンの軌道エネルギー)を取り出す。

    閉殻(RHF/RKS)は1次元の配列、開殻(UHF/UKS)はα・βの2行の配列で保持されている。
    開殻では、αスピンの軌道を基準に扱う(軌道の表示もαスピンの軌道)。
    """
    occ = np.asarray(mf.mo_occ, dtype=float)
    energy = np.asarray(mf.mo_energy, dtype=float)
    if occ.ndim == 2:
        occ_alpha = occ[0]
        occ_total = occ[0] + occ[1]
    else:
        occ_total = occ
        occ_alpha = (occ > 0).astype(float)
    if energy.ndim == 2:
        energy = energy[0]
    return occ_total, occ_alpha, energy


def orbital_choices(mol, mf, degeneracy_tolerance=DEGENERACY_TOLERANCE_HARTREE):
    """分子軌道の選択肢(表示名と軌道番号)と、最初に選んでおく軌道を作る。

    選択肢に入れる軌道:
        軌道0番から、「内殻軌道+価電子殻の軌道」の数(valence_space_size)に相当する
        番号まで。つまり、電子が入っているすべての軌道と、各原子の最外殻だけから
        できる空軌道(の数だけ、エネルギーの低い順)。電子が入っている軌道が
        それより多い場合は、電子が入っているすべての軌道まで広げる。
        (最外殻の軌道かどうかは、軌道の数で近似している。大きな基底関数・拡散関数を
        含む基底では、エネルギーの低い空軌道に最外殻以外の軌道が混ざることがある。)

    表示名は「軌道n番」を基本とし、次の場合だけ末尾に付ける。
        閉殻: 最高被占軌道(HOMO)は「(HOMO)」、最低空軌道(LUMO)は「(LUMO)」。
              エネルギーが縮退している(差が degeneracy_tolerance 以内の)軌道には、すべてに付ける。
        開殻: 電子が1個だけ入っている軌道は、すべて「(SOMO)」。HOMO・LUMOは付けない。

    最初に選んでおく軌道は、電子が入っている(αスピンの)軌道のうち、最も番号の大きいもの。
    """
    occ_total, occ_alpha, energy = _occupations(mf)
    n_mo = len(occ_total)

    occupied = [i for i in range(n_mo) if occ_alpha[i] > 0]
    default_index = max(occupied) if occupied else 0

    somo = {i for i in range(n_mo) if abs(occ_total[i] - 1.0) < 1e-6}
    open_shell = bool(somo)

    homo_set, lumo_set = set(), set()
    if not open_shell:
        filled = [i for i in range(n_mo) if occ_total[i] > 0]
        empty = [i for i in range(n_mo) if occ_total[i] <= 0]
        if filled:
            homo = max(filled)
            homo_set = {i for i in filled if abs(energy[i] - energy[homo]) <= degeneracy_tolerance}
        if empty:
            lumo = min(empty)
            lumo_set = {i for i in empty if abs(energy[i] - energy[lumo]) <= degeneracy_tolerance}

    n_core, n_valence = valence_space_size(mol)
    upper = max(n_core + n_valence, default_index + 1, max(lumo_set) + 1 if lumo_set else 0)
    upper = min(upper, n_mo)

    options = []
    for i in range(upper):
        label = f"軌道{i}番"
        if open_shell:
            if i in somo:
                label += "(SOMO)"
        elif i in homo_set:
            label += "(HOMO)"
        elif i in lumo_set:
            label += "(LUMO)"
        options.append((label, i))
    return OrbitalChoices(options, default_index, open_shell)


def compute_mulliken_charges(mol, mf):
    """Mulliken電荷を原子ごとに計算する。戻り値は [(元素記号, 電荷), ...]。"""
    _, atomic_charges = mf.mulliken_pop(verbose=0)
    symbols = [mol.atom_symbol(i) for i in range(mol.natm)]
    return list(zip(symbols, [float(c) for c in atomic_charges]))
