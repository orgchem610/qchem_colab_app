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
    - UMAの利用条件の注意書きを表示し、確認のチェックを入れないと実行できない。
    - 分子軌道・原子電荷・moldenの出力はない(UMAは電子状態を返さないため)。
    - 振動数計算は、構造最適化の後処理として行う(PySCF版と同じ位置づけ)。
    - Hugging Faceのトークンは、このGUIでは扱わない(ノートブックの専用セルで設定する)。

【ipywidgetsの版について】
    Colabのランタイムにはipywidgets 7.7.1が入っており、Colab標準のGUI表示の仕組みは7.x向け
    (8.xに更新すると、GUI部品が表示されず「コードスニペット」のパネルが開くだけになる)。
    このファイルは7.x・8.xのどちらでも動くように書いてあり、requirements-uma.txt では
    ipywidgetsの版を指定していない。8.xが入っている場合の対処は ColabApp_UMA.ipynb の
    「II-0」のセルを参照。

【PySCF版と共通の部品】
    ドラッグ&ドロップ領域・クリックできるエネルギーグラフ(common/colab_widgets.py)、
    構造・振動の表示(common/plot_common.py)、構造ファイルの読み込み・検証(common/io_reader.py)、
    xyz出力(common/writer_xyz.py)。
    _dropdown_from_list と _extract_uploaded_file は gui.py と同じ内容のコピー
    (gui.py側を変更せずに済ませるため。将来、両アプリが安定したら common/ へ集約する想定)。

使い方(ColabApp_UMA.ipynbから):
    import gui_uma
    app = gui_uma.build_app()
    display(app)
"""

import html
import os
import shutil
import tempfile
import time
import traceback

import ipywidgets as widgets
from IPython.display import display, clear_output, HTML, JSON

from uma_app import load_yaml, __version__
from uma_app import uma_engine, uma_optimize, uma_freq, uma_notice, uma_report
from common import io_reader, writer_xyz, plot_common, colab_widgets


# -----------------------------------------------------------------------------
# 補助関数
# -----------------------------------------------------------------------------

def _dropdown_from_list(items, description, width="420px"):
    options = [(item["label"], item["key"]) for item in items]
    return widgets.Dropdown(
        options=options,
        description=description,
        style={"description_width": "140px"},
        layout=widgets.Layout(width=width),
    )


def _extract_uploaded_file(upload_widget, dropped_file=None):
    """アップロードされたファイルの中身(bytes)とファイル名を取り出す(gui.pyと同じ内容)。

    dropped_file({"name":..., "content":...})が渡された場合は、ドラッグ&ドロップ
    領域で受け取ったファイルを優先する。そうでなければ、ipywidgets 7.x / 8.x
    どちらのFileUpload.valueの形にも対応して取り出す。
    """
    if dropped_file is not None:
        return bytes(dropped_file["content"]), dropped_file["name"]

    value = upload_widget.value
    if not value:
        raise io_reader.StructureError(
            "構造ファイルがアップロードされていません。"
            "ドロップ領域にファイルをドラッグ&ドロップするか、「ファイルを選択」ボタンから"
            "ファイルを選択してください。"
        )

    # ipywidgets 8.x: tuple[dict] (各要素が name/type/size/content を持つ)
    if isinstance(value, (tuple, list)):
        first = value[0]
        if isinstance(first, dict):
            return bytes(first["content"]), first["name"]
        return bytes(first.content), first.name

    # ipywidgets 7.x: dict[filename] -> {"content": ..., ...}
    if isinstance(value, dict):
        filename, first = next(iter(value.items()))
        return bytes(first["content"]), filename

    raise RuntimeError(
        f"想定外の形式のFileUpload.valueを受け取りました(型: {type(value)})。"
        "ipywidgetsのバージョンをrequirements-uma.txt記載のものに合わせてください。"
    )


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
    notice_box = widgets.HTML(uma_notice.notice_html())
    consent_checkbox = widgets.Checkbox(
        value=False, description=uma_notice.CONSENT_LABEL, indent=False,
        layout=widgets.Layout(width="760px"),
    )

    state = {}  # 受け取ったファイル・計算結果をウィジェット間で共有するための入れ物

    # ドラッグ&ドロップ領域(Colabのみ)。ドロップされたファイルは state["dropped_file"] に入る。
    drop_status = widgets.HTML(
        "<span style='color:#666'>ファイルはまだ選択されていません。</span>")

    def _on_file_dropped(payload):
        """JavaScript(ドロップ領域)から呼ばれる。ファイルを検証して state に保存する。"""
        try:
            name, content = colab_widgets.parse_dropped_payload(payload)
            state["dropped_file"] = {"name": name, "content": content}
            drop_status.value = (
                f"<span style='color:#167a2e'>✓ {html.escape(name)} を受け取りました"
                f"({len(content):,} バイト)。</span>")
        except ValueError as e:
            state.pop("dropped_file", None)
            drop_status.value = (
                "<span style='color:#b42318'>ドロップされたファイルを受け取れませんでした: "
                f"{html.escape(str(e))}</span>")
        return JSON({"ok": True})

    drop_callback = colab_widgets.register_callback(_on_file_dropped, prefix="qchem_uma_drop")
    drop_zone_output = widgets.Output()
    if drop_callback is not None:
        # JavaScriptを含むHTMLは、ipywidgets.HTMLのvalueではなく
        # Output内でdisplay(HTML(...))して表示する(scriptが実行されるため)。
        with drop_zone_output:
            display(HTML(colab_widgets.build_drop_zone_html(drop_callback)))

    upload = widgets.FileUpload(
        accept=".xyz,.com,.gjf,.pdb", multiple=False,
        description="構造ファイル(.xyz/.com/.gjf/.pdb)",
        layout=widgets.Layout(width="320px"),
    )

    def _on_upload_changed(change):
        # ボタンで選び直した場合は、そちらを優先する(最後に選んだファイルを使う)
        if change["name"] == "value" and change["new"]:
            state.pop("dropped_file", None)
            drop_status.value = (
                "<span style='color:#666'>「構造ファイル」ボタンで選んだファイルを使用します。</span>")

    upload.observe(_on_upload_changed, names="value")

    if drop_callback is not None:
        hint_text = ("上の枠にファイルをドラッグ＆ドロップするか、下のボタンで選択してください。"
                     "両方を使った場合は、最後に選んだファイルが使われます。")
    else:
        hint_text = "ボタンをクリックして構造ファイルを選択してください。"
    upload_hint = widgets.HTML(
        f"<p style='color:#666'>{hint_text}"
        "対応形式: .xyz, .com, .gjf, .pdb(.mol/.sdfは現時点では未対応です)</p>"
    )

    model_dd = _dropdown_from_list(models, "UMAモデル")
    if gui_defaults.get("model") in [m["key"] for m in models]:
        model_dd.value = gui_defaults["model"]

    charge_input = widgets.IntText(
        value=gui_defaults["charge"], description="電荷",
        style={"description_width": "140px"}, layout=widgets.Layout(width="220px"),
    )
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
        notice_box,
        consent_checkbox,
        widgets.HTML("<h4>① 構造ファイルと計算条件</h4>"),
        *([drop_zone_output, drop_status] if drop_callback is not None else []),
        upload,
        upload_hint,
        model_dd,
        widgets.HBox([charge_input, mult_input]),
        freq_checkbox,
    ])

    # --- ② 実行ボタン・ログ ------------------------------------------------
    run_button = widgets.Button(description="計算を実行する", button_style="primary",
                                 layout=widgets.Layout(width="200px"))
    log_output = widgets.Output(layout=widgets.Layout(border="1px solid #ccc", padding="6px"))

    # --- ③ 可視化エリア ---------------------------------------------------
    viz_header = widgets.HTML("<h4>③ 可視化</h4>")
    energy_output = widgets.Output()
    plot_status = widgets.HTML()  # グラフのクリック処理でPython側に問題が起きたときのメッセージ用
    step_slider = widgets.IntSlider(
        description="ステップ", min=0, max=0, value=0, disabled=True,
        style={"description_width": "70px"}, layout=widgets.Layout(width="420px"),
    )
    step_view_output = widgets.Output()

    vib_mode_dd = widgets.Dropdown(description="振動モード", options=[], disabled=True,
                                    style={"description_width": "140px"}, layout=widgets.Layout(width="420px"))
    vib_button = widgets.Button(description="振動アニメーションを表示", disabled=True)
    vib_output = widgets.Output()

    viz_box = widgets.VBox([
        viz_header,
        widgets.HTML(
            "<b>エネルギー収束</b>"
            "<p style='color:#666;margin:2px 0'>グラフ上の点をクリックすると、"
            "対応する構造を下に表示します(お使いの環境でクリックが効かない場合は、"
            "代わりにスライダーで同じことができます)。</p>"
        ),
        energy_output, plot_status, step_slider, step_view_output,
        widgets.HTML("<b>振動アニメーション</b>"), widgets.HBox([vib_mode_dd, vib_button]), vib_output,
    ])

    # --- ④ ダウンロードエリア ------------------------------------------------
    download_header = widgets.HTML("<h4>④ ダウンロード</h4>")
    download_output = widgets.Output()
    download_box = widgets.VBox([download_header, download_output])

    # -------------------------------------------------------------------
    # 可視化の描画(エネルギー収束グラフと構造表示。gui.pyと同じ仕組み)
    # -------------------------------------------------------------------
    def _show_structure_at_step(step_index):
        opt_result = state["opt_result"]
        n_steps = state.get("n_steps") or len(opt_result.coords_history)
        step_index = max(0, min(int(step_index), n_steps - 1))
        with step_view_output:
            clear_output(wait=True)
            e = opt_result.energies[step_index]
            e_rel_kcal = (e - opt_result.energies[n_steps - 1]) * colab_widgets.HARTREE_TO_KCAL_MOL
            print(f"ステップ {step_index}: 相対エネルギー {e_rel_kcal:+.2f} kcal/mol"
                  f"  (力の最大値 fmax = {opt_result.fmax_history[step_index]:.4f} eV/Å)")
            view = plot_common.render_single_structure(
                opt_result.symbols, opt_result.coords_history[step_index])
            view.show()

    def _draw_energy_plot(selected_index):
        """エネルギー収束グラフ(点をクリックできるSVG)を描き直す。

        selected_index の点が赤い菱形で強調される。点をクリックすると
        JavaScriptが plot_callback(= _on_plot_clicked)を呼び、対応する構造が
        下に表示される(Colab以外ではクリックは効かず、スライダーで切り替える)。
        """
        opt_result = state["opt_result"]
        energies = list(opt_result.energies[:state["n_steps"]])
        with energy_output:
            clear_output(wait=True)
            try:
                display(HTML(colab_widgets.build_energy_plot_html(
                    energies, selected_index=selected_index, callback_name=plot_callback)))
            except Exception as e:
                print(f"(グラフを描画できませんでした。下のスライダーで構造を切り替えられます。詳細: {e})")

    def _on_step_slider_changed(change):
        if change["name"] != "value":
            return
        _show_structure_at_step(change["new"])
        # 点のクリックが原因の変更では、JavaScript側が既に赤い菱形を動かしているため描き直さない
        if not state.get("suppress_plot_redraw"):
            _draw_energy_plot(change["new"])

    step_slider.observe(_on_step_slider_changed, names="value")

    def _on_plot_clicked(index):
        """JavaScript(グラフ上の点のクリック)から呼ばれる。点の番号 index の構造を表示する。"""
        try:
            n_steps = state.get("n_steps", 0)
            if "opt_result" not in state or n_steps <= 0:
                return JSON({"ok": False})
            index = max(0, min(int(index), n_steps - 1))
            plot_status.value = ""
            state["suppress_plot_redraw"] = True
            try:
                if step_slider.value != index:
                    step_slider.value = index  # → _on_step_slider_changed が構造を表示する
                else:
                    _show_structure_at_step(index)
            finally:
                state["suppress_plot_redraw"] = False
        except Exception as e:
            plot_status.value = (
                "<span style='color:#b42318'>構造の表示に失敗しました。"
                f"スライダーをご利用ください。詳細: {html.escape(str(e))}</span>")
        return JSON({"ok": True})

    plot_callback = colab_widgets.register_callback(_on_plot_clicked, prefix="qchem_uma_plot")

    def _render_energy_and_structure():
        opt_result = state["opt_result"]
        n_steps = min(len(opt_result.energies), len(opt_result.coords_history))
        state["n_steps"] = n_steps
        plot_status.value = ""

        if n_steps == 0:
            with energy_output:
                clear_output(wait=True)
                print("エネルギーと構造の履歴が記録されていないため、グラフを表示できません。")
            step_slider.disabled = True
            return

        last = n_steps - 1
        # スライダーを動かすと observer が走る(構造を表示する)。グラフの描き直しは
        # 最後に1回だけ行うため、ここではグラフの再描画だけ止めておく。
        previous_value = step_slider.value
        state["suppress_plot_redraw"] = True
        try:
            step_slider.max = last
            step_slider.value = last
        finally:
            state["suppress_plot_redraw"] = False
        step_slider.disabled = (n_steps <= 1)
        _draw_energy_plot(last)
        if step_slider.value == previous_value:
            # スライダーの値が変わらなかった場合は observer が走らないため、ここで構造を表示する
            _show_structure_at_step(last)

    # -------------------------------------------------------------------
    # 振動アニメーション
    # -------------------------------------------------------------------
    def _setup_vibration_controls():
        freq_result = state.get("freq_result")
        if freq_result is None or freq_result.normal_modes is None or not freq_result.frequencies_cm1:
            vib_mode_dd.options = []
            vib_mode_dd.disabled = True
            vib_button.disabled = True
            return
        options = []
        for i, f in enumerate(freq_result.frequencies_cm1):
            tag = "(虚振動)" if f < 0 else ""
            options.append((f"モード{i + 1}: {f:.1f} cm⁻¹ {tag}", i))
        vib_mode_dd.options = options
        vib_mode_dd.value = 0 if options else None
        vib_mode_dd.disabled = False
        vib_button.disabled = False

    def _on_vib_button_clicked(_):
        freq_result = state["freq_result"]
        with vib_output:
            clear_output(wait=True)
            view, label = plot_common.render_vibration(
                state["final_symbols"], state["final_coords"],
                freq_result.frequencies_cm1, freq_result.normal_modes,
                mode_index=vib_mode_dd.value,
            )
            print(label)
            view.show()

    vib_button.on_click(_on_vib_button_clicked)

    # -------------------------------------------------------------------
    # ダウンロード
    # -------------------------------------------------------------------
    def _sanitize_filename_stem(raw: str) -> str:
        """ファイル名として使えない文字を除去する。空ならデフォルトの'result'にする。"""
        import re
        stem = (raw or "").strip()
        stem = re.sub(r'[\\/:*?"<>|]', "", stem)
        return stem or "result"

    def _refresh_downloads():
        with download_output:
            clear_output(wait=True)
            try:
                from google.colab import files as colab_files
                in_colab = True
            except ImportError:
                in_colab = False

            if not in_colab:
                print(
                    "(Google Colab以外の環境で実行しているため自動ダウンロードは"
                    "行いません。以下のパスから直接ファイルを取得してください。)"
                )
                print(f"・最終構造: {state['final_xyz_path']}")
                print(f"・トラジェクトリ: {state['traj_xyz_path']}")
                print(f"・計算ログ: {state['log_path']}")
                return

            # (説明ラベル, 元ファイルのパス, 付与する拡張子/サフィックス, ボタンラベル)
            items = [
                ("最終構造(ColabReactionにそのままアップロード可能)",
                 state["final_xyz_path"], ".xyz", ".xyz"),
                ("最適化トラジェクトリ(多フレーム)",
                 state["traj_xyz_path"], "_traj.xyz", "_traj.xyz"),
                ("計算ログ(条件・履歴・振動数・UMAに関する注意)",
                 state["log_path"], "_log.txt", "_log.txt"),
            ]

            # ファイル名入力欄は1つだけ用意し、全てのボタンで共有する。
            name_input = widgets.Text(
                placeholder="result",
                description="ファイル名",
                style={"description_width": "70px"},
                layout=widgets.Layout(width="240px"),
            )

            rows = [name_input]
            for description, src_path, suffix, button_label in items:
                button = widgets.Button(description=button_label, layout=widgets.Layout(width="110px"))

                def _make_handler(src_path=src_path, suffix=suffix):
                    def _handler(_):
                        stem = _sanitize_filename_stem(name_input.value)
                        filename = f"{stem}{suffix}"
                        tmp_dir = tempfile.mkdtemp(prefix="qchem_uma_dl_")
                        dst_path = os.path.join(tmp_dir, filename)
                        shutil.copyfile(src_path, dst_path)
                        colab_files.download(dst_path)
                    return _handler

                button.on_click(_make_handler())
                rows.append(widgets.HBox([
                    widgets.HTML(f"<div style='width:340px'>{description}</div>"),
                    button,
                ]))

            display(widgets.VBox(rows))

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
                if not consent_checkbox.value:
                    raise ValueError(
                        "UMAの利用条件の確認欄にチェックを入れてください。"
                        "(上の注意書きを読み、Hugging Face上でUMAの利用条件に同意済みであることを"
                        "確認するためのチェックです。)")

                charge = int(charge_input.value)
                multiplicity = int(mult_input.value)
                model_key = model_dd.value
                do_freq = bool(freq_checkbox.value)

                content_bytes, uploaded_filename = _extract_uploaded_file(
                    upload, state.get("dropped_file"))
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
                print("\n" + uma_notice.RESULT_NATURE)

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

                state.update(dict(
                    structure=structure, opt_result=opt_result, freq_result=freq_result,
                    final_symbols=final_symbols, final_coords=final_coords,
                    out_dir=out_dir, final_xyz_path=final_xyz_path,
                    traj_xyz_path=traj_xyz_path, log_path=log_path,
                ))

                print("\n計算が完了しました。下の「③ 可視化」「④ ダウンロード」をご確認ください。")

                _render_energy_and_structure()
                _setup_vibration_controls()
                _refresh_downloads()

            except (io_reader.StructureError, ValueError) as e:
                print("\n❌ 入力内容にエラーがあります:")
                print(str(e))
            except uma_engine.UmaSetupError as e:
                print("\n❌ UMAを使うための準備に問題があります:")
                print(str(e))
            except ImportError as e:
                print("\n❌ 必要なライブラリを読み込めませんでした:")
                print(f"{e}\n「2. 依存ライブラリのインストール」のセルを実行し直してください。")
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
