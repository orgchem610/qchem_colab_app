"""
tests/real_molecules.py
-----------------------
単体テストで、外部ライブラリ(PySCF・ASE・py3Dmol・ipywidgets・torch・fairchem)の実物を使うための補助。

    - HAS_PYSCF など : そのライブラリがインストールされているか。入っていない環境では、
                       @unittest.skipUnless(HAS_...) で、そのテストだけをスキップする。
    - 小さな分子・SCFの結果 : 水・メチルラジカル・酸素(三重項)・エタノール陽イオン・ベンゼン・直線の水。
                       どれも1秒未満で終わる。複数のテストで使い回すため、最初に使ったときに1回だけ計算する。
                       テストの中で値を書き換えるときは、modified_copy() で複製してから書き換える
                       (使い回す結果そのものは、書き換えない)。

PySCFは、関数の中でimportする。入っていない環境でも、このモジュール自体は読み込める。
"""

import copy
import functools
import importlib.util
import math

import numpy as np


def _installed(name):
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


HAS_PYSCF = _installed("pyscf")
HAS_GEOMETRIC = _installed("geometric")
HAS_ASE = _installed("ase")
HAS_PY3DMOL = _installed("py3Dmol")
HAS_IPYWIDGETS = _installed("ipywidgets")
HAS_TORCH = _installed("torch")
HAS_FAIRCHEM = _installed("fairchem")

# 構造(Å)。atom の書式は pyscf.gto.Mole.atom の文字列
WATER = "O 0 0 0.1173; H 0 0.7572 -0.4692; H 0 -0.7572 -0.4692"
METHYL = "C 0 0 0; H 1.079 0 0; H -0.5395 0.9344 0; H -0.5395 -0.9344 0"
OXYGEN = "O 0 0 0; O 0 0 1.21"
ETHANOL = ("C 1.1879 -0.3829 0; C 0 0.5526 0; O -1.1867 -0.2472 0; H -1.9237 0.3850 0; "
           "H 2.0985 0.2306 0; H 1.1184 -1.0093 0.8869; H 1.1184 -1.0093 -0.8869; "
           "H -0.0227 1.1812 0.8852; H -0.0227 1.1812 -0.8852")
BENZENE = "; ".join(
    f"{symbol} {radius * math.cos(math.radians(60 * k)):.6f} {radius * math.sin(math.radians(60 * k)):.6f} 0"
    for k in range(6) for symbol, radius in (("C", 1.39), ("H", 2.48)))
# HF/STO-3G の平衡構造に近い水(O-H 0.9894 Å, H-O-H 100°)。振動数が、すべて実数になる
_OH = 0.9894
WATER_EQUILIBRIUM = (f"O 0 0 0; H 0 {_OH * math.sin(math.radians(50)):.6f} {_OH * math.cos(math.radians(50)):.6f}; "
                     f"H 0 {-_OH * math.sin(math.radians(50)):.6f} {_OH * math.cos(math.radians(50)):.6f}")
# 直線の水。曲がる向きの振動が、2つとも虚振動になる(鞍点)
WATER_LINEAR = "O 0 0 0; H 0 0 0.99; H 0 0 -0.99"


def build_mole(atom, basis="6-31g", charge=0, spin=0):
    """pyscf.gto.Mole を作る(計算はしない)。"""
    from pyscf import gto
    return gto.M(atom=atom, basis=basis, charge=charge, spin=spin, verbose=0)


def atom_mole(symbol, basis="sto-3g"):
    """原子1個の Mole。電子の数が奇数なら、スピンを1にする。"""
    from pyscf import gto
    return build_mole(f"{symbol} 0 0 0", basis=basis, spin=gto.charge(symbol) % 2)


def run_scf(mol, method="RHF", conv_tol=1e-10):
    """指定した方法(RHF・UHF・ROHF)でSCFを実行し、収束した結果を返す。"""
    from pyscf import scf
    mf = getattr(scf, method)(mol)
    mf.verbose = 0
    mf.conv_tol = conv_tol
    mf.kernel()
    assert mf.converged, f"{method} が収束しませんでした"
    return mf


@functools.lru_cache(maxsize=None)
def water_rhf():
    """水 RHF/6-31G。軌道13個、電子の入った軌道5個。"""
    return run_scf(build_mole(WATER))


@functools.lru_cache(maxsize=None)
def methyl_uhf():
    """メチルラジカル UHF/6-31G。α電子5個・β電子4個。"""
    return run_scf(build_mole(METHYL, spin=1), "UHF")


@functools.lru_cache(maxsize=None)
def methyl_rohf():
    """メチルラジカル ROHF/6-31G。占有数は1次元の配列で、電子が1個の軌道だけ占有数が1。"""
    return run_scf(build_mole(METHYL, spin=1), "ROHF")


@functools.lru_cache(maxsize=None)
def oxygen_triplet_uhf():
    """酸素分子(三重項) UHF/6-31G。α電子9個・β電子7個。"""
    return run_scf(build_mole(OXYGEN, spin=2), "UHF")


@functools.lru_cache(maxsize=None)
def ethanol_cation_uhf():
    """エタノール陽イオン UHF/6-31G。軌道39個、α電子13個・β電子12個。"""
    return run_scf(build_mole(ETHANOL, charge=1, spin=1), "UHF")


@functools.lru_cache(maxsize=None)
def benzene_rhf():
    """ベンゼン RHF/STO-3G。HOMO・LUMOが、どちらも2重に縮退している。"""
    return run_scf(build_mole(BENZENE, basis="sto-3g"))


@functools.lru_cache(maxsize=None)
def water_equilibrium_rhf():
    """平衡構造に近い水 RHF/STO-3G(Hessianの精度のため、収束条件を厳しくしてある)。"""
    return run_scf(build_mole(WATER_EQUILIBRIUM, basis="sto-3g"), conv_tol=1e-12)


@functools.lru_cache(maxsize=None)
def linear_water_rhf():
    """直線の水 RHF/STO-3G(鞍点。振動数解析で、虚振動が2個になる)。"""
    return run_scf(build_mole(WATER_LINEAR, basis="sto-3g"), conv_tol=1e-12)


def modified_copy(mf, **attributes):
    """SCFの結果を浅く複製し、指定した属性だけ書き換えて返す(使い回す結果そのものは、書き換えない)。"""
    clone = copy.copy(mf)
    for name, value in attributes.items():
        setattr(clone, name, value)
    return clone


def hypothetical_rhf(mol, n_occupied, n_mo, energies=None):
    """計算していない RHF オブジェクトに、仮の軌道占有数・軌道エネルギー(Hartree)を入れる。

    実際には起こらない軌道の数(軌道の上限・価電子殻より多い占有軌道)の確認用。
    energies を省略すると、0, 1, 2, ... の等間隔にする(縮退しない)。
    """
    from pyscf import scf
    mf = scf.RHF(mol)
    mf.mo_occ = np.array([2.0] * n_occupied + [0.0] * (n_mo - n_occupied))
    mf.mo_energy = np.arange(n_mo, dtype=float) if energies is None else np.array(energies, dtype=float)
    return mf
