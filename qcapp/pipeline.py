"""
qcapp.pipeline
--------------
PySCF版の「計算の流れ」をまとめたモジュール。

    検証済みの構造 → 遷移金属の確認 → 構造最適化(GPU4PySCF・CPUの自動切り替え)
    → 最終構造でのCPU上のSCF再計算 → (任意)振動数解析 → 出力ファイル(xyz・molden)の書き出し

画面(ipywidgets)にも、アップロードされたファイルの扱いにも依存しない。画面に出す文面は、
log という関数(既定は print)を通して受け渡すため、GUI(gui.py)は log_output の中で
この関数を呼ぶだけでよく、ColabやPySCFなしでも、各段階の呼び出しの順序と受け渡しを
単体テストできる(engine・optimize・freq・writer_molden を差し替えて確認する)。

GUI側の責務(gui.py): 入力値の収集、アップロードされたファイルの読み込みと検証
(common/gui_input.load_uploaded_structure)、この関数の呼び出し、結果の表示、
例外の利用者向けメッセージへの変換。例外は、ここでは捕まえずにそのまま送出する。
"""

import os
import tempfile
import time
from dataclasses import dataclass

from common import io_reader, writer_xyz
from qcapp import __version__, engine, freq as freq_module, optimize, writer_molden


@dataclass
class CalculationSettings:
    """利用者が指定する計算条件。"""
    charge: int
    multiplicity: int
    functional_key: str          # config/functionals.yaml の key
    basis_key: str               # config/basis_sets.yaml の key
    do_frequency: bool = True    # 構造最適化のあとに、振動数計算も行うか
    try_gpu: bool = None         # GPU4PySCFを試すか。None のときは、GPUランタイムかどうかを自動で判定する


@dataclass
class CalculationResult:
    """計算の結果と、書き出したファイルの場所。画面表示・ダウンロードに使う。"""
    structure: object            # common.io_reader.Structure(読み込んだ構造)
    opt_result: object           # qcapp.optimize.OptimizationResult
    final_mol: object            # 最適化後の構造の pyscf Mole
    mf_final: object             # 最終構造でCPU上で収束させたSCFオブジェクト
    freq_result: object          # qcapp.freq.FrequencyResult(振動数計算をしなかった場合は None)
    final_symbols: list
    final_coords: list           # 単位 Å
    out_dir: str                 # 出力ファイルを書き出したフォルダ
    final_xyz_path: str
    traj_xyz_path: str
    molden_path: str
    total_seconds: float


def run_calculation(structure, settings, defaults, log=print):
    """PySCF版の計算を、最初から最後まで実行して、結果を返す。

    Parameters
    ----------
    structure : common.io_reader.Structure(読み込みと入力検証が済んだ構造)
    settings : CalculationSettings
    defaults : config/defaults.yaml を読み込んだ辞書
    log : 進捗・注意を1行(または複数行)の文字列で受け取る関数(既定は print)

    Raises
    ------
    io_reader.StructureError : 遷移金属を含む構造など、このバージョンで扱えない入力のとき
    engine.SCFConvergenceError : SCFが収束しなかったとき
    RuntimeError : 構造最適化が収束しなかったとき(optimize が送出する)
    """
    t_total_start = time.perf_counter()
    functional_key = settings.functional_key
    basis_key = settings.basis_key
    try_gpu = settings.try_gpu if settings.try_gpu is not None else engine.gpu_runtime_detected()

    if engine.contains_transition_metal(structure):
        raise io_reader.StructureError(
            "アップロードされた構造に遷移金属元素が含まれています。\n"
            "現在のプロトタイプ(HF/3-21G)は主要な典型元素(H〜Ar程度)"
            "のみに対応しており、遷移金属の計算にはまだ対応していません。\n"
            "今後のバージョンでECP付き基底関数(LANL2DZ等)を追加予定です。"
        )

    mol = engine.build_mole(structure, settings.charge, settings.multiplicity, basis_key)

    log("\n--- 構造最適化を開始します ---")
    log("  GPUランタイム: " + (
        "検出されました(GPU4PySCFでの計算を試みます)" if try_gpu
        else "検出されませんでした(CPUで計算します)"))
    opt_result = optimize.run_geometry_optimization(mol, functional_key, defaults, try_gpu=try_gpu)
    log(f"  {opt_result.gpu_message}")
    log(f"  構造最適化 所要時間: {opt_result.elapsed_seconds:.1f} 秒"
        f"  (記録されたエネルギー点数: {len(opt_result.energies)})")
    if len(opt_result.energies) <= 1:
        log("  [注意] 記録されたエネルギー点数が非常に少ないため、"
            "エネルギー収束グラフが単調にならない可能性があります。"
            "qcapp/optimize.py の _make_callback() のキー名調整が"
            "必要かもしれません。")

    final_mol = opt_result.mol_final
    final_mol.cart = True  # 念のため明示(GaussView/MacMolPlt互換のデカルト型d/f軌道)
    natm = final_mol.natm
    log(f"\n--- 最終構造でCPU上のSCFを再計算しています(原子数: {natm})---\n"
        "  (分子軌道・電荷・moldenファイル出力等はCPU版PySCFで統一的に扱うため、\n"
        "   構造最適化にGPUを使った場合でもこの再計算はCPU上で行っています。\n"
        "   構造最適化時の密度行列を初期値として使うことで、通常より速く\n"
        "   収束するはずですが、原子数が多いほど時間がかかります)")
    t_cpu_scf_start = time.perf_counter()
    mf_final, _, _ = engine.build_scf(final_mol, functional_key, try_gpu=False)
    mf_final = engine.run_scf(mf_final, defaults, dm0=opt_result.dm0_guess)
    log(f"  CPU再計算 所要時間: {time.perf_counter() - t_cpu_scf_start:.1f} 秒")

    freq_result = None
    if settings.do_frequency:
        if natm >= defaults["frequency"]["warn_natoms"]:
            log(f"\n  [注意] 原子数が{natm}と多いため、振動数計算(Hessian計算)は\n"
                "  CPU上でかなりの時間(数十分〜数時間程度)がかかる可能性があります。\n"
                "  Colabの接続が長時間の無出力状態で切断されることがあるため、\n"
                "  途中経過が出ない間もこのタブを開いたままにしておいてください。")
        log("\n--- 振動数計算を開始します ---")
        t_freq_start = time.perf_counter()
        freq_result = freq_module.run_frequency_analysis(mf_final, defaults)
        log(f"  振動数計算 所要時間: {freq_result.elapsed_seconds:.1f} 秒"
            f"(実測の壁時計時間: {time.perf_counter() - t_freq_start:.1f} 秒)")
        if freq_result.warning_message:
            log(f"  [注意] {freq_result.warning_message}")

    total_seconds = time.perf_counter() - t_total_start
    label = "構造最適化 + 振動数計算" if settings.do_frequency else "構造最適化のみ"
    log(f"\n=== 合計所要時間({label}): {total_seconds:.1f} 秒 ===")

    out_dir = tempfile.mkdtemp(prefix="qchem_output_")
    final_symbols = [final_mol.atom_symbol(i) for i in range(final_mol.natm)]
    final_coords = [list(c) for c in final_mol.atom_coords(unit="Angstrom")]

    xyz_comment = f"Optimized by qchem_colab_app (v{__version__}, {functional_key}/{basis_key})"
    final_xyz_path, traj_xyz_path = writer_xyz.write_optimization_outputs(
        out_dir, final_symbols, final_coords, xyz_comment, opt_result)

    molden_path = os.path.join(out_dir, "final_structure.molden")
    writer_molden.write_molden(mf_final, molden_path)

    return CalculationResult(
        structure=structure, opt_result=opt_result, final_mol=final_mol, mf_final=mf_final,
        freq_result=freq_result, final_symbols=final_symbols, final_coords=final_coords,
        out_dir=out_dir, final_xyz_path=final_xyz_path, traj_xyz_path=traj_xyz_path,
        molden_path=molden_path, total_seconds=total_seconds)
