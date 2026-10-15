"""
gui.py
------
ipywidgets を使って、ColabApp.ipynb の Execution Section から呼び出す
GUI一式を組み立てるモジュール。

設計方針:
    - ウィジェットの「見た目」を組み立てる責務だけをこのファイルに置き、
      実際の計算処理(PySCFの呼び出し等)は qcapp/ 以下の各モジュールに
      委譲する(GUIと計算ロジックを分離し、どちらか一方だけを
      差し替えやすくするため)。
    - 画面はおおまかに次の4ブロックに分かれる:
        ① 入力(構造ファイルのドラッグ&ドロップ/選択・計算条件)
        ② 実行ボタンとログ出力
        ③ 可視化(エネルギー推移[点をクリックで対応する構造を表示]・
           振動アニメーション・MO・原子電荷)
        ④ ダウンロード(最終構造xyz・トラジェクトリxyz・moldenファイル)

構造ファイルの入力(ドラッグ&ドロップ)・エネルギーグラフ(点のクリック)・振動アニメーション・
ダウンロード・電荷入力の画面部品は、UMA版(gui_uma.py)と共通の common/gui_parts.py にある。
これらは、ブラウザ側JavaScript → Colabのコールバック → Python の仕組み
(common/colab_widgets.py)で実現している(ipywidgets.FileUploadやPlotlyのFigureWidgetは
Colab上で動作しない場合があったため)。Colab以外の環境では、ドロップ領域を出さず
通常のファイル選択ボタンとスライダーだけで動作する。このファイルには、PySCF版にしかない
部分(計算手法・基底関数の選択、MO・原子電荷の可視化、PySCFの呼び出し)だけを残している。

使い方(ColabApp.ipynbから):
    import gui
    app = gui.build_app()
    display(app)
"""

import os
import tempfile
import time
import traceback

import ipywidgets as widgets
from IPython.display import display, clear_output

from qcapp import load_yaml, __version__
from common import io_reader, writer_xyz, gui_parts, gui_helpers
from qcapp import engine, optimize, freq as freq_module
from qcapp import writer_molden, visualizer_pyscf, analysis_pyscf


# -----------------------------------------------------------------------------
# アプリ本体
# -----------------------------------------------------------------------------

def build_app():
    purposes = load_yaml("purposes.yaml")
    functionals = load_yaml("functionals.yaml")
    basis_cfg = load_yaml("basis_sets.yaml")
    defaults = load_yaml("defaults.yaml")
    basis_items = basis_cfg.get("main_group") or []

    # --- ① 入力ウィジェット ---------------------------------------------------
    title = widgets.HTML(
        f"<h2>量子化学計算プロトタイプ (qchem_colab_app v{__version__})</h2>"
        f"<p>対応している計算手法・基底関数は「① 構造ファイルと計算条件」の"
        f"ドロップダウンからご確認ください。</p>"
    )

    state = {}  # 計算結果をウィジェット間で共有するための入れ物

    # 構造ファイルの入力・エネルギーグラフ・振動アニメーション・ダウンロードは、
    # gui_uma.py(UMA版)と共通の部品(common/gui_parts.py)を使う。
    file_input = gui_parts.StructureFileInput(callback_prefix="qchem_drop")

    purpose_dd = gui_parts.dropdown_from_list(purposes, "計算目的")
    method_dd = gui_parts.dropdown_from_list(functionals, "計算手法")
    basis_dd = gui_parts.dropdown_from_list(basis_items, "基底関数")

    # 電荷の入力欄は、UMA版(gui_uma.py)と共通の部品(「+1」の形で表示・−1/+1ボタンつき)
    charge_input = gui_parts.ChargeInput(value=defaults["gui_defaults"]["charge"])
    mult_input = gui_parts.MultiplicityInput(value=defaults["gui_defaults"]["multiplicity"])
    freq_checkbox = widgets.Checkbox(
        value=defaults["gui_defaults"]["do_frequency"],
        description="振動数計算も実行する",
    )

    input_box = widgets.VBox([
        title,
        widgets.HTML("<h4>① 構造ファイルと計算条件</h4>"),
        *file_input.widgets,
        purpose_dd, method_dd, basis_dd,
        widgets.HBox([charge_input.controls, mult_input.widget]),
        charge_input.message,
        freq_checkbox,
    ])

    # --- ② 実行ボタン・ログ ------------------------------------------------
    run_button = widgets.Button(description="計算を実行する", button_style="primary",
                                 layout=widgets.Layout(width="200px"))
    log_output = widgets.Output(layout=widgets.Layout(border="1px solid #ccc", padding="6px"))

    # --- ③ 可視化エリア ---------------------------------------------------
    viz_header = widgets.HTML("<h4>③ 可視化</h4>")
    energy_viewer = gui_parts.EnergyStructureViewer(callback_prefix="qchem_plot")
    vib_viewer = gui_parts.VibrationViewer()

    mo_dd = widgets.Dropdown(description="分子軌道", options=[], disabled=True,
                              style={"description_width": "140px"}, layout=widgets.Layout(width="420px"))
    mo_button = widgets.Button(description="分子軌道を表示", disabled=True)
    mo_note = widgets.HTML()
    mo_output = widgets.Output()

    density_button = widgets.Button(description="原子電荷を表示", disabled=True)
    charge_table_output = widgets.Output()
    charge_labels_checkbox = widgets.Checkbox(
        value=True, description="図中の原子に電荷の数値ラベルも表示する", disabled=True)
    charge_view_output = widgets.Output()

    viz_box = widgets.VBox([
        viz_header,
        energy_viewer.widget,
        vib_viewer.widget,
        widgets.HTML("<b>分子軌道</b>"), widgets.HBox([mo_dd, mo_button]), mo_note, mo_output,
        widgets.HTML("<b>原子電荷(Mulliken電荷)</b>"), density_button,
        charge_table_output, charge_labels_checkbox, charge_view_output,
    ])

    # --- ④ ダウンロードエリア ------------------------------------------------
    downloads = gui_parts.DownloadPanel(tmp_prefix="qchem_dl_", description_width="280px")
    download_box = downloads.widget

    # -------------------------------------------------------------------
    # 分子軌道・原子電荷(PySCF版にしかない可視化)
    # -------------------------------------------------------------------
    def _setup_mo_controls():
        mf_final = state["mf_final"]
        choices = analysis_pyscf.orbital_choices(state["final_mol"], mf_final)
        mo_dd.options = choices.options
        mo_dd.value = choices.default_index
        mo_note.value = ("<small>開殻分子のため、αスピンの軌道を表示します"
                         "(SOMO: 電子が1個だけ入っている軌道)。</small>") if choices.open_shell else ""
        mo_dd.disabled = False
        mo_button.disabled = False
        density_button.disabled = False

    def _on_mo_button_clicked(_):
        with mo_output:
            clear_output(wait=True)
            view = visualizer_pyscf.render_orbital(state["final_mol"], state["mf_final"], mo_dd.value)
            view.show()

    def _render_charge_view():
        mol_final = state["final_mol"]
        charges = state["charges"]
        with charge_view_output:
            clear_output(wait=True)
            view = visualizer_pyscf.render_charges(
                mol_final, charges, show_labels=charge_labels_checkbox.value)
            view.show()

    def _on_density_button_clicked(_):
        mol_final = state["final_mol"]
        mf_final = state["mf_final"]
        charges = analysis_pyscf.compute_mulliken_charges(mol_final, mf_final)
        state["charges"] = charges
        with charge_table_output:
            clear_output(wait=True)
            display(widgets.HTML(
                "<b>原子ごとのMulliken電荷</b>"
                "(球の色: 正電荷=青 ・ 中性付近=緑 ・ 負電荷=赤 のグラデーション)" +
                visualizer_pyscf.atomic_charges_table_html(charges)))
        charge_labels_checkbox.disabled = False
        _render_charge_view()

    def _on_charge_labels_toggled(change):
        if change["name"] == "value" and "charges" in state:
            _render_charge_view()

    mo_button.on_click(_on_mo_button_clicked)
    density_button.on_click(_on_density_button_clicked)
    charge_labels_checkbox.observe(_on_charge_labels_toggled, names="value")

    # -------------------------------------------------------------------
    # 実行ボタンのハンドラ(計算パイプライン本体)
    # -------------------------------------------------------------------
    def on_run_clicked(_):
        # 計算中にもう一度押されても、二重に実行しない(UMA版 gui_uma.py と同じ)
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
                charge = int(charge_input.value)
                multiplicity = int(mult_input.value)
                basis_key = basis_dd.value
                functional_key = method_dd.value
                do_freq = bool(freq_checkbox.value)
                try_gpu = engine.gpu_runtime_detected()  # GPUランタイムなら自動でGPU4PySCFを試す

                content_bytes, uploaded_filename = file_input.read()
                structure = gui_helpers.load_uploaded_structure(
                    content_bytes, uploaded_filename, charge, multiplicity,
                    defaults["validation"]["min_interatomic_distance_angstrom"])

                if io_reader.contains_transition_metal(structure):
                    raise io_reader.StructureError(
                        "アップロードされた構造に遷移金属元素が含まれています。\n"
                        "現在のプロトタイプ(HF/3-21G)は主要な典型元素(H〜Ar程度)"
                        "のみに対応しており、遷移金属の計算にはまだ対応していません。\n"
                        "今後のバージョンでECP付き基底関数(LANL2DZ等)を追加予定です。"
                    )

                mol = engine.build_mole(structure, charge, multiplicity, basis_key)

                print("\n--- 構造最適化を開始します ---")
                print("  GPUランタイム: " + (
                    "検出されました(GPU4PySCFでの計算を試みます)" if try_gpu
                    else "検出されませんでした(CPUで計算します)"))
                opt_result = optimize.run_geometry_optimization(
                    mol, functional_key, defaults, try_gpu=try_gpu)
                print(f"  {opt_result.gpu_message}")
                print(f"  構造最適化 所要時間: {opt_result.elapsed_seconds:.1f} 秒"
                      f"  (記録されたエネルギー点数: {len(opt_result.energies)})")
                if len(opt_result.energies) <= 1:
                    print(
                        "  [注意] 記録されたエネルギー点数が非常に少ないため、"
                        "エネルギー収束グラフが単調にならない可能性があります。"
                        "qcapp/optimize.py の _make_callback() のキー名調整が"
                        "必要かもしれません(README.mdのトラブルシューティング参照)。"
                    )

                final_mol = opt_result.mol_final
                final_mol.cart = True  # 念のため明示(GaussView/MacMolPlt互換のデカルト型d/f軌道)
                natm = final_mol.natm
                print(
                    f"\n--- 最終構造でCPU上のSCFを再計算しています(原子数: {natm})---\n"
                    "  (分子軌道・電荷・moldenファイル出力等はCPU版PySCFで統一的に扱うため、\n"
                    "   構造最適化にGPUを使った場合でもこの再計算はCPU上で行っています。\n"
                    "   構造最適化時の密度行列を初期値として使うことで、通常より速く\n"
                    "   収束するはずですが、原子数が多いほど時間がかかります)"
                )
                t_cpu_scf_start = time.perf_counter()
                mf_final, _, _ = engine.build_scf(final_mol, functional_key, try_gpu=False)
                mf_final = engine.run_scf(mf_final, defaults, dm0=opt_result.dm0_guess)
                print(f"  CPU再計算 所要時間: {time.perf_counter() - t_cpu_scf_start:.1f} 秒")

                freq_result = None
                if do_freq:
                    if natm >= defaults["frequency"]["warn_natoms"]:
                        print(
                            f"\n  [注意] 原子数が{natm}と多いため、振動数計算(Hessian計算)は\n"
                            "  CPU上でかなりの時間(数十分〜数時間程度)がかかる可能性があります。\n"
                            "  Colabの接続が長時間の無出力状態で切断されることがあるため、\n"
                            "  途中経過が出ない間もこのタブを開いたままにしておいてください。"
                        )
                    print("\n--- 振動数計算を開始します ---")
                    t_freq_start = time.perf_counter()
                    freq_result = freq_module.run_frequency_analysis(mf_final, defaults)
                    print(f"  振動数計算 所要時間: {freq_result.elapsed_seconds:.1f} 秒"
                          f"(実測の壁時計時間: {time.perf_counter() - t_freq_start:.1f} 秒)")
                    if freq_result.warning_message:
                        print(f"  [注意] {freq_result.warning_message}")

                total_elapsed = time.perf_counter() - t_total_start
                label = "構造最適化 + 振動数計算" if do_freq else "構造最適化のみ"
                print(f"\n=== 合計所要時間({label}): {total_elapsed:.1f} 秒 ===")

                out_dir = tempfile.mkdtemp(prefix="qchem_output_")
                final_symbols = [final_mol.atom_symbol(i) for i in range(final_mol.natm)]
                final_coords = [list(c) for c in final_mol.atom_coords(unit="Angstrom")]

                xyz_comment = f"Optimized by qchem_colab_app (v{__version__}, {functional_key}/{basis_key})"
                final_xyz_path, traj_xyz_path = writer_xyz.write_optimization_outputs(
                    out_dir, final_symbols, final_coords, xyz_comment, opt_result)

                molden_path = os.path.join(out_dir, "final_structure.molden")
                writer_molden.write_molden(mf_final, molden_path)

                state.update(dict(
                    structure=structure, opt_result=opt_result,
                    final_mol=final_mol, mf_final=mf_final, freq_result=freq_result,
                    final_symbols=final_symbols, final_coords=final_coords,
                    out_dir=out_dir, final_xyz_path=final_xyz_path,
                    traj_xyz_path=traj_xyz_path, molden_path=molden_path,
                ))

                print("\n計算が完了しました。下の「③ 可視化」「④ ダウンロード」をご確認ください。")

                energy_viewer.show(opt_result)
                vib_viewer.setup(freq_result, final_symbols, final_coords)
                _setup_mo_controls()
                downloads.show([
                    *gui_helpers.xyz_download_items(final_xyz_path, traj_xyz_path),
                    ("分子軌道・構造(molden)",
                     molden_path, ".molden", "molden"),
                ], default_stem=gui_helpers.default_download_stem(uploaded_filename))

            except (io_reader.StructureError, ValueError) as e:
                print("\n❌ 入力内容にエラーがあります:")
                print(str(e))
            except engine.SCFConvergenceError as e:
                print("\n❌ SCF計算エラー:")
                print(str(e))
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
