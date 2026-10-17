"""
uma_app.uma_pipeline
--------------------
UMA版の「計算の流れ」をまとめたモジュール。

    検証済みの構造 → Hugging Faceのアクセス権の確認 → モデルの読み込み(デバイスの判定)
    → 構造最適化 → (任意)振動数解析 → 出力ファイル(xyz・計算ログ)の書き出し

画面(ipywidgets)にも、アップロードされたファイルの扱いにも依存しない。画面に出す文面は、
log という関数(既定は print)を通して受け渡すため、GUI(gui_uma.py)は log_output の中で
この関数を呼ぶだけでよく、UMA・fairchem・Colabなしでも、各段階の呼び出しの順序と
受け渡しを単体テストできる(uma_hf・uma_engine・uma_optimize・uma_freq を差し替えて確認する)。

GUI側の責務(gui_uma.py): 入力値の収集、アップロードされたファイルの読み込みと検証
(common/gui_input.load_uploaded_structure)、この関数の呼び出し、結果の表示、
例外の利用者向けメッセージへの変換。例外は、ここでは捕まえずにそのまま送出する。
PySCF版の qcapp/pipeline.py とは独立しており(uma_app は qcapp に依存しない)、
似た流れでも、エンジンごとに別々に変えていける。
"""

import os
import tempfile
import time
from dataclasses import dataclass

from common import writer_xyz
from uma_app import __version__, uma_engine, uma_freq, uma_hf, uma_optimize, uma_report


@dataclass
class CalculationSettings:
    """利用者が指定する計算条件。"""
    charge: int
    multiplicity: int
    model_key: str               # config/uma_models.yaml の key
    do_frequency: bool = True    # 構造最適化のあとに、振動数計算も行うか
    input_filename: str = ""     # 計算ログに記載する、入力ファイル名


@dataclass
class CalculationResult:
    """計算の結果と、書き出したファイルの場所。画面表示・ダウンロードに使う。"""
    structure: object            # common.io_reader.Structure(読み込んだ構造)
    opt_result: object           # uma_app.uma_optimize.OptimizationResult
    freq_result: object          # uma_app.uma_freq.FrequencyResult(振動数計算をしなかった場合は None)
    final_symbols: list
    final_coords: list           # 単位 Å
    device_label: str            # 計算に使ったデバイスの説明(例: GPU(Tesla T4))
    out_dir: str                 # 出力ファイルを書き出したフォルダ
    final_xyz_path: str
    traj_xyz_path: str
    log_path: str
    total_seconds: float


def run_calculation(structure, settings, defaults, log=print):
    """UMA版の計算を、最初から最後まで実行して、結果を返す。

    Parameters
    ----------
    structure : common.io_reader.Structure(読み込みと入力検証が済んだ構造)
    settings : CalculationSettings
    defaults : config/uma_defaults.yaml を読み込んだ辞書
    log : 進捗・注意を1行(または複数行)の文字列で受け取る関数(既定は print)

    Raises
    ------
    uma_hf.UmaSetupError : トークン・アクセス権・ライブラリ未導入など、UMAを使う準備の問題
    ImportError : 必要なライブラリを読み込めなかったとき
    ValueError : 設定ファイルの内容に誤りがあるとき(最適化アルゴリズム名など)
    """
    t_total_start = time.perf_counter()
    model_key = settings.model_key
    task_name = defaults["uma"]["task_name"]
    charge = settings.charge
    multiplicity = settings.multiplicity

    log("\n--- Hugging Faceのアクセス権を確認しています ---")
    uma_hf.check_model_access()
    log("  UMAへのアクセスを確認しました。")

    device = uma_engine.get_device()
    device_label = uma_engine.describe_device(device)
    log(f"\n--- UMAモデル {model_key} を読み込みます(デバイス: {device_label}) ---")
    if device == "cpu":
        log("  [注意] GPUが使えないため、計算に非常に時間がかかります。"
            "「ランタイム」→「ランタイムのタイプを変更」でT4 GPUを選んでください。")
    log("  (初回はモデルファイルのダウンロードに時間がかかります。"
        "しばらくお待ちください)")
    t_load = time.perf_counter()
    predictor = uma_engine.load_predictor(model_key, device)
    calculator = uma_engine.make_calculator(predictor, task_name)
    log(f"  モデル準備 所要時間: {time.perf_counter() - t_load:.1f} 秒")

    atoms = uma_engine.build_atoms(structure, charge, multiplicity)

    opt_cfg = defaults["geometry_optimization"]
    log(f"\n--- 構造最適化を開始します"
        f"({opt_cfg['optimizer']}, 収束条件 fmax <= {opt_cfg['fmax_ev_per_angstrom']} eV/Å,"
        f" 最大 {opt_cfg['max_steps']} ステップ) ---")

    def _log_opt_progress(step, energy_hartree, fmax):
        log(f"  step {step:3d}  E = {energy_hartree:.6f} Ha  fmax = {fmax:.4f} eV/Å")

    opt_result = uma_optimize.run_geometry_optimization(
        atoms, calculator, opt_cfg, progress=_log_opt_progress)
    if opt_result.converged:
        log(f"  収束しました。構造最適化 所要時間: {opt_result.elapsed_seconds:.1f} 秒"
            f"  (記録された点数: {len(opt_result.energies)})")
    else:
        log(f"  [注意] {opt_result.max_steps}ステップ以内に収束しませんでした"
            f"(最終 fmax = {opt_result.final_fmax:.4f} eV/Å)。"
            "途中経過の構造を表示します。初期構造を見直すか、"
            "config/uma_defaults.yaml の max_steps を増やして再実行してください。")

    final_symbols = list(opt_result.symbols)
    final_coords = [list(c) for c in opt_result.coords_history[-1]]

    freq_result = None
    if settings.do_frequency:
        natoms = len(final_symbols)
        freq_cfg = defaults["frequency"]
        if natoms >= freq_cfg["warn_natoms"]:
            log(f"\n  [注意] 原子数が{natoms}と多いため、振動数計算には"
                "時間がかかる可能性があります。このタブを開いたままお待ちください。")
        log("\n--- 振動数計算を開始します(数値微分によるHessian) ---")
        atoms_final = atoms.copy()
        atoms_final.set_positions(final_coords)
        report_every = max(1, natoms // 10)

        def _log_freq_progress(done, total):
            if done % report_every == 0 or done == total:
                log(f"  Hessian計算: {done}/{total} 原子")

        freq_result = uma_freq.run_frequency_analysis(
            atoms_final, calculator, freq_cfg, progress=_log_freq_progress)
        log(f"  振動数計算 所要時間: {freq_result.elapsed_seconds:.1f} 秒"
            f"  (虚振動: {freq_result.n_imaginary}個)")
        if freq_result.warning_message:
            log(f"  [注意] {freq_result.warning_message}")

    total_seconds = time.perf_counter() - t_total_start
    label = "構造最適化 + 振動数計算" if settings.do_frequency else "構造最適化のみ"
    log(f"\n=== 合計所要時間({label}): {total_seconds:.1f} 秒 ===")

    out_dir = tempfile.mkdtemp(prefix="qchem_uma_output_")
    xyz_comment = (f"Optimized by qchem_colab_app UMA "
                   f"(v{__version__}, {model_key}, {task_name})")
    final_xyz_path, traj_xyz_path = writer_xyz.write_optimization_outputs(
        out_dir, final_symbols, final_coords, xyz_comment, opt_result)

    log_path = os.path.join(out_dir, "calculation_log.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(uma_report.build_log_text(
            version=__version__, model_key=model_key, task_name=task_name,
            device_label=device_label, input_filename=settings.input_filename,
            charge=charge, multiplicity=multiplicity,
            opt_result=opt_result, freq_result=freq_result,
            total_seconds=total_seconds))

    return CalculationResult(
        structure=structure, opt_result=opt_result, freq_result=freq_result,
        final_symbols=final_symbols, final_coords=final_coords, device_label=device_label,
        out_dir=out_dir, final_xyz_path=final_xyz_path, traj_xyz_path=traj_xyz_path,
        log_path=log_path, total_seconds=total_seconds)
