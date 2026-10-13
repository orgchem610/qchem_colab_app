"""
tests/test_gui_parts.py
-----------------------
common/gui_parts.py(PySCF版 gui.py とUMA版 gui_uma.py で共通の画面部品)の単体テスト。

ipywidgets・Google Colab・py3Dmolの代わりに、tests/fake_gui_env.py の簡易な代用品を使う。
ウィジェットの値の更新・observeの呼び出し・Outputへの表示・Colabのコールバックの登録といった
「部品どうしのつなぎ方」を確認するもので、実際の見た目やJavaScriptの動作の確認(Colab実機)の代わりにはならない。
"""

import base64
import contextlib
import io
import os
import re
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.dirname(__file__))

from fake_gui_env import fake_gui_env  # noqa: E402
from common import io_reader  # noqa: E402

XYZ = b"3\nwater\nO 0.0 0.0 0.0\nH 0.96 0.0 0.0\nH -0.24 0.93 0.0\n"


def _payload(name, content=XYZ):
    return {"name": name, "content_b64": base64.b64encode(content).decode("ascii")}


def _result(n_energies=6, n_coords=7):
    return SimpleNamespace(
        symbols=["O", "H", "H"],
        energies=[-76.0 - 0.02 * (1 - 0.7 ** i) for i in range(n_energies)],
        coords_history=[[[0.0, 0.0, 0.1 * i]] * 3 for i in range(n_coords)],
        fmax_history=[1.0 / (i + 1) for i in range(max(n_energies, n_coords))],
    )


def _capture(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(*args, **kwargs)
    return buf.getvalue()


class _Base(unittest.TestCase):
    colab = True

    def setUp(self):
        self._ctx = fake_gui_env(colab=self.colab)
        self.env = self._ctx.__enter__()
        self.gp = self.env.import_module("common.gui_parts")
        self.shown = []

        class _View:
            def show(inner):
                self.shown.append(1)

        self._patches = [
            mock.patch.object(self.gp.plot_common, "render_single_structure",
                              lambda symbols, coords: _View()),
            mock.patch.object(self.gp.plot_common, "render_vibration",
                              lambda *a, **k: (_View(), "振動数 1600.0 cm⁻¹")),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self._ctx.__exit__(None, None, None)


class TestStructureFileInputInColab(_Base):
    def setUp(self):
        super().setUp()
        self.inp = self.gp.StructureFileInput(callback_prefix="test_drop")
        self.drop = next(fn for name, fn in self.env.callbacks.items() if name.startswith("test_drop"))

    def test_drop_zone_is_shown_and_connected_to_the_registered_callback(self):
        callback_name = next(iter(self.env.callbacks))
        drop_zone = self.inp.widgets[0]
        self.assertIn(callback_name, drop_zone.outputs[0].data)
        self.assertIn("ドラッグ＆ドロップ", drop_zone.outputs[0].data)

    def test_read_before_any_file_raises_a_helpful_error(self):
        with self.assertRaises(io_reader.StructureError):
            self.inp.read()

    def test_dropped_file_is_returned_by_read(self):
        result = self.drop(_payload("water.xyz"))
        self.assertEqual(result.data, {"ok": True})
        self.assertEqual(self.inp.read(), (XYZ, "water.xyz"))
        self.assertIn("water.xyz", self.inp.widgets[1].value)

    def test_invalid_drop_is_reported_and_discards_the_previous_file(self):
        self.drop(_payload("water.xyz"))
        self.drop(_payload("notes.txt"))
        self.assertIn("対応形式", self.inp.widgets[1].value)
        with self.assertRaises(io_reader.StructureError):
            self.inp.read()

    def test_the_last_selected_file_wins(self):
        self.drop(_payload("dropped.xyz"))
        self.inp.upload.value = ({"name": "button.xyz", "content": b"b", "type": "", "size": 1},)
        self.assertEqual(self.inp.read(), (b"b", "button.xyz"))        # ボタンで選び直した
        self.drop(_payload("dropped_again.xyz"))
        self.assertEqual(self.inp.read(), (XYZ, "dropped_again.xyz"))  # もう一度ドロップした


class TestStructureFileInputOutsideColab(_Base):
    colab = False

    def test_no_drop_zone_and_no_callback_outside_colab(self):
        inp = self.gp.StructureFileInput()
        self.assertEqual(self.env.callbacks, {})
        self.assertEqual(len(inp.widgets), 2)              # ファイル選択ボタンと説明だけ
        self.assertIn("ボタンをクリック", inp.widgets[1].value)

    def test_upload_button_still_works(self):
        inp = self.gp.StructureFileInput()
        inp.upload.value = ({"name": "a.xyz", "content": XYZ, "type": "", "size": len(XYZ)},)
        self.assertEqual(inp.read(), (XYZ, "a.xyz"))


class TestEnergyStructureViewer(_Base):
    def setUp(self):
        super().setUp()
        self.viewer = self.gp.EnergyStructureViewer(callback_prefix="test_plot")
        self.click = next(fn for name, fn in self.env.callbacks.items() if name.startswith("test_plot"))

    def _plot_html(self):
        return self.viewer.energy_output.outputs[0].data

    def test_show_uses_only_points_that_have_both_energy_and_coordinates(self):
        out = _capture(self.viewer.show, _result(n_energies=6, n_coords=7))
        self.assertEqual(self._plot_html().count('class="qc-hit"'), 6)
        self.assertEqual((self.viewer.slider.max, self.viewer.slider.value), (5, 5))
        self.assertFalse(self.viewer.slider.disabled)
        self.assertIn("ステップ 5: 相対エネルギー +0.00 kcal/mol", out)
        self.assertEqual(len(self.shown), 1)               # 構造の描画は1回だけ

    def test_plot_is_connected_to_the_click_callback(self):
        _capture(self.viewer.show, _result())
        callback_name = next(n for n in self.env.callbacks if n.startswith("test_plot"))
        self.assertIn(callback_name, self._plot_html())

    def test_click_moves_the_slider_and_shows_that_structure_without_redrawing_the_plot(self):
        _capture(self.viewer.show, _result())
        before = self.viewer.energy_output.outputs[0]
        out = _capture(self.click, 2)
        self.assertEqual(self.viewer.slider.value, 2)
        self.assertIn("ステップ 2", out)
        self.assertIs(self.viewer.energy_output.outputs[0], before)   # 赤い菱形はJavaScript側が動かす

    def test_clicking_the_shown_point_again_shows_the_structure_again(self):
        _capture(self.viewer.show, _result())
        _capture(self.click, 2)
        count = len(self.shown)
        _capture(self.click, 2)
        self.assertEqual(len(self.shown), count + 1)

    def test_click_index_is_clamped(self):
        _capture(self.viewer.show, _result())
        _capture(self.click, 999)
        self.assertEqual(self.viewer.slider.value, 5)
        _capture(self.click, -4)
        self.assertEqual(self.viewer.slider.value, 0)

    def test_click_before_show_is_ignored(self):
        self.assertEqual(self.click(1).data, {"ok": False})

    def test_moving_the_slider_redraws_the_plot_with_the_new_marker(self):
        _capture(self.viewer.show, _result())
        before = self._plot_html()
        _capture(setattr, self.viewer.slider, "value", 3)
        after = self._plot_html()
        pattern = r'-sel" transform="([^"]+)"'
        self.assertNotEqual(re.search(pattern, before).group(1), re.search(pattern, after).group(1))

    def test_failure_to_draw_the_structure_is_reported_next_to_the_plot(self):
        _capture(self.viewer.show, _result())
        with mock.patch.object(self.gp.plot_common, "render_single_structure",
                               side_effect=RuntimeError("テスト用の例外")):
            _capture(self.click, 1)
        self.assertIn("構造の表示に失敗", self.viewer.plot_status.value)
        self.assertIn("テスト用の例外", self.viewer.plot_status.value)

    def test_custom_step_label_is_used(self):
        viewer = self.gp.EnergyStructureViewer(
            callback_prefix="test_plot2",
            step_label=lambda i, e, r: f"独自の見出し {i} / fmax {r.fmax_history[i]:.2f}")
        out = _capture(viewer.show, _result())
        self.assertIn("独自の見出し 5 / fmax 0.17", out)

    def test_rerun_with_fewer_steps_resets_the_slider(self):
        _capture(self.viewer.show, _result(6, 6))
        _capture(self.viewer.show, _result(3, 3))
        self.assertEqual((self.viewer.slider.max, self.viewer.slider.value), (2, 2))
        self.assertEqual(self._plot_html().count('class="qc-hit"'), 3)

    def test_empty_history_shows_a_message_and_disables_the_slider(self):
        out = _capture(self.viewer.show, _result(0, 0))
        self.assertTrue(self.viewer.slider.disabled)
        self.assertEqual(len(self.viewer.energy_output.outputs), 0)
        self.assertIn("履歴が記録されていない", out)


class TestVibrationViewer(_Base):
    def setUp(self):
        super().setUp()
        self.viewer = self.gp.VibrationViewer()

    def test_controls_are_disabled_when_no_frequency_calculation_was_done(self):
        self.viewer.setup(None, ["O", "H", "H"], [[0, 0, 0]] * 3)
        self.assertTrue(self.viewer.button.disabled)
        self.assertTrue(self.viewer.mode_dropdown.disabled)

    def test_controls_are_disabled_when_there_are_no_modes(self):
        freq = SimpleNamespace(frequencies_cm1=[], normal_modes=None)
        self.viewer.setup(freq, ["H"], [[0, 0, 0]])
        self.assertTrue(self.viewer.button.disabled)

    def test_modes_are_listed_with_imaginary_ones_marked(self):
        freq = SimpleNamespace(frequencies_cm1=[-35.0, 1600.5, 3700.2], normal_modes=[0, 1, 2])
        self.viewer.setup(freq, ["O", "H", "H"], [[0, 0, 0]] * 3)
        labels = [label for label, _ in self.viewer.mode_dropdown.options]
        self.assertEqual(len(labels), 3)
        self.assertIn("虚振動", labels[0])
        self.assertNotIn("虚振動", labels[1])
        self.assertFalse(self.viewer.button.disabled)

    def test_button_shows_the_animation_and_its_label(self):
        freq = SimpleNamespace(frequencies_cm1=[1600.5], normal_modes=[0])
        self.viewer.setup(freq, ["O", "H", "H"], [[0, 0, 0]] * 3)
        out = _capture(self.viewer.button.click)
        self.assertIn("1600.0", out)
        self.assertEqual(len(self.shown), 1)


class TestDownloadPanelInColab(_Base):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.mkdtemp()
        self.items = []
        for suffix, short in ((".xyz", "最終構造"), ("_traj.xyz", "トラジェクトリ"), ("_log.txt", "計算ログ")):
            path = os.path.join(self.tmp, f"src{suffix}")
            with open(path, "w") as f:
                f.write("x")
            self.items.append((f"説明{short}", path, suffix, short))
        self.panel = self.gp.DownloadPanel(tmp_prefix="test_dl_")

    def _shown_rows(self):
        return self.panel._output.outputs[0].children

    def _name_input(self):
        return self._shown_rows()[0]

    def test_default_stem_is_put_in_the_name_input_and_placeholder_stays_result(self):
        self.panel.show(self.items, default_stem="water_result")
        self.assertEqual((self._name_input().value, self._name_input().placeholder), ("water_result", "result"))

    def test_empty_default_stem_keeps_the_input_empty(self):
        self.panel.show(self.items)
        self.assertEqual(self._name_input().value, "")

    def _buttons(self):
        return [row.children[1] for row in self._shown_rows()[1:]]

    def test_buttons_download_files_named_after_the_input_and_their_suffix(self):
        self.panel.show(self.items, default_stem="water_result")
        for button in self._buttons():
            button.click()
        self.assertEqual(self.env.downloaded, ["water_result.xyz", "water_result_traj.xyz", "water_result_log.txt"])

    def test_empty_name_falls_back_to_result_and_forbidden_characters_are_removed(self):
        self.panel.show(self.items, default_stem="water_result")
        self._name_input().value = ""
        self._buttons()[0].click()
        self._name_input().value = "my?name"
        self._buttons()[0].click()
        self.assertEqual(self.env.downloaded, ["result.xyz", "myname.xyz"])

    def test_showing_again_replaces_the_previous_buttons(self):
        self.panel.show(self.items, default_stem="a")
        self.panel.show(self.items, default_stem="b")
        self.assertEqual(len(self.panel._output.outputs), 1)
        self.assertEqual(self._name_input().value, "b")


class TestDownloadPanelOutsideColab(_Base):
    colab = False

    def test_paths_are_printed_instead_of_buttons(self):
        panel = self.gp.DownloadPanel()
        out = _capture(panel.show, [("説明", "/tmp/a.xyz", ".xyz", "最終構造"),
                                    ("説明", "/tmp/b.molden", ".molden", "molden")])
        self.assertIn("・最終構造: /tmp/a.xyz", out)
        self.assertIn("・molden: /tmp/b.molden", out)
        self.assertEqual(self.env.downloaded, [])


class TestDropdownFromList(_Base):
    def test_labels_and_keys_become_options(self):
        dd = self.gp.dropdown_from_list([{"label": "HF", "key": "hf"}, {"label": "B3LYP", "key": "b3lyp"}], "計算手法")
        self.assertEqual(dd.options, [("HF", "hf"), ("B3LYP", "b3lyp")])
        self.assertEqual(dd.value, "hf")


if __name__ == "__main__":
    unittest.main()
