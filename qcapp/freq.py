"""
qcapp.freq
----------
最適化後の構造に対して Hessian(エネルギーの2次微分)を計算し、
調和振動数解析(振動数・基準振動モード・簡単な熱力学量)を行うモジュール。

【GPUについての方針】
GPU4PySCFのHessian(2次微分)機能はまだ十分な検証ができていないため、
本モジュールは常にCPU版PySCFのSCFオブジェクトを前提とする
(構造最適化をGPUで行ったかどうかに関わらず、振動数計算はCPUで行う)。
振動数計算は最適化ループのように何百回も繰り返す処理ではなく、
収束した1つの構造に対して1回だけ行う処理なので、CPU実行による
全体所要時間への影響は相対的に小さいと考えられる。

【実装上の注意】
pyscf.hessian.thermo.harmonic_analysis() が返す辞書のキー名は、
PySCFのバージョンによって細部が異なる可能性があるため、
_get() ヘルパーで複数の候補キー名を試す作りにしている。
"""

import time


def _get(d: dict, *keys, default=None):
    for k in keys:
        if k in d:
            return d[k]
    return default


class FrequencyResult:
    def __init__(self):
        self.frequencies_cm1 = []   # 振動数(cm^-1)。虚振動は負の値で表す(PySCFの慣例)
        self.normal_modes = None    # 基準振動モードの変位ベクトル。shape (n_modes, natom, 3) を想定
        self.n_imaginary = 0
        self.thermo_summary = {}
        self.elapsed_seconds = 0.0
        self.warning_message = ""


def run_frequency_analysis(mf, defaults: dict) -> FrequencyResult:
    """収束済みのCPU版SCFオブジェクトからHessianと振動数解析を実行する。

    Parameters
    ----------
    mf : 収束済み(mf.converged == True)の pyscf CPU SCF オブジェクト
    defaults : config/defaults.yaml を読み込んだ辞書
    """
    from pyscf.hessian import thermo

    result = FrequencyResult()
    t0 = time.perf_counter()

    hess = mf.Hessian().kernel()
    freq_info = thermo.harmonic_analysis(mf.mol, hess)

    freqs = list(_get(freq_info, "freq_wavenumber", "freq_cm-1", default=[]))
    result.frequencies_cm1 = [float(f.real) if hasattr(f, "real") else float(f) for f in freqs]
    result.n_imaginary = sum(1 for f in result.frequencies_cm1 if f < 0)
    result.normal_modes = _get(freq_info, "norm_mode", "normal_mode")

    freq_cfg = defaults["frequency"]
    freq_au = _get(freq_info, "freq_au")
    try:
        if freq_au is None:
            raise KeyError("freq_au")
        thermo_info = thermo.thermo(mf, freq_au, freq_cfg["temperature_K"], freq_cfg["pressure_Pa"])
        result.thermo_summary = {
            "ZPE_Hartree": float(_get(thermo_info, "ZPE", default=(None,))[0]),
            "G_tot_Hartree": float(_get(thermo_info, "G_tot", default=(None,))[0]),
            "temperature_K": freq_cfg["temperature_K"],
        }
    except Exception as e:
        result.thermo_summary = {}
        result.warning_message += (
            f"熱力学量(ZPE・自由エネルギー)の計算に失敗しました(振動数自体は取得できています): {e}\n"
        )

    if result.n_imaginary > 0:
        result.warning_message += (
            f"虚振動が{result.n_imaginary}個検出されました。"
            "この構造は真の極小構造(エネルギー最小点)ではない可能性があります。"
            "最適化の収束条件を厳しくする、初期構造を見直す、といった対応をご検討ください。"
        )

    result.elapsed_seconds = time.perf_counter() - t0
    return result
