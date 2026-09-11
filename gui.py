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
        ① 入力(構造アップロード・計算条件)
        ② 実行ボタンとログ出力
        ③ 可視化(エネルギー推移・軌跡・振動アニメーション・MO・原子電荷)
        ④ ダウンロード(最終構造xyz・トラジェクトリxyz・moldenファイル)

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
from IPython.display import display, clear_output, HTML, Image

from qcapp import load_yaml, __version__
from qcapp import io_reader, engine, optimize, freq as freq_module
from qcapp import writer_xyz, writer_molden, visualizer


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


def _extract_uploaded_bytes(upload_widget):
    """ipywidgets 7.x / 8.x どちらのFileUpload.valueの形にも対応して
    アップロードされたファイルの中身(bytes)を取り出す。
    """
    value = upload_widget.value
    if not value:
        raise io_reader.StructureError(
            "構造ファイル(.xyz)がアップロードされていません。"
            "「構造ファイル(.xyz)」のアップロード欄からファイルを選択してください。"
        )

    # ipywidgets 8.x: tuple[dict] (各要素が name/type/size/content を持つ)
    if isinstance(value, (tuple, list)):
        first = value[0]
        content = first["content"] if isinstance(first, dict) else first.content
        return bytes(content)

    # ipywidgets 7.x: dict[filename] -> {"content": ..., ...}
    if isinstance(value, dict):
        first = next(iter(value.values()))
        return bytes(first["content"])

    raise RuntimeError(
        f"想定外の形式のFileUpload.valueを受け取りました(型: {type(value)})。"
        "ipywidgetsのバージョンをrequirements.txt記載のものに合わせてください。"
    )


def _homo_lumo_window(mf, half_width=2):
    """HOMOを中心に前後 half_width 個ずつの軌道インデックスとラベルを作る。"""
    homo_idx, lumo_idx = visualizer.get_homo_lumo_indices(mf)
    n_mo = mf.mo_energy.shape[-1] if hasattr(mf.mo_energy, "shape") else len(mf.mo_energy)

    options = []
    for i in range(homo_idx - half_width + 1, lumo_idx + half_width):
        if i < 0 or i >= n_mo:
            continue
        if i == homo_idx:
            label = f"HOMO (軌道{i}番)"
        elif i == lumo_idx:
            label = f"LUMO (軌道{i}番)"
        elif i < homo_idx:
            label = f"HOMO-{homo_idx - i} (軌道{i}番)"
        else:
            label = f"LUMO+{i - lumo_idx} (軌道{i}番)"
        options.append((label, i))
    return options, homo_idx


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
        f"<p>現在対応している計算手法・基底関数は限定されています"
        f"(HF / 3-21G のみ)。今後のバージョンで拡張予定です。</p>"
    )

    upload = widgets.FileUpload(
        accept=".xyz", multiple=False,
        description="構造ファイル(.xyz)",
        layout=widgets.Layout(width="300px"),
    )

    purpose_dd = _dropdown_from_list(purposes, "計算目的")
    method_dd = _dropdown_from_list(functionals, "計算手法")
    basis_dd = _dropdown_from_list(basis_items, "基底関数")

    charge_input = widgets.IntText(
        value=defaults["gui_defaults"]["charge"], description="電荷",
        style={"description_width": "140px"}, layout=widgets.Layout(width="220px"),
    )
    mult_input = widgets.IntText(
        value=defaults["gui_defaults"]["multiplicity"], description="スピン多重度",
        style={"description_width": "140px"}, layout=widgets.Layout(width="220px"),
    )
    freq_checkbox = widgets.Checkbox(
        value=defaults["gui_defaults"]["do_frequency"],
        description="振動数計算も実行する(既定でON)",
    )
    gpu_checkbox = widgets.Checkbox(
        value=defaults["gpu"]["try_gpu4pyscf"],
        description="可能ならGPU(GPU4PySCF)を使う(未対応環境では自動的にCPUで実行されます)",
    )

    input_box = widgets.VBox([
        title,
        widgets.HTML("<h4>① 構造ファイルと計算条件</h4>"),
        upload,
        purpose_dd, method_dd, basis_dd,
        widgets.HBox([charge_input, mult_input]),
        freq_checkbox,
        gpu_checkbox,
    ])

    # --- ② 実行ボタン・ログ ------------------------------------------------
    run_button = widgets.Button(description="計算を実行する", button_style="primary",
                                 layout=widgets.Layout(width="200px"))
    log_output = widgets.Output(layout=widgets.Layout(border="1px solid #ccc", padding="6px"))

    # --- ③ 可視化エリア ---------------------------------------------------
    viz_header = widgets.HTML("<h4>③ 可視化</h4>")
    energy_output = widgets.Output()
    traj_output = widgets.Output()

    vib_mode_dd = widgets.Dropdown(description="振動モード", options=[], disabled=True,
                                    style={"description_width": "140px"}, layout=widgets.Layout(width="420px"))
    vib_button = widgets.Button(description="振動アニメーションを表示", disabled=True)
    vib_output = widgets.Output()

    mo_dd = widgets.Dropdown(description="分子軌道", options=[], disabled=True,
                              style={"description_width": "140px"}, layout=widgets.Layout(width="420px"))
    mo_button = widgets.Button(description="分子軌道を表示", disabled=True)
    mo_output = widgets.Output()

    density_button = widgets.Button(description="原子電荷を表示", disabled=True)
    density_output = widgets.Output()

    viz_box = widgets.VBox([
        viz_header,
        widgets.HTML("<b>エネルギー収束</b>"), energy_output,
        widgets.HTML("<b>構造最適化の軌跡(アニメーション)</b>"), traj_output,
        widgets.HTML("<b>振動アニメーション</b>"), widgets.HBox([vib_mode_dd, vib_button]), vib_output,
        widgets.HTML("<b>分子軌道</b>"), widgets.HBox([mo_dd, mo_button]), mo_output,
        widgets.HTML("<b>原子電荷(Mulliken電荷)</b>"), density_button, density_output,
    ])

    # --- ④ ダウンロードエリア ------------------------------------------------
    download_header = widgets.HTML("<h4>④ ダウンロード</h4>")
    download_output = widgets.Output()
    download_box = widgets.VBox([download_header, download_output])

    state = {}  # 計算結果をウィジェット間で共有するための入れ物

    # -------------------------------------------------------------------
    # 可視化の描画
    # -------------------------------------------------------------------
    def _render_energy_and_trajectory():
        opt_result = state["opt_result"]
        with energy_output:
            clear_output(wait=True)
            try:
                png_bytes = visualizer.energy_convergence_png(opt_result.energies)
                # 画像自体は綺麗にレイアウトされたサイズ(700x400相当)で生成し、
                # 表示サイズ(width/height)だけをここで縮小する
                # (画像データ自体を小さくするとグラフ内の文字が崩れるため)。
                display(Image(data=png_bytes, width=460, height=270))
            except Exception as e:
                # kaleidoが使えない等の理由でPNG化に失敗した場合のフォールバック。
                print(f"(静的画像への変換に失敗したため、HTML表示にフォールバックします: {e})")
                html_str = visualizer.energy_convergence_html(opt_result.energies)
                display(HTML(html_str))
        with traj_output:
            clear_output(wait=True)
            view = visualizer.render_trajectory(
                opt_result.symbols, opt_result.coords_history, opt_result.energies)
            view.show()

    def _setup_vibration_controls():
        freq_result = state.get("freq_result")
        if freq_result is None or freq_result.normal_modes is None:
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
            view, label = visualizer.render_vibration(
                state["final_symbols"], state["final_coords"],
                freq_result.frequencies_cm1, freq_result.normal_modes,
                mode_index=vib_mode_dd.value,
            )
            print(label)
            view.show()

    def _setup_mo_controls():
        mf_final = state["mf_final"]
        options, homo_idx = _homo_lumo_window(mf_final)
        mo_dd.options = options
        mo_dd.value = homo_idx
        mo_dd.disabled = False
        mo_button.disabled = False
        density_button.disabled = False

    def _on_mo_button_clicked(_):
        with mo_output:
            clear_output(wait=True)
            view = visualizer.render_orbital(state["final_mol"], state["mf_final"], mo_dd.value)
            view.show()

    def _on_density_button_clicked(_):
        with density_output:
            clear_output(wait=True)
            mol_final = state["final_mol"]
            mf_final = state["mf_final"]
            charges = visualizer.compute_mulliken_charges(mol_final, mf_final)
            display(widgets.HTML(
                "<b>原子ごとのMulliken電荷</b>(3D図中の数値ラベルにも同じ値を表示しています)" +
                visualizer.atomic_charges_table_html(charges)))
            view = visualizer.render_charges(mol_final, charges)
            view.show()

    vib_button.on_click(_on_vib_button_clicked)
    mo_button.on_click(_on_mo_button_clicked)
    density_button.on_click(_on_density_button_clicked)

    # -------------------------------------------------------------------
    # ダウンロードリンクの用意
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
                print(f"・molden: {state['molden_path']}")
                return

            # (説明ラベル, 元ファイルのパス, 付与する拡張子/サフィックス, ボタンラベル)
            items = [
                ("最終構造(ColabReactionにそのままアップロード可能)",
                 state["final_xyz_path"], ".xyz", ".xyz"),
                ("最適化トラジェクトリ(多フレーム)",
                 state["traj_xyz_path"], "_traj.xyz", "_traj.xyz"),
                ("分子軌道・構造(molden)",
                 state["molden_path"], ".molden", ".molden"),
            ]

            # ファイル名入力欄は1つだけ用意し、3つのボタン全てで共有する
            # (「.xyz」「_traj.xyz」「.molden」を同じ名前に対して付与する)。
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
                        tmp_dir = tempfile.mkdtemp(prefix="qchem_dl_")
                        dst_path = os.path.join(tmp_dir, filename)
                        import shutil
                        shutil.copyfile(src_path, dst_path)
                        colab_files.download(dst_path)
                    return _handler

                button.on_click(_make_handler())
                rows.append(widgets.HBox([
                    widgets.HTML(f"<div style='width:280px'>{description}</div>"),
                    button,
                ]))

            display(widgets.VBox(rows))

    # -------------------------------------------------------------------
    # 実行ボタンのハンドラ(計算パイプライン本体)
    # -------------------------------------------------------------------
    def on_run_clicked(_):
        with log_output:
            clear_output(wait=True)
            t_total_start = time.perf_counter()
            try:
                charge = int(charge_input.value)
                multiplicity = int(mult_input.value)
                basis_key = basis_dd.value
                functional_key = method_dd.value
                do_freq = bool(freq_checkbox.value)
                try_gpu = bool(gpu_checkbox.value)

                content_bytes = _extract_uploaded_bytes(upload)
                with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False, mode="wb") as tf:
                    tf.write(content_bytes)
                    tmp_path = tf.name

                structure = io_reader.read_xyz(tmp_path)
                print(f"[入力構造] 原子数: {len(structure.symbols)}  組成: "
                      f"{', '.join(sorted(set(structure.symbols)))}")

                io_reader.validate_structure(
                    structure, defaults["validation"]["min_interatomic_distance_angstrom"])
                io_reader.validate_charge_and_multiplicity(structure, charge, multiplicity)

                if io_reader.contains_transition_metal(structure):
                    raise io_reader.StructureError(
                        "アップロードされた構造に遷移金属元素が含まれています。\n"
                        "現在のプロトタイプ(HF/3-21G)は主要な典型元素(H〜Ar程度)"
                        "のみに対応しており、遷移金属の計算にはまだ対応していません。\n"
                        "今後のバージョンでECP付き基底関数(LANL2DZ等)を追加予定です。"
                    )

                mol = engine.build_mole(structure, charge, multiplicity, basis_key)

                print("\n--- 構造最適化を開始します ---")
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
                mf_final, _, _ = engine.build_scf(final_mol, functional_key, try_gpu=False)
                mf_final = engine.run_scf(mf_final, defaults)

                freq_result = None
                if do_freq:
                    print("\n--- 振動数計算を開始します ---")
                    freq_result = freq_module.run_frequency_analysis(mf_final, defaults)
                    print(f"  振動数計算 所要時間: {freq_result.elapsed_seconds:.1f} 秒")
                    if freq_result.warning_message:
                        print(f"  [注意] {freq_result.warning_message}")

                total_elapsed = time.perf_counter() - t_total_start
                label = "構造最適化 + 振動数計算" if do_freq else "構造最適化のみ"
                print(f"\n=== 合計所要時間({label}): {total_elapsed:.1f} 秒 ===")

                out_dir = tempfile.mkdtemp(prefix="qchem_output_")
                final_symbols = [final_mol.atom_symbol(i) for i in range(final_mol.natm)]
                final_coords = [list(c) for c in final_mol.atom_coords(unit="Angstrom")]

                final_xyz_path = os.path.join(out_dir, "final_structure_for_ColabReaction.xyz")
                writer_xyz.write_final_structure(final_symbols, final_coords, final_xyz_path)

                traj_xyz_path = os.path.join(out_dir, "optimization_trajectory.xyz")
                writer_xyz.write_trajectory(
                    opt_result.symbols, opt_result.coords_history, traj_xyz_path, opt_result.energies)

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

                _render_energy_and_trajectory()
                _setup_vibration_controls()
                _setup_mo_controls()
                _refresh_downloads()

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
