"""
qchem_colab_app.gui.pyscf_screen
--------------------------------
ipywidgets を使って、ColabApp.ipynb の Execution Section から呼び出す
PySCF版のGUI一式を組み立てるモジュール。

設計方針:
    - ウィジェットの「見た目」を組み立てる責務だけをこのファイルに置き、
      計算の流れ(構造最適化 → CPUでのSCF再計算 → 振動数解析 → 出力ファイルの書き出し)は
      pyscf_backend/pipeline.py に委譲する(GUIと計算ロジックを分離し、どちらか一方だけを
      差し替えやすく、また、PySCFやColabなしで計算の流れを単体テストできるようにするため)。
      このファイルは、入力値の収集、アップロードされたファイルの読み込みと検証、結果の表示、
      例外の利用者向けメッセージへの変換だけを行う。
    - 画面はおおまかに次の4ブロックに分かれる:
        ① 入力(構造ファイルのドラッグ&ドロップ/選択・計算条件)
        ② 実行ボタンとログ出力
        ③ 可視化(エネルギー推移[点をクリックで対応する構造を表示]・
           振動アニメーション・MO・原子電荷)
        ④ ダウンロード(最終構造xyz・トラジェクトリxyz・moldenファイル)

構造ファイルの入力(ドラッグ&ドロップ)・エネルギーグラフ(点のクリック)・振動アニメーション・
ダウンロード・電荷入力の画面部品は、UMA版(gui/uma_screen.py)と共通の gui/parts.py にある。
これらは、ブラウザ側JavaScript → Colabのコールバック → Python の仕組み
(gui/colab_widgets.py)で実現している(ipywidgets.FileUploadやPlotlyのFigureWidgetは
Colab上で動作しない場合があったため)。Colab以外の環境では、ドロップ領域を出さず
通常のファイル選択ボタンとスライダーだけで動作する。このファイルには、PySCF版にしかない
部分(計算手法・基底関数の選択、MO・原子電荷の可視化、PySCFの呼び出し)だけを残している。

パッケージ内での位置づけ: 画面の層(gui)のうち、計算エンジン(pyscf_backend)を呼び出す「画面」。
計算エンジンを呼び出してよいのは、このファイルと uma_screen.py だけで、共通の画面部品(parts.py など)は、
計算エンジンのパッケージをimportしない(tests/test_package_layering.py で検査)。

使い方(ColabApp.ipynbから):
    from qchem_colab_app.gui import pyscf_screen
    app = pyscf_screen.build_app()
    display(app)
"""

import traceback

import ipywidgets as widgets
from IPython.display import display, clear_output

from qchem_colab_app.common_backend import config_loader, io_reader, version
from qchem_colab_app.gui import parts, inputs, outputs
from qchem_colab_app.pyscf_backend import engine, pipeline, visualizer_pyscf, analysis_pyscf


# -----------------------------------------------------------------------------
# アプリ本体
# -----------------------------------------------------------------------------

def build_app():
    purposes = config_loader.load_yaml("purposes.yaml")
    functionals = config_loader.load_yaml("functionals.yaml")
    basis_cfg = config_loader.load_yaml("basis_sets.yaml")
    defaults = config_loader.load_yaml("defaults.yaml")
    basis_items = basis_cfg.get("main_group") or []

    # --- ① 入力ウィジェット ---------------------------------------------------
    title = widgets.HTML(
        f"<h2>量子化学計算プロトタイプ (qchem_colab_app v{version.__version__})</h2>"
        f"<p>対応している計算手法・基底関数は「① 構造ファイルと計算条件」の"
        f"ドロップダウンからご確認ください。</p>"
    )

    state = {}  # 計算結果をウィジェット間で共有するための入れ物

    # 構造ファイルの入力・エネルギーグラフ・振動アニメーション・ダウンロードは、
    # uma_screen.py(UMA版)と共通の部品(gui/parts.py)を使う。
    file_input = parts.StructureFileInput(callback_prefix="qchem_drop")

    purpose_dd = parts.dropdown_from_list(purposes, "計算目的")
    method_dd = parts.dropdown_from_list(functionals, "計算手法")
    basis_dd = parts.dropdown_from_list(basis_items, "基底関数")

    # 電荷の入力欄は、UMA版(uma_screen.py)と共通の部品(「+1」の形で表示・−1/+1ボタンつき)
    charge_input = parts.ChargeInput(value=defaults["gui_defaults"]["charge"])
    mult_input = parts.MultiplicityInput(value=defaults["gui_defaults"]["multiplicity"])
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
    energy_viewer = parts.EnergyStructureViewer(callback_prefix="qchem_plot")
    vib_viewer = parts.VibrationViewer()

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
    downloads = parts.DownloadPanel(tmp_prefix="qchem_dl_", description_width="280px")
    download_box = downloads.widget

    # -------------------------------------------------------------------
    # 分子軌道・原子電荷(PySCF版にしかない可視化)
    # -------------------------------------------------------------------
    def _reset_results():
        """前回の計算結果の表示を、すべて消す(新しい結果と混ざらないように、計算の開始時に呼ぶ)。"""
        state.clear()
        energy_viewer.reset()
        vib_viewer.reset()
        downloads.reset()
        mo_dd.options = []
        mo_dd.disabled = True
        mo_button.disabled = True
        mo_note.value = ""
        density_button.disabled = True
        charge_labels_checkbox.disabled = True
        for output in (mo_output, charge_table_output, charge_view_output):
            with output:
                clear_output()

    def _setup_mo_controls():
        result = state["result"]
        choices = analysis_pyscf.orbital_choices(result.final_mol, result.mf_final)
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
            result = state["result"]
            view = visualizer_pyscf.render_orbital(result.final_mol, result.mf_final, mo_dd.value)
            view.show()

    def _render_charge_view():
        mol_final = state["result"].final_mol
        charges = state["charges"]
        with charge_view_output:
            clear_output(wait=True)
            view = visualizer_pyscf.render_charges(
                mol_final, charges, show_labels=charge_labels_checkbox.value)
            view.show()

    def _on_density_button_clicked(_):
        mol_final = state["result"].final_mol
        mf_final = state["result"].mf_final
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
        # 計算中にもう一度押されても、二重に実行しない(UMA版 uma_screen.py と同じ)
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
            _reset_results()
            try:
                charge = int(charge_input.value)
                multiplicity = int(mult_input.value)

                content_bytes, uploaded_filename = file_input.read()
                structure = inputs.load_uploaded_structure(
                    content_bytes, uploaded_filename, charge, multiplicity,
                    defaults["validation"]["min_interatomic_distance_angstrom"])

                settings = pipeline.CalculationSettings(
                    charge=charge, multiplicity=multiplicity,
                    functional_key=method_dd.value, basis_key=basis_dd.value,
                    do_frequency=bool(freq_checkbox.value))
                result = pipeline.run_calculation(structure, settings, defaults)
                state["result"] = result

                print("\n計算が完了しました。下の「③ 可視化」「④ ダウンロード」をご確認ください。")

                energy_viewer.show(result.opt_result)
                vib_viewer.setup(result.freq_result, result.final_symbols, result.final_coords)
                _setup_mo_controls()
                downloads.show([
                    *outputs.xyz_download_items(result.final_xyz_path, result.traj_xyz_path),
                    ("分子軌道・構造(molden)",
                     result.molden_path, ".molden", "molden"),
                ], default_stem=outputs.default_download_stem(uploaded_filename))

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
