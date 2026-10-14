"""
gui_uma.py
----------
UMA(機械学習ポテンシャル)版のGUI組み立て(ColabApp_UMA.ipynb のエントリーポイント)。

PySCF版の gui.py とは別ファイルになっており、お互いに影響しない。
(README.md「gui.pyをルート直下に置いている理由」のとおり、`gui.py` は `qcapp` と `common`
から、`gui_uma.py` は `uma_app` と `common` から、それぞれ必要な部品を組み合わせて
画面を組み立てる「アプリの組み立て役」。)

【PySCF版との違い】
    - 計算手法・基底関数の代わりに「UMAモデル」を選ぶ。
    - UMAのライセンス・引用などの情報は、このGUIには表示しない(ノートブック冒頭にまとめて表示する)。
    - 分子軌道・原子電荷・moldenの出力はない(UMAは電子状態を返さないため)。
    - 振動数計算は、構造最適化の後処理として行う(PySCF版と同じ位置づけ)。
    - Hugging Faceのトークンは、このGUIでは一切扱わない。ノートブックの「2.」のセルが
      環境変数 HF_TOKEN に設定し、uma_engine がそれを読み取る(入力欄をGUIに置くと、
      入力値がウィジェットの状態として保持され、保存されるノートブックに残りうるため)。

【ipywidgetsの版について】
    Colabのランタイムにはipywidgets 7.7.1が入っており、Colab標準のGUI表示の仕組みは7.x向け
    (8.xに更新すると、GUI部品が表示されず「コードスニペット」のパネルが開くだけになる)。
    このファイルは7.x・8.xのどちらでも動くように書いてあり、requirements-uma.txt では
    ipywidgetsの版を指定していない。8.xが入っている場合の対処は ColabApp_UMA.ipynb の
    「II-0」のセルを参照。

【PySCF版と共通の部品】(どちらも common/ にある)
    画面部品: 構造ファイルの入力(ドラッグ&ドロップ)・エネルギーグラフ(点のクリック)・
              振動アニメーション・ダウンロード(common/gui_parts.py)
    補助関数: アップロードされたファイルの取り出し・ダウンロードのファイル名(common/gui_helpers.py)
    そのほか: 構造ファイルの読み込み・検証(common/io_reader.py)、xyz出力(common/writer_xyz.py)、
              構造・振動の3D表示(common/plot_common.py)
    このファイルには、UMA版にしかない部分(モデルの選択、電荷の入力欄、UMAの呼び出し)だけを残している。

使い方(ColabApp_UMA.ipynbから):
    import gui_uma
    app = gui_uma.build_app()
    display(app)
"""

import os
import tempfile
import time
import traceback

import ipywidgets as widgets
from IPython.display import clear_output

from uma_app import load_yaml, __version__
from uma_app import uma_engine, uma_optimize, uma_freq, uma_report
from common import io_reader, writer_xyz, gui_parts, gui_helpers


# -----------------------------------------------------------------------------
# GUI本体
# -----------------------------------------------------------------------------

def build_app():
    models = load_yaml("uma_models.yaml")
    defaults = load_yaml("uma_defaults.yaml")
    gui_defaults = defaults["gui_defaults"]
    task_name = defaults["uma"]["task_name"]

    # --- ① 入力ウィジェット ---------------------------------------------------
    title = widgets.HTML(
        f"<h2>UMA版 構造最適化・振動数解析 (qchem_colab_app v{__version__})</h2>"
        "<p>機械学習ポテンシャルUMAによる高速な構造最適化を行います。</p>"
    )

    # 構造ファイルの入力・エネルギーグラフ・振動アニメーション・ダウンロードは、
    # gui.py(PySCF版)と共通の部品(common/gui_parts.py)を使う。
    file_input = gui_parts.StructureFileInput(callback_prefix="qchem_uma_drop")

    model_dd = gui_parts.dropdown_from_list(models, "UMAモデル")
    if gui_defaults.get("model") in [m["key"] for m in models]:
        model_dd.value = gui_defaults["model"]

    # 電荷の入力欄は、PySCF版(gui.py)と共通の部品(「+1」の形で表示・−1/+1ボタンつき)
    charge_input = gui_parts.ChargeInput(value=int(gui_defaults["charge"]))
    mult_input = widgets.IntText(
        value=gui_defaults["multiplicity"], description="スピン多重度",
        style={"description_width": "140px"}, layout=widgets.Layout(width="220px"),
    )
    freq_checkbox = widgets.Checkbox(
        value=gui_defaults["do_frequency"],
        description="振動数計算も実行する",
    )

    input_box = widgets.VBox([
        title,
        widgets.HTML("<h4>① 構造ファイルと計算条件</h4>"),
        *file_input.widgets,
        model_dd,
        widgets.HBox([charge_input.controls, mult_input]),
        charge_input.message,
        freq_checkbox,
    ])

    # --- ② 実行ボタン・ログ ------------------------------------------------
    run_button = widgets.Button(description="計算を実行する", button_style="primary",
                                 layout=widgets.Layout(width="200px"))
    log_output = widgets.Output(layout=widgets.Layout(border="1px solid #ccc", padding="6px"))

    # --- ③ 可視化エリア ---------------------------------------------------
    viz_header = widgets.HTML("<h4>③ 可視化</h4>")

    def _step_label(step_index, relative_energy_kcal, result):
        # 構造表示の見出しに、UMA版では力の最大値(fmax)も添える
        return (f"ステップ {step_index}: 相対エネルギー {relative_energy_kcal:+.2f} kcal/mol"
                f"  (力の最大値 fmax = {result.fmax_history[step_index]:.4f} eV/Å)")

    energy_viewer = gui_parts.EnergyStructureViewer(
        callback_prefix="qchem_uma_plot", step_label=_step_label)
    vib_viewer = gui_parts.VibrationViewer()

    viz_box = widgets.VBox([viz_header, energy_viewer.widget, vib_viewer.widget])

    # --- ④ ダウンロードエリア ------------------------------------------------
    downloads = gui_parts.DownloadPanel(tmp_prefix="qchem_uma_dl_", description_width="340px")
    download_box = downloads.widget

    # -------------------------------------------------------------------
    # 実行ボタンのハンドラ(計算パイプライン本体)
    # -------------------------------------------------------------------
    def on_run_clicked(_):
        if run_button.disabled:
            return
        run_button.disabled = True
        try:
            _run_pipeline()
        finally:
            run_button.disabled = False

    def _run_pipeline():
        with log_output:
            clear_output(wait=True)
            t_total_start = time.perf_counter()
            try:
                charge = charge_input.value
                multiplicity = int(mult_input.value)
                model_key = model_dd.value
                do_freq = bool(freq_checkbox.value)

                content_bytes, uploaded_filename = file_input.read()
                file_ext = os.path.splitext(uploaded_filename)[1] or ".xyz"
                with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False, mode="wb") as tf:
                    tf.write(content_bytes)
                    tmp_path = tf.name

                structure = io_reader.read_structure(tmp_path)
                print(f"[入力構造] ファイル: {uploaded_filename}"
                      f"  原子数: {len(structure.symbols)}  組成: "
                      f"{', '.join(sorted(set(structure.symbols)))}")

                io_reader.validate_structure(
                    structure, defaults["validation"]["min_interatomic_distance_angstrom"])
                io_reader.validate_charge_and_multiplicity(structure, charge, multiplicity)

                print("\n--- Hugging Faceのアクセス権を確認しています ---")
                uma_engine.check_model_access()
                print("  UMAへのアクセスを確認しました。")

                device = uma_engine.get_device()
                device_label = uma_engine.describe_device(device)
                print(f"\n--- UMAモデル {model_key} を読み込みます(デバイス: {device_label}) ---")
                if device == "cpu":
                    print("  [注意] GPUが使えないため、計算に非常に時間がかかります。"
                          "「ランタイム」→「ランタイムのタイプを変更」でT4 GPUを選んでください。")
                print("  (初回はモデルファイルのダウンロードに時間がかかります。"
                      "しばらくお待ちください)")
                t_load = time.perf_counter()
                predictor = uma_engine.load_predictor(model_key, device)
                calculator = uma_engine.make_calculator(predictor, task_name)
                print(f"  モデル準備 所要時間: {time.perf_counter() - t_load:.1f} 秒")

                atoms = uma_engine.build_atoms(structure, charge, multiplicity)

                opt_cfg = defaults["geometry_optimization"]
                print(f"\n--- 構造最適化を開始します"
                      f"({opt_cfg['optimizer']}, 収束条件 fmax <= {opt_cfg['fmax_ev_per_angstrom']} eV/Å,"
                      f" 最大 {opt_cfg['max_steps']} ステップ) ---")

                def _print_opt_progress(step, energy_hartree, fmax):
                    print(f"  step {step:3d}  E = {energy_hartree:.6f} Ha  fmax = {fmax:.4f} eV/Å")

                opt_result = uma_optimize.run_geometry_optimization(
                    atoms, calculator, opt_cfg, progress=_print_opt_progress)
                if opt_result.converged:
                    print(f"  収束しました。構造最適化 所要時間: {opt_result.elapsed_seconds:.1f} 秒"
                          f"  (記録された点数: {len(opt_result.energies)})")
                else:
                    print(f"  [注意] {opt_result.max_steps}ステップ以内に収束しませんでした"
                          f"(最終 fmax = {opt_result.final_fmax:.4f} eV/Å)。"
                          "途中経過の構造を表示します。初期構造を見直すか、"
                          "config/uma_defaults.yaml の max_steps を増やして再実行してください。")

                final_symbols = list(opt_result.symbols)
                final_coords = [list(c) for c in opt_result.coords_history[-1]]

                freq_result = None
                if do_freq:
                    natoms = len(final_symbols)
                    freq_cfg = defaults["frequency"]
                    if natoms >= freq_cfg["warn_natoms"]:
                        print(f"\n  [注意] 原子数が{natoms}と多いため、振動数計算には"
                              "時間がかかる可能性があります。このタブを開いたままお待ちください。")
                    print("\n--- 振動数計算を開始します(数値微分によるHessian) ---")
                    atoms_final = atoms.copy()
                    atoms_final.set_positions(final_coords)
                    report_every = max(1, natoms // 10)

                    def _print_freq_progress(done, total):
                        if done % report_every == 0 or done == total:
                            print(f"  Hessian計算: {done}/{total} 原子")

                    freq_result = uma_freq.run_frequency_analysis(
                        atoms_final, calculator, freq_cfg, progress=_print_freq_progress)
                    print(f"  振動数計算 所要時間: {freq_result.elapsed_seconds:.1f} 秒"
                          f"  (虚振動: {freq_result.n_imaginary}個)")
                    if freq_result.warning_message:
                        print(f"  [注意] {freq_result.warning_message}")

                total_elapsed = time.perf_counter() - t_total_start
                label = "構造最適化 + 振動数計算" if do_freq else "構造最適化のみ"
                print(f"\n=== 合計所要時間({label}): {total_elapsed:.1f} 秒 ===")

                out_dir = tempfile.mkdtemp(prefix="qchem_uma_output_")
                final_xyz_path = os.path.join(out_dir, "final_structure_for_ColabReaction.xyz")
                xyz_comment = (f"Optimized by qchem_colab_app UMA "
                               f"(v{__version__}, {model_key}, {task_name})")
                writer_xyz.write_final_structure(final_symbols, final_coords, final_xyz_path,
                                                 comment=xyz_comment)

                traj_xyz_path = os.path.join(out_dir, "optimization_trajectory.xyz")
                writer_xyz.write_trajectory(
                    opt_result.symbols, opt_result.coords_history, traj_xyz_path, opt_result.energies)

                log_path = os.path.join(out_dir, "calculation_log.txt")
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write(uma_report.build_log_text(
                        version=__version__, model_key=model_key, task_name=task_name,
                        device_label=device_label, input_filename=uploaded_filename,
                        charge=charge, multiplicity=multiplicity,
                        opt_result=opt_result, freq_result=freq_result,
                        total_seconds=total_elapsed))

                print("\n計算が完了しました。下の「③ 可視化」「④ ダウンロード」をご確認ください。")

                energy_viewer.show(opt_result)
                vib_viewer.setup(freq_result, final_symbols, final_coords)
                downloads.show(
                    [
                        ("最終構造(ColabReactionにそのままアップロード可能)",
                         final_xyz_path, ".xyz", "最終構造"),
                        ("最適化トラジェクトリ(多フレーム)",
                         traj_xyz_path, "_traj.xyz", "トラジェクトリ"),
                        ("計算ログ(条件・履歴・振動数・UMAに関する情報)",
                         log_path, "_log.txt", "計算ログ"),
                    ],
                    default_stem=gui_helpers.default_download_stem(uploaded_filename),
                )

            except (io_reader.StructureError, ValueError) as e:
                print("\n❌ 入力内容にエラーがあります:")
                print(str(e))
            except uma_engine.UmaSetupError as e:
                print("\n❌ UMAを使うための準備に問題があります:")
                print(str(e))
            except ImportError as e:
                print("\n❌ 必要なライブラリを読み込めませんでした:")
                print(f"{e}\n「3. 依存ライブラリのインストール」のセルを実行し直してください。")
            except RuntimeError as e:
                print("\n❌ 計算エラー:")
                print(str(e))
            except Exception as e:
                print("\n❌ 予期しないエラーが発生しました:")
                print(f"{type(e).__name__}: {e}")
                traceback.print_exc()

    run_button.on_click(on_run_clicked)

    return widgets.VBox([
        input_box,
        widgets.HTML("<h4>② 実行</h4>"),
        run_button,
        log_output,
        viz_box,
        download_box,
    ])
