"""
uma_backend.uma_report
------------------
計算結果をまとめたログファイル(テキスト)の本文を組み立てるモジュール。
ファイルへの書き出しやダウンロードはGUI側(gui_uma.py)が行い、ここでは文字列を
作るだけにしている(単体テストしやすくするため)。

ログには、条件・最適化の履歴・振動数・UMAに関する注意書き(uma_notice)を入れる。
Hugging Faceのトークンなどの秘密情報は一切含めない。
"""

from common.energy_plot import HARTREE_TO_KCAL_MOL
from uma_backend import uma_notice


def build_log_text(*, version, model_key, task_name, device_label, input_filename,
                   charge, multiplicity, opt_result, freq_result=None, total_seconds=None):
    lines = []
    add = lines.append

    add(f"qchem_colab_app UMA版 計算ログ (v{version})")
    add("=" * 60)
    add(f"入力ファイル : {input_filename}")
    add(f"モデル       : {model_key}(タスク: {task_name})")
    add(f"デバイス     : {device_label}")
    add(f"電荷 / スピン多重度 : {charge:+d} / {multiplicity}")
    add(f"最適化       : {opt_result.optimizer_name}"
        f"(収束条件 fmax <= {opt_result.fmax_target} eV/Å、最大 {opt_result.max_steps} ステップ)")
    add("")

    n_points = len(opt_result.energies)
    if opt_result.converged:
        add(f"結果: 収束しました(最終 fmax = {opt_result.final_fmax:.4f} eV/Å)")
    else:
        add("結果: 最大ステップ数までに収束しませんでした"
            f"(最終 fmax = {opt_result.final_fmax:.4f} eV/Å)。"
            "得られた構造は途中経過のものです。")
    if n_points:
        add(f"最終エネルギー: {opt_result.energies[-1]:.8f} Hartree"
            f"({opt_result.energies_ev[-1]:.6f} eV)")
    add(f"最適化の所要時間: {opt_result.elapsed_seconds:.1f} 秒")
    if freq_result is not None:
        add(f"振動数計算の所要時間: {freq_result.elapsed_seconds:.1f} 秒")
    if total_seconds is not None:
        add(f"合計所要時間: {total_seconds:.1f} 秒")
    add("")

    add("[最適化の履歴]")
    add(f"{'step':>5s} {'E (Hartree)':>16s} {'ΔE (kcal/mol)':>15s} {'fmax (eV/Å)':>12s}")
    if n_points:
        e_final = opt_result.energies[-1]
        for i in range(n_points):
            d_e = (opt_result.energies[i] - e_final) * HARTREE_TO_KCAL_MOL
            add(f"{i:5d} {opt_result.energies[i]:16.8f} {d_e:15.3f} {opt_result.fmax_history[i]:12.5f}")
        add("(ΔEは最終構造を基準とした相対エネルギー)")
    add("")

    if freq_result is not None:
        add("[振動数 (cm^-1)。負の値は虚振動]")
        if freq_result.frequencies_cm1:
            for i, f in enumerate(freq_result.frequencies_cm1, start=1):
                add(f"  モード{i:3d}: {f:10.2f}")
            summary = freq_result.thermo_summary or {}
            if "ZPE_Hartree" in summary:
                add(f"ゼロ点エネルギー(ZPE): {summary['ZPE_Hartree']:.6f} Hartree"
                    f"({summary['ZPE_kcal_per_mol']:.2f} kcal/mol)")
        if freq_result.warning_message:
            add(f"[注意] {freq_result.warning_message}")
        add("")

    add(uma_notice.notice_text())
    return "\n".join(lines) + "\n"
