"""
gui_uma.py
----------
UMA(機械学習ポテンシャル)版のGUI組み立て(ColabApp_UMA.ipynb のエントリーポイント)。

PySCF版の gui.py とは別ファイルになっており、お互いに影響しない。
計算の流れ(アクセス権の確認 → モデルの読み込み → 構造最適化 → 振動数解析 → 出力ファイルの書き出し)は
uma_backend/uma_pipeline.py に委譲し、このファイルは、入力値の収集、アップロードされたファイルの
読み込みと検証、結果の表示、例外の利用者向けメッセージへの変換だけを行う。
(README.md「gui.pyをルート直下に置いている理由」のとおり、`gui.py` は `pyscf_backend` と `common`
から、`gui_uma.py` は `uma_backend` と `common` から、それぞれ必要な部品を組み合わせて
画面を組み立てる「アプリの組み立て役」。)

【PySCF版との違い】
    - 計算手法・基底関数の代わりに「UMAモデル」を選ぶ。
    - UMAのライセンス・引用などの情報は、このGUIには表示しない(ノートブック冒頭にまとめて表示する)。
    - 分子軌道・原子電荷・moldenの出力はない(UMAは電子状態を返さないため)。
    - 振動数計算は、構造最適化の後処理として行う(PySCF版と同じ位置づけ)。
    - Hugging Faceのトークンは、このGUIでは一切扱わない。ノートブックの「2.」のセルが
      環境変数 HF_TOKEN に設定し、uma_hf がそれを読み取る(入力欄をGUIに置くと、
      入力値がウィジェットの状態として保持され、保存されるノートブックに残りうるため)。

【ipywidgetsの版について】
    Colabのランタイムにはipywidgets 7.7.1が入っており、Colab標準のGUI表示の仕組みは7.x向け
    (8.xに更新すると、GUI部品が表示されず「コードスニペット」のパネルが開くだけになる)。
    このファイルは7.x・8.xのどちらでも動くように書いてあり、requirements-uma.txt では
    ipywidgetsの版を指定していない。8.xが入っている場合の対処は ColabApp_UMA.ipynb の
    「II-0」のセルを参照。

【PySCF版と共通の部品】(どちらも common/ にある)
    画面部品: 構造ファイルの入力(ドラッグ&ドロップ)・エネルギーグラフ(点のクリック)・
              振動アニメーション・ダウンロード・電荷とスピン多重度の入力欄(common/gui_parts.py)
    補助関数: アップロードされたファイルの取り出し・読み込みと検証・ダウンロードのファイル名・
              電荷の表示と読み取り(common/gui_input.py・common/gui_output.py)
    そのほか: 構造ファイルの読み込み・検証(common/io_reader.py)、xyz出力(common/writer_xyz.py)、
              構造・振動の3D表示(common/plot_common.py)
    このファイルには、UMA版にしかない部分(モデルの選択、UMAの呼び出し)だけを残している。

使い方(ColabApp_UMA.ipynbから):
    import gui_uma
    app = gui_uma.build_app()
    display(app)
"""

import traceback

import ipywidgets as widgets
from IPython.display import clear_output

from uma_backend import load_yaml, __version__
from uma_backend import uma_hf, uma_pipeline
from common import io_reader, gui_parts, gui_input, gui_output


# -----------------------------------------------------------------------------
# GUI本体
# -----------------------------------------------------------------------------

def build_app():
    models = load_yaml("uma_models.yaml")
    defaults = load_yaml("uma_defaults.yaml")
    gui_defaults = defaults["gui_defaults"]

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
    mult_input = gui_parts.MultiplicityInput(value=gui_defaults["multiplicity"])
    freq_checkbox = widgets.Checkbox(
        value=gui_defaults["do_frequency"],
        description="振動数計算も実行する",
    )

    input_box = widgets.VBox([
        title,
        widgets.HTML("<h4>① 構造ファイルと計算条件</h4>"),
        *file_input.widgets,
        model_dd,
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

    def _reset_results():
        """前回の計算結果の表示を、すべて消す(新しい結果と混ざらないように、計算の開始時に呼ぶ)。"""
        energy_viewer.reset()
        vib_viewer.reset()
        downloads.reset()

    def _run_pipeline():
        with log_output:
            clear_output(wait=True)
            _reset_results()
            try:
                charge = charge_input.value
                multiplicity = int(mult_input.value)

                content_bytes, uploaded_filename = file_input.read()
                structure = gui_input.load_uploaded_structure(
                    content_bytes, uploaded_filename, charge, multiplicity,
                    defaults["validation"]["min_interatomic_distance_angstrom"])

                settings = uma_pipeline.CalculationSettings(
                    charge=charge, multiplicity=multiplicity, model_key=model_dd.value,
                    do_frequency=bool(freq_checkbox.value), input_filename=uploaded_filename)
                result = uma_pipeline.run_calculation(structure, settings, defaults)

                print("\n計算が完了しました。下の「③ 可視化」「④ ダウンロード」をご確認ください。")

                energy_viewer.show(result.opt_result)
                vib_viewer.setup(result.freq_result, result.final_symbols, result.final_coords)
                downloads.show(
                    [
                        *gui_output.xyz_download_items(result.final_xyz_path, result.traj_xyz_path),
                        ("計算ログ(条件・履歴・振動数・UMAに関する情報)",
                         result.log_path, "_log.txt", "計算ログ"),
                    ],
                    default_stem=gui_output.default_download_stem(uploaded_filename),
                )

            except (io_reader.StructureError, ValueError) as e:
                print("\n❌ 入力内容にエラーがあります:")
                print(str(e))
            except uma_hf.UmaSetupError as e:
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
