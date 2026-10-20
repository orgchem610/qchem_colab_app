"""
uma_backend.uma_freq
----------------
UMAを使った振動数解析(調和近似)。

【方法】(ASEの Vibrations ではなく、次の理由で自前実装にしている)
    1. 力(UMAが返す-dE/dx)を、各原子の各方向に±δだけ動かして中心差分で微分し、
       Hessian(エネルギーの2次微分行列)を作る。
    2. 質量で重みづけし、並進3+回転3(直線分子は回転2)の方向を除いた空間で
       対角化する。これにより振動モードだけ(3N-6個。直線分子は3N-5個)が得られ、
       PySCF版(qchem_colab_app/pyscf_backend/freq.py)と同じ個数・同じ形式で結果を返せる。
       (ASEのVibrationsをそのまま使うと、並進・回転に由来するゼロ付近の
        モードが混ざり、虚振動の数え方が紛らわしくなるため)
    3. 数値計算の部分(compute_hessian_fd, harmonic_analysis, ZPEの計算)は、
       ASEにもUMAにも依存しない純粋なnumpyの関数で、common_backend/vibration.py にある
       (v0.2.2で、このファイルから移した)。数値の検証は tests/test_vibration.py が行う。
       このファイルは、UMAの計算器を使って力の関数を作り、それらを呼び出して結果をまとめる。

【単位】 座標[Å]、力[eV/Å]、Hessian[eV/Å^2]、質量[amu]、振動数[cm^-1]
虚振動は、PySCF版と同じく負の値で表す。

【結果の形式】(qchem_colab_app/pyscf_backend/freq.py の FrequencyResult と項目名をそろえている)
    frequencies_cm1 : 振動数のリスト(昇順。虚振動は負)
    normal_modes    : 各モードの原子変位ベクトル。shape (モード数, 原子数, 3)
    n_imaginary, thermo_summary, elapsed_seconds, warning_message
"""

import time

from qchem_colab_app.common_backend import energy, vibration


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
    hessian = vibration.compute_hessian_fd(forces_fn, atoms.get_positions(), delta, progress)
    freqs, modes = vibration.harmonic_analysis(atoms.get_masses(), atoms.get_positions(), hessian)

    result.frequencies_cm1 = [float(f) for f in freqs]
    result.normal_modes = modes
    result.n_imaginary = sum(1 for f in result.frequencies_cm1 if f < 0)

    zpe_ev = vibration.zero_point_energy_ev(result.frequencies_cm1)
    result.thermo_summary = {
        "ZPE_Hartree": zpe_ev / energy.HARTREE_TO_EV,
        "ZPE_kcal_per_mol": zpe_ev * energy.EV_TO_KCAL_MOL,
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
