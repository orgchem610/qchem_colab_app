"""
uma_app.uma_freq
----------------
UMAを使った振動数解析(調和近似)。

【方法】(README.md設計案の「ASE Vibrationsによる数値Hessian」を、次の理由で自前実装にした)
    1. 力(UMAが返す-dE/dx)を、各原子の各方向に±δだけ動かして中心差分で微分し、
       Hessian(エネルギーの2次微分行列)を作る。
    2. 質量で重みづけし、並進3+回転3(直線分子は回転2)の方向を除いた空間で
       対角化する。これにより振動モードだけ(3N-6個。直線分子は3N-5個)が得られ、
       PySCF版(qcapp/freq.py)と同じ個数・同じ形式で結果を返せる。
       (ASEのVibrationsをそのまま使うと、並進・回転に由来するゼロ付近の
        モードが混ざり、虚振動の数え方が紛らわしくなるため)
    3. 数値計算の部分(compute_hessian_fd, harmonic_analysis)は、ASEにもUMAにも
       依存しない純粋なnumpyの関数にしてあり、単体テストで検証できる。
       tests/test_uma_freq.py では、解析解(バネのモデル)との照合に加えて、ASE付属の簡易ポテンシャル
       (EMT)を使い、ASEの Vibrations(力の中心差分)・VibrationsData(Hessianからの振動数)と
       振動数が一致することも確認している(ASEが入っていない環境では、この照合だけスキップされる)。

【単位】 座標[Å]、力[eV/Å]、Hessian[eV/Å^2]、質量[amu]、振動数[cm^-1]
虚振動は、PySCF版と同じく負の値で表す。

【結果の形式】(qcapp/freq.py の FrequencyResult と項目名をそろえている)
    frequencies_cm1 : 振動数のリスト(昇順。虚振動は負)
    normal_modes    : 各モードの原子変位ベクトル。shape (モード数, 原子数, 3)
    n_imaginary, thermo_summary, elapsed_seconds, warning_message
"""

import math
import time

import numpy as np

# 物理定数(CODATA 2018)
_EV_J = 1.602176634e-19
_AMU_KG = 1.66053906660e-27
_ANGSTROM_M = 1.0e-10
_C_CM_PER_S = 2.99792458e10
_HC_EV_CM = 1.239841984e-4                 # h*c [eV cm]
_HARTREE_PER_EV = 1.0 / 27.211386245988
_KCAL_PER_EV = 23.060548012069496

# 質量重み付きHessianの固有値 [eV/(Å^2 amu)] -> 角振動数の2乗 [s^-2]
_LAMBDA_TO_OMEGA2 = _EV_J / (_AMU_KG * _ANGSTROM_M ** 2)
_OMEGA_TO_CM1 = 1.0 / (2.0 * math.pi * _C_CM_PER_S)


def compute_hessian_fd(forces_fn, positions, delta=0.01, progress=None):
    """力の中心差分でHessian [eV/Å^2] を作る。shape (3N, 3N)。

    forces_fn(positions) は、座標 (N,3)[Å] を受け取り、力 (N,3)[eV/Å] を返す関数。
    H[a, b] = -dF_a/dx_b を、 -(F(x_b+δ) - F(x_b-δ)) / (2δ) で近似する。
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


class FrequencyResult:
    def __init__(self):
        self.frequencies_cm1 = []
        self.normal_modes = None
        self.n_imaginary = 0
        self.thermo_summary = {}
        self.elapsed_seconds = 0.0
        self.warning_message = ""


def run_frequency_analysis(atoms, calculator, freq_cfg, progress=None):
    """最適化後の構造(ASE Atoms)の振動数解析を行う。

    Parameters
    ----------
    atoms : charge/spinがinfoに設定済みの、最適化後のASE Atoms
    calculator : uma_engine.make_calculator()の戻り値
    freq_cfg : config/uma_defaults.yaml の frequency 節
    progress : progress(完了した原子数, 全原子数) を呼ぶ関数(省略可)
    """
    result = FrequencyResult()
    t0 = time.perf_counter()

    if len(atoms) < 2:
        result.warning_message = "原子が1個だけの構造には、振動モードがありません。"
        result.elapsed_seconds = time.perf_counter() - t0
        return result

    work = atoms.copy()
    work.calc = calculator

    def forces_fn(positions):
        work.set_positions(positions)
        return work.get_forces()

    delta = float(freq_cfg.get("displacement_angstrom", 0.01))
    hessian = compute_hessian_fd(forces_fn, atoms.get_positions(), delta, progress)
    freqs, modes = harmonic_analysis(atoms.get_masses(), atoms.get_positions(), hessian)

    result.frequencies_cm1 = [float(f) for f in freqs]
    result.normal_modes = modes
    result.n_imaginary = sum(1 for f in result.frequencies_cm1 if f < 0)

    zpe_ev = 0.5 * sum(f for f in result.frequencies_cm1 if f > 0) * _HC_EV_CM
    result.thermo_summary = {
        "ZPE_Hartree": zpe_ev * _HARTREE_PER_EV,
        "ZPE_kcal_per_mol": zpe_ev * _KCAL_PER_EV,
    }

    if result.n_imaginary > 0:
        imaginary = [f for f in result.frequencies_cm1 if f < 0]
        small = float(freq_cfg.get("small_imaginary_cm1", 50))
        listing = ", ".join(f"{f:.1f}" for f in imaginary)
        if all(abs(f) <= small for f in imaginary):
            result.warning_message = (
                f"虚振動が{result.n_imaginary}個検出されました({listing} cm⁻¹)。"
                f"いずれも絶対値が{small:.0f} cm⁻¹以内と小さいため、最適化の収束不足や"
                "数値誤差による見かけの虚振動の可能性があります。"
                "config/uma_defaults.yaml の fmax_ev_per_angstrom を小さくして"
                "再実行すると解消することがあります。")
        else:
            result.warning_message = (
                f"虚振動が{result.n_imaginary}個検出されました({listing} cm⁻¹)。"
                "この構造は真の極小構造(エネルギー最小点)ではない可能性があります。"
                "初期構造を見直す、収束条件を厳しくして再実行する、といった対応を"
                "ご検討ください。")

    result.elapsed_seconds = time.perf_counter() - t0
    return result
