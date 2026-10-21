"""
common_backend.vibration
------------------------
振動数解析の、計算エンジンに依存しない数値計算(純粋なnumpy)。

    - compute_hessian_fd()     : 力の中心差分から、Hessian(エネルギーの2次微分行列)を作る
    - harmonic_analysis()      : Hessianから、並進・回転を除いた調和振動数と基準振動モードを求める
    - zero_point_energy_ev()   : 振動数からゼロ点エネルギー(ZPE)を求める
    - FrequencyResult          : 振動数解析の結果を入れる入れ物(PySCF版・UMA版の共通の親)

ASEにも、UMAにも、PySCFにも依存しない。数値計算の関数は、現在は uma_backend/uma_freq.py だけが使う
(PySCF版は、PySCF自身の解析的Hessianと pyscf.hessian.thermo を使う)。
FrequencyResult は、両方のエンジンが使う。UMA版はそのまま使い、PySCF版は子クラス
(pyscf_backend/freq.py の FrequencyResult)で、PySCFが求める熱力学量(自由エネルギー・温度)の項目を足す。
画面(gui/parts.py の VibrationViewer)は frequencies_cm1 と normal_modes だけを使う。
数値の正しさは、tests/test_vibration.py で、バネのモデルの解析解・同位体効果・回転不変性、
およびASEの Vibrations・VibrationsData との照合で確認している。

(v0.2.2で、uma_backend/uma_freq.py から、この共通部品に移した。)

【単位】 座標[Å]、力[eV/Å]、Hessian[eV/Å^2]、質量[amu]、振動数[cm^-1]、ZPE[eV]
虚振動は、負の値で表す。
"""

import math

import numpy as np

from qchem_colab_app.common_backend import energy

# 物理定数(CODATA 2018)
_EV_J = 1.602176634e-19
_AMU_KG = 1.66053906660e-27
_ANGSTROM_M = 1.0e-10
_C_CM_PER_S = 2.99792458e10
_HC_EV_CM = 1.239841984e-4                 # h*c [eV cm]

# 質量重み付きHessianの固有値 [eV/(Å^2 amu)] -> 角振動数の2乗 [s^-2]
_LAMBDA_TO_OMEGA2 = _EV_J / (_AMU_KG * _ANGSTROM_M ** 2)
_OMEGA_TO_CM1 = 1.0 / (2.0 * math.pi * _C_CM_PER_S)


def compute_hessian_fd(forces_fn, positions, delta=0.01, progress=None):
    """力の中心差分でHessian [eV/Å^2] を作る。shape (3N, 3N)。

    forces_fn(positions) は、座標 (N,3)[Å] を受け取り、力 (N,3)[eV/Å] を返す関数。
    H[a, b] = -dF_a/dx_b を、 -(F(x_b+δ) - F(x_b-δ)) / (2δ) で近似する。
    progress(完了した原子数, 全原子数) を渡すと、原子ごとに呼ぶ。
    """
    pos0 = np.array(positions, dtype=float)
    n = len(pos0)
    hessian = np.zeros((3 * n, 3 * n))
    for i in range(n):
        for k in range(3):
            plus = pos0.copy()
            plus[i, k] += delta
            minus = pos0.copy()
            minus[i, k] -= delta
            f_plus = np.asarray(forces_fn(plus), dtype=float).reshape(-1)
            f_minus = np.asarray(forces_fn(minus), dtype=float).reshape(-1)
            hessian[:, 3 * i + k] = -(f_plus - f_minus) / (2.0 * delta)
        if progress is not None:
            progress(i + 1, n)
    return 0.5 * (hessian + hessian.T)


def harmonic_analysis(masses, positions, hessian, rank_tol=1e-8):
    """Hessianから、調和近似の振動数[cm^-1]と基準振動モードを求める。

    Returns
    -------
    (frequencies_cm1, normal_modes)
        frequencies_cm1 : shape (n_modes,) 昇順。虚振動は負。
        normal_modes    : shape (n_modes, N, 3)。各モードの原子変位(長さ1に規格化)。
    原子が1個だけのときは、振動モードがないため空の結果を返す。
    """
    masses = np.asarray(masses, dtype=float)
    pos = np.asarray(positions, dtype=float)
    n = len(masses)
    if n < 2:
        return np.zeros(0), np.zeros((0, n, 3))

    sqrt_m = np.repeat(np.sqrt(masses), 3)
    h_mw = np.asarray(hessian, dtype=float) / np.outer(sqrt_m, sqrt_m)
    h_mw = 0.5 * (h_mw + h_mw.T)

    # 並進3方向・回転3方向(質量重み付き座標での表現)
    com = (masses[:, None] * pos).sum(axis=0) / masses.sum()
    rel = pos - com
    sqrt_m_atoms = np.sqrt(masses)[:, None]
    vectors = []
    for k in range(3):
        t = np.zeros((n, 3))
        t[:, k] = np.sqrt(masses)
        vectors.append(t.ravel())
    for k in range(3):
        axis = np.zeros(3)
        axis[k] = 1.0
        vectors.append((np.cross(axis, rel) * sqrt_m_atoms).ravel())
    basis = np.array(vectors).T                       # shape (3N, 6)

    # 並進・回転の空間の正規直交基底を求め、その補空間(=振動の空間)を取り出す。
    # 直線分子では回転が2つしか独立でないため、特異値でランクを判定する。
    u, s, _ = np.linalg.svd(basis, full_matrices=True)
    rank = int(np.sum(s > rank_tol * s.max()))
    complement = u[:, rank:]                          # shape (3N, 3N-rank)

    h_internal = complement.T @ h_mw @ complement
    h_internal = 0.5 * (h_internal + h_internal.T)
    eigenvalues, eigenvectors = np.linalg.eigh(h_internal)

    modes_mw = complement @ eigenvectors              # 質量重み付き座標でのモード
    displacements = modes_mw / sqrt_m[:, None]        # 元の(デカルト)座標での変位
    displacements = displacements / np.linalg.norm(displacements, axis=0)

    frequencies = np.sign(eigenvalues) * np.sqrt(np.abs(eigenvalues) * _LAMBDA_TO_OMEGA2) * _OMEGA_TO_CM1
    return frequencies, displacements.T.reshape(-1, n, 3)


def zero_point_energy_ev(frequencies_cm1):
    """調和振動数[cm^-1]のリストから、ゼロ点エネルギー(ZPE)[eV]を求める。

    ZPE = (1/2) Σ hν。虚振動(負の値)は、含めない。
    Hartree・kcal/molへの換算は、common_backend.energy の係数を使う。
    """
    return 0.5 * sum(f for f in frequencies_cm1 if f > 0) * _HC_EV_CM


class FrequencyResult:
    """振動数解析の結果。PySCF版・UMA版で共通の項目を持つ(エンジン固有の項目は、子クラスで足す)。

    frequencies_cm1 : 振動数 [cm^-1] のリスト。虚振動は負の値
    normal_modes    : 基準振動モードの原子変位。shape (モード数, 原子数, 3)。求めていなければ None
    zpe_hartree     : ゼロ点エネルギー [Hartree]。求めていなければ None
    elapsed_seconds : 所要時間 [秒]
    warning_message : 利用者に示す注意文(なければ空文字)
    n_imaginary     : 虚振動の数(frequencies_cm1 から求める)
    zpe_kcal_per_mol: ゼロ点エネルギー [kcal/mol](zpe_hartree から求める)
    """

    def __init__(self):
        self.frequencies_cm1 = []
        self.normal_modes = None
        self.zpe_hartree = None
        self.elapsed_seconds = 0.0
        self.warning_message = ""

    @property
    def n_imaginary(self):
        return sum(1 for f in self.frequencies_cm1 if f < 0)

    @property
    def zpe_kcal_per_mol(self):
        if self.zpe_hartree is None:
            return None
        return self.zpe_hartree * energy.HARTREE_TO_KCAL_MOL
