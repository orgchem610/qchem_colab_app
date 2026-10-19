"""
qchem_colab_app.gui.parts
-------------------------
gui/pyscf_calc.py(PySCF版)と gui/uma_calc.py(UMA版)で共通の、画面部品(ipywidgets)をまとめたモジュール。
計算エンジンには依存せず、次の「プレーンな値」だけを受け取る(疎結合)。

    StructureFileInput    構造ファイルの入力。Colabでは、ドラッグ&ドロップ領域(枠をクリックしても選べる)。
                          Colab以外では、ファイル選択ボタン。受け取ったファイルの構造は、その場で自動的に表示する
    EnergyStructureViewer エネルギー収束グラフ(点をクリック)+ スライダー + 構造表示
                          渡す結果: .energies[Hartree] / .coords_history[Å] / .symbols を持つ任意のオブジェクト
    VibrationViewer       振動モードの選択とアニメーション表示
                          渡す結果: .frequencies_cm1 / .normal_modes を持つ任意のオブジェクト
    DownloadPanel         ダウンロードボタン(ファイル名の入力欄つき)
    ChargeInput           電荷の入力欄(「+1」の形で表示。−1/+1ボタンつき)
    MultiplicityInput     スピン多重度の入力欄(電荷の入力欄と同じ行に並べる)

各部品は、画面に置くウィジェットを `.widget`(または `.widgets`)として公開し、
計算が終わった後に show() / setup() を呼んで中身を更新する。新しい計算を始めるときは、
reset() を呼んで、前回の結果の表示を消す。計算の結果をどう得るかは
呼び出し側(gui/pyscf_calc.py / gui/uma_calc.py)の責任で、部品は計算エンジンのパッケージをimportしない。

ドラッグ&ドロップとグラフのクリックは、gui/colab_widgets.py の
「ブラウザ側JavaScript → Colabのコールバック → Python」の仕組みで実現している。
Colab以外の環境では、ドロップ領域を出さず、通常のファイル選択ボタンとスライダーだけで動作する。

ipywidgets 7.x(Colab標準)・8.x のどちらでも動くように書いてある。
"""

import html
import os
import shutil
import tempfile

import ipywidgets as widgets
from IPython.display import display, clear_output, HTML, JSON

from qchem_colab_app.common_backend import energy, io_reader
from qchem_colab_app.gui import colab_widgets, energy_plot, inputs, outputs, plot_common


def dropdown_from_list(items, description, width="420px"):
    """[{"label":..., "key":...}, ...] からドロップダウンを作る(設定ファイルの選択肢用)。"""
    options = [(item["label"], item["key"]) for item in items]
    return widgets.Dropdown(
        options=options,
        description=description,
        style={"description_width": "140px"},
        layout=widgets.Layout(width=width),
    )


# -----------------------------------------------------------------------------
# 電荷の入力
# -----------------------------------------------------------------------------

# 計算条件の入力欄(電荷・スピン多重度)で共通の、見た目の寸法
_LABEL_WIDTH = "140px"
_INPUT_WIDTH = "220px"


class ChargeInput:
    """電荷の入力部品。正の値を「+1」のように符号付きで表示するため、数値ウィジェット(IntText)ではなく
    文字の入力欄(Text)にして、−1/+1ボタンを添えている。

    入力は「1」でも「+1」でもよく、Enterキーを押すか欄の外をクリックすると、「+1」の形に整えて
    表示し直す(0と負の値はそのまま表示)。整数として読み取れない入力は、直前の値に戻してメッセージを出す。

    controls : 入力欄と−1/+1ボタンを並べたHBox(スピン多重度の欄など、他の入力欄と同じ行に置ける)
    message  : 入力エラーのメッセージ欄(controlsの下に置く)
    value    : 現在の電荷(整数)
    """

    def __init__(self, value=0, description="電荷"):
        self._value = int(value)
        self._updating = False

        self.text = widgets.Text(
            value=inputs.format_charge(self._value), description=description,
            continuous_update=False,   # 入力の途中ではなく、Enterまたは欄の外へ移ったときに反映する
            style={"description_width": _LABEL_WIDTH}, layout=widgets.Layout(width=_INPUT_WIDTH),
        )
        self.minus_button = widgets.Button(
            description="−1", button_style="info", layout=widgets.Layout(width="48px"))
        self.plus_button = widgets.Button(
            description="+1", button_style="info", layout=widgets.Layout(width="48px"))
        self.message = widgets.HTML()
        self.controls = widgets.HBox([self.text, self.minus_button, self.plus_button])

        self.text.observe(self._on_text_changed, names="value")
        self.minus_button.on_click(lambda _: self._step(-1))
        self.plus_button.on_click(lambda _: self._step(+1))

    @property
    def value(self):
        return self._value

    def _on_text_changed(self, change):
        if change["name"] != "value" or self._updating:
            return
        try:
            self._value = inputs.parse_charge(change["new"])
            self.message.value = ""
        except inputs.ChargeInputError as e:
            self.message.value = f"<span style='color:#b42318'>{html.escape(str(e))}</span>"
        # 読み取れた場合は「+1」の形に整え、読み取れなかった場合は直前の値に戻す
        shown = inputs.format_charge(self._value)
        if self.text.value != shown:
            self._updating = True
            try:
                self.text.value = shown
            finally:
                self._updating = False

    def _step(self, delta):
        self.message.value = ""
        self.text.value = inputs.format_charge(self._value + delta)


class MultiplicityInput:
    """スピン多重度の入力部品(整数の入力欄)。

    電荷の入力欄(ChargeInput)と同じ幅・同じ説明欄の幅にそろえてあり、同じ行に並べて使う。
    値の範囲や、電子数との整合の確認は、この部品ではなく、計算前の検証
    (gui/inputs.load_uploaded_structure → io_reader)で行う。

    widget : 入力欄(ipywidgets.IntText)
    value  : 現在のスピン多重度(整数)
    """

    def __init__(self, value=1, description="スピン多重度"):
        self.widget = widgets.IntText(
            value=int(value), description=description,
            style={"description_width": _LABEL_WIDTH}, layout=widgets.Layout(width=_INPUT_WIDTH),
        )

    @property
    def value(self):
        return int(self.widget.value)


# -----------------------------------------------------------------------------
# 構造ファイルの入力
# -----------------------------------------------------------------------------

class StructureFileInput:
    """構造ファイルの入力部品。Colabでは、ドラッグ&ドロップ領域(枠をクリックしてファイルを選ぶこともできる)だけを
    表示する。Colab以外の環境では、ドロップ領域が使えないため、ファイル選択ボタンを表示する
    (v0.2.2で、Colabでは、ドロップ領域の下のファイル選択ボタンを削除した。枠をクリックして選べるため)。

    widgets : 画面に並べるウィジェットのリスト(最後が、受け取った構造の表示欄)
    read()  : (ファイルの中身[bytes], ファイル名) を返す。選ばれていなければ io_reader.StructureError

    ファイルを受け取ると(ドロップ・枠のクリック・ボタンのいずれでも)、その構造を、すぐ下の表示欄に自動で表示する
    (原子数・組成の概要と、3D表示)。読み込めない場合は、その理由を表示する(計算の前に、
    構造ファイルの内容を目で確認できるようにするため)。
    """

    def __init__(self, callback_prefix="qchem_drop"):
        self._dropped_file = None
        self._status = widgets.HTML(
            "<span style='color:#666'>ファイルはまだ選択されていません。</span>")

        self._drop_callback = colab_widgets.register_callback(
            self._on_file_dropped, prefix=callback_prefix)
        self._drop_zone_output = widgets.Output()
        if self._drop_callback is not None:
            # JavaScriptを含むHTMLは、ipywidgets.HTMLのvalueではなく
            # Output内でdisplay(HTML(...))して表示する(scriptが実行されるため)。
            with self._drop_zone_output:
                display(HTML(colab_widgets.build_drop_zone_html(self._drop_callback)))

        # ファイル選択ボタン。画面に置くのは、Colab以外の環境だけ(Colabでは、ドロップ領域をクリックしても
        # 選べるため、置かない)。Colabでも、値の取り出し(read)の仕組みを共通にするため、部品自体は作っておく。
        self.upload = widgets.FileUpload(
            accept=".xyz,.com,.gjf,.pdb", multiple=False,
            description="構造ファイル(.xyz/.com/.gjf/.pdb)",
            layout=widgets.Layout(width="320px"),
        )
        self.upload.observe(self._on_upload_changed, names="value")

        if self._drop_callback is not None:
            hint_text = ("上の枠にファイルをドラッグ＆ドロップするか、枠をクリックしてファイルを選択してください。"
                         "続けて選び直した場合は、最後に選んだファイルが使われます。")
        else:
            hint_text = "ボタンをクリックして構造ファイルを選択してください。"
        hint = widgets.HTML(
            f"<p style='color:#666'>{hint_text}"
            "対応形式: .xyz, .com, .gjf, .pdb(.mol/.sdfは現時点では未対応です)</p>"
        )

        self.preview_output = widgets.Output()   # 受け取った構造の表示欄

        if self._drop_callback is not None:
            self.widgets = [self._drop_zone_output, self._status, hint, self.preview_output]
        else:
            self.widgets = [self.upload, hint, self.preview_output]

    def _on_file_dropped(self, payload):
        """JavaScript(ドロップ領域)から呼ばれる。ファイルを検証して保存する。"""
        try:
            name, content = colab_widgets.parse_dropped_payload(payload)
            self._dropped_file = {"name": name, "content": content}
            self._status.value = (
                f"<span style='color:#167a2e'>✓ {html.escape(name)} を受け取りました"
                f"({len(content):,} バイト)。</span>")
        except ValueError as e:
            self._dropped_file = None
            self._status.value = (
                "<span style='color:#b42318'>ドロップされたファイルを受け取れませんでした: "
                f"{html.escape(str(e))}</span>")
            self._clear_preview()
            return JSON({"ok": True})
        self._update_preview()
        return JSON({"ok": True})

    def _on_upload_changed(self, change):
        # ボタンで選び直した場合は、そちらを優先する(最後に選んだファイルを使う)
        if change["name"] == "value" and change["new"]:
            self._dropped_file = None
            self._status.value = (
                "<span style='color:#666'>「構造ファイル」ボタンで選んだファイルを使用します。</span>")
            self._update_preview()
        elif change["name"] == "value":
            self._clear_preview()

    def _clear_preview(self):
        with self.preview_output:
            clear_output()

    def _update_preview(self):
        """受け取った構造ファイルを読み込んで、概要と3D表示を出す。読み込めない場合は理由を表示する。"""
        with self.preview_output:
            clear_output(wait=True)
            try:
                content, name = self.read()
                structure = inputs.read_uploaded_structure(content, name)
                print(f"[受け取った構造] {inputs.describe_structure(structure, name)}")
                view = plot_common.render_single_structure(structure.symbols, structure.coords)
                view.show()
            except (io_reader.StructureError, ValueError) as e:
                print("構造を表示できませんでした。ファイルの形式・内容をご確認ください:")
                print(str(e))
            except Exception as e:  # 表示のための処理が、ファイルの受け取りを妨げないようにする
                print(f"構造を表示できませんでした(内部エラー: {type(e).__name__}: {e})")

    def read(self):
        return inputs.extract_uploaded_file(self.upload, self._dropped_file)


# -----------------------------------------------------------------------------
# エネルギー収束グラフ + 構造表示
# -----------------------------------------------------------------------------

def default_step_label(step_index, relative_energy_kcal, result):
    return f"ステップ {step_index}: 相対エネルギー {relative_energy_kcal:+.2f} kcal/mol"


class EnergyStructureViewer:
    """エネルギー収束グラフ(点をクリックできるSVG)・スライダー・構造表示をまとめた部品。

    グラフの点をクリックするとその点の構造が下に表示される(Colab以外ではクリックは効かず、
    スライダーで切り替える)。選択中の点は赤い菱形で強調される。

    step_label : 構造表示の見出しを作る関数 f(ステップ番号, 相対エネルギー[kcal/mol], 結果) -> 文字列。
                 計算エンジンごとに見出しに足したい情報(力の最大値など)があるときに差し替える。
    show(result) : 結果を受け取って、グラフと構造を表示する。
    """

    def __init__(self, callback_prefix="qchem_plot", step_label=None):
        self._step_label = step_label or default_step_label
        self._result = None
        self._n_steps = 0
        self._suppress_plot_redraw = False

        self.energy_output = widgets.Output()
        self.plot_status = widgets.HTML()  # クリック処理でPython側に問題が起きたときのメッセージ用
        self.slider = widgets.IntSlider(
            description="ステップ", min=0, max=0, value=0, disabled=True,
            style={"description_width": "70px"}, layout=widgets.Layout(width="420px"),
        )
        self.step_view_output = widgets.Output()
        self.slider.observe(self._on_slider_changed, names="value")
        self._plot_callback = colab_widgets.register_callback(
            self._on_plot_clicked, prefix=callback_prefix)

        self.widget = widgets.VBox([
            widgets.HTML(
                "<b>エネルギー収束</b>"
                "<p style='color:#666;margin:2px 0'>グラフ上の点をクリックすると、"
                "対応する構造を下に表示します(お使いの環境でクリックが効かない場合は、"
                "代わりにスライダーで同じことができます)。</p>"
            ),
            self.energy_output, self.plot_status, self.slider, self.step_view_output,
        ])

    def show(self, result):
        self._result = result
        # エネルギーと座標が対になっている点だけを扱う。計算エンジンのcallback実装の差で
        # 片方だけが1点多く記録されても、対応関係を崩さない。
        n_steps = min(len(result.energies), len(result.coords_history))
        self._n_steps = n_steps
        self.plot_status.value = ""

        if n_steps == 0:
            with self.energy_output:
                clear_output(wait=True)
                print("エネルギーと構造の履歴が記録されていないため、グラフを表示できません。")
            self.slider.disabled = True
            return

        last = n_steps - 1
        # スライダーを動かすと observer が走る(構造を表示する)。グラフの描き直しは
        # 最後に1回だけ行うため、ここではグラフの再描画だけ止めておく。
        previous_value = self.slider.value
        self._suppress_plot_redraw = True
        try:
            self.slider.max = last
            self.slider.value = last
        finally:
            self._suppress_plot_redraw = False
        self.slider.disabled = (n_steps <= 1)
        self._draw_energy_plot(last)
        if self.slider.value == previous_value:
            # スライダーの値が変わらなかった場合は observer が走らないため、ここで構造を表示する
            self._show_structure_at_step(last)

    def reset(self):
        """前回の結果の表示(グラフ・構造・スライダー)をすべて消す。新しい計算を始めるときに呼ぶ。"""
        self._result = None
        self._n_steps = 0
        self._suppress_plot_redraw = True
        try:
            self.slider.value = 0
            self.slider.max = 0
        finally:
            self._suppress_plot_redraw = False
        self.slider.disabled = True
        self.plot_status.value = ""
        with self.energy_output:
            clear_output()
        with self.step_view_output:
            clear_output()

    def _show_structure_at_step(self, step_index):
        result = self._result
        # グラフに載せているのは「エネルギーと座標が対になっている点」だけ(n_steps個)。
        n_steps = self._n_steps or len(result.coords_history)
        step_index = max(0, min(int(step_index), n_steps - 1))
        with self.step_view_output:
            clear_output(wait=True)
            e_rel_kcal = ((result.energies[step_index] - result.energies[n_steps - 1])
                          * energy.HARTREE_TO_KCAL_MOL)
            print(self._step_label(step_index, e_rel_kcal, result))
            view = plot_common.render_single_structure(
                result.symbols, result.coords_history[step_index])
            view.show()

    def _draw_energy_plot(self, selected_index):
        """グラフを描き直す。selected_index の点が赤い菱形で強調される。"""
        energies = list(self._result.energies[:self._n_steps])
        with self.energy_output:
            clear_output(wait=True)
            try:
                display(HTML(energy_plot.build_energy_plot_html(
                    energies, selected_index=selected_index, callback_name=self._plot_callback)))
            except Exception as e:
                print(f"(グラフを描画できませんでした。下のスライダーで構造を切り替えられます。詳細: {e})")

    def _on_slider_changed(self, change):
        if change["name"] != "value" or self._result is None:
            return
        self._show_structure_at_step(change["new"])
        # 点のクリックが原因の変更では、JavaScript側が既に赤い菱形を動かしているため描き直さない
        if not self._suppress_plot_redraw:
            self._draw_energy_plot(change["new"])

    def _on_plot_clicked(self, index):
        """JavaScript(グラフ上の点のクリック)から呼ばれる。点の番号 index の構造を表示する。"""
        try:
            if self._result is None or self._n_steps <= 0:
                return JSON({"ok": False})
            index = max(0, min(int(index), self._n_steps - 1))
            self.plot_status.value = ""
            self._suppress_plot_redraw = True
            try:
                if self.slider.value != index:
                    self.slider.value = index  # → _on_slider_changed が構造を表示する
                else:
                    self._show_structure_at_step(index)
            finally:
                self._suppress_plot_redraw = False
        except Exception as e:
            self.plot_status.value = (
                "<span style='color:#b42318'>構造の表示に失敗しました。"
                f"スライダーをご利用ください。詳細: {html.escape(str(e))}</span>")
        return JSON({"ok": True})


# -----------------------------------------------------------------------------
# 振動アニメーション
# -----------------------------------------------------------------------------

class VibrationViewer:
    """振動モードを選んで、アニメーションを表示する部品。

    setup(freq_result, symbols, coords) : 振動数解析の結果(.frequencies_cm1 / .normal_modes を持つ
        オブジェクト。計算していない場合は None)と、振動させる構造を受け取って、選択肢を更新する。
        前回のアニメーションの表示は、このとき消す。
    reset() : 前回の結果の表示をすべて消す(新しい計算を始めるとき)。
    """

    def __init__(self):
        self._freq_result = None
        self._symbols = None
        self._coords = None
        self.mode_dropdown = widgets.Dropdown(
            description="振動モード", options=[], disabled=True,
            style={"description_width": "140px"}, layout=widgets.Layout(width="420px"))
        self.button = widgets.Button(description="振動アニメーションを表示", disabled=True)
        self.output = widgets.Output()
        self.button.on_click(self._on_button_clicked)
        self.widget = widgets.VBox([
            widgets.HTML("<b>振動アニメーション</b>"),
            widgets.HBox([self.mode_dropdown, self.button]),
            self.output,
        ])

    def reset(self):
        self.setup(None, None, None)

    def setup(self, freq_result, symbols, coords):
        self._freq_result = freq_result
        self._symbols = symbols
        self._coords = coords
        with self.output:
            clear_output()       # 前回のアニメーションを残さない
        if (freq_result is None or freq_result.normal_modes is None
                or not len(freq_result.frequencies_cm1)):
            self.mode_dropdown.options = []
            self.mode_dropdown.disabled = True
            self.button.disabled = True
            return
        options = []
        for i, f in enumerate(freq_result.frequencies_cm1):
            tag = "(虚振動)" if f < 0 else ""
            options.append((f"モード{i + 1}: {f:.1f} cm⁻¹ {tag}", i))
        self.mode_dropdown.options = options
        self.mode_dropdown.value = 0 if options else None
        self.mode_dropdown.disabled = False
        self.button.disabled = False

    def _on_button_clicked(self, _):
        freq_result = self._freq_result
        with self.output:
            clear_output(wait=True)
            view, label = plot_common.render_vibration(
                self._symbols, self._coords,
                freq_result.frequencies_cm1, freq_result.normal_modes,
                mode_index=self.mode_dropdown.value,
            )
            print(label)
            view.show()


# -----------------------------------------------------------------------------
# ダウンロード
# -----------------------------------------------------------------------------

class DownloadPanel:
    """ダウンロードボタンの一覧(ファイル名の入力欄は1つだけで、全てのボタンで共有する)。

    show(items, default_stem) の items は、次の形のタプルのリスト:
        (説明, 元ファイルのパス, 付与するサフィックス, Colab以外で表示するときの短い名前)
    サフィックスは、ボタンのラベルにもなる(例: ".xyz"、"_traj.xyz")。
    default_stem は、ファイル名の入力欄の既定値(空なら、プレースホルダーの「result」が使われる)。
    """

    def __init__(self, tmp_prefix="qchem_dl_", description_width="280px"):
        self._tmp_prefix = tmp_prefix
        self._description_width = description_width
        self._output = widgets.Output()
        self.widget = widgets.VBox([widgets.HTML("<h4>④ ダウンロード</h4>"), self._output])

    def reset(self):
        """前回のダウンロードボタンを消す。新しい計算を始めるときに呼ぶ。"""
        with self._output:
            clear_output()

    def show(self, items, default_stem=""):
        with self._output:
            clear_output(wait=True)
            try:
                from google.colab import files as colab_files
            except ImportError:
                colab_files = None

            if colab_files is None:
                print(
                    "(Google Colab以外の環境で実行しているため自動ダウンロードは"
                    "行いません。以下のパスから直接ファイルを取得してください。)"
                )
                for _description, src_path, _suffix, short_name in items:
                    print(f"・{short_name}: {src_path}")
                return

            # ファイル名入力欄は1つだけ用意し、全てのボタンで共有する
            # (同じ名前に、それぞれのサフィックスを付与する)。空にした場合は「result」になる。
            name_input = widgets.Text(
                value=default_stem,
                placeholder="result",
                description="ファイル名",
                style={"description_width": "70px"},
                layout=widgets.Layout(width="240px"),
            )

            rows = [name_input]
            for description, src_path, suffix, _short_name in items:
                button = widgets.Button(description=suffix, layout=widgets.Layout(width="110px"))

                def _make_handler(src_path=src_path, suffix=suffix):
                    def _handler(_):
                        stem = outputs.sanitize_filename_stem(name_input.value)
                        tmp_dir = tempfile.mkdtemp(prefix=self._tmp_prefix)
                        dst_path = os.path.join(tmp_dir, f"{stem}{suffix}")
                        shutil.copyfile(src_path, dst_path)
                        colab_files.download(dst_path)
                    return _handler

                button.on_click(_make_handler())
                rows.append(widgets.HBox([
                    widgets.HTML(
                        f"<div style='width:{self._description_width}'>{description}</div>"),
                    button,
                ]))

            display(widgets.VBox(rows))
