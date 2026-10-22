"""
test/test_colab_widgets.py
--------------------------
gui.colab_widgets のうち、Colab/ブラウザなしでテストできる部分
(ドロップ領域のHTML生成・ドロップされたファイルの検証・識別子の安全確認)の単体テスト。
(エネルギーグラフの部分は、gui/energy_plot.py に分けたため、tests/test_energy_plot.py にある。)

JavaScriptがColab上で実際に動くか(ドロップ → Python呼び出し)は
このテストでは確認できないため、Colab上での実機確認が必要(README.md参照)。
"""

import base64
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qchem_colab_app.gui import colab_widgets as cw  # noqa: E402


class TestParseDroppedPayload(unittest.TestCase):
    @staticmethod
    def _payload(name, content=b"3\nwater\nO 0 0 0\nH 0 0 1\nH 0 1 0\n"):
        return {"name": name, "content_b64": base64.b64encode(content).decode("ascii")}

    def test_valid_xyz_returns_name_and_bytes(self):
        content = b"1\nx\nH 0 0 0\n"
        name, data = cw.parse_dropped_payload(self._payload("water.xyz", content))
        self.assertEqual(name, "water.xyz")
        self.assertEqual(data, content)

    def test_extension_check_is_case_insensitive(self):
        name, _ = cw.parse_dropped_payload(self._payload("WATER.XYZ"))
        self.assertEqual(name, "WATER.XYZ")

    def test_directory_part_of_file_name_is_removed(self):
        name, _ = cw.parse_dropped_payload(self._payload("C:\\Users\\me\\water.xyz"))
        self.assertEqual(name, "water.xyz")
        name, _ = cw.parse_dropped_payload(self._payload("../../etc/water.gjf"))
        self.assertEqual(name, "water.gjf")

    def test_unsupported_extension_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            cw.parse_dropped_payload(self._payload("water.mol"))
        self.assertIn("対応形式", str(ctx.exception))

    def test_invalid_base64_is_rejected(self):
        with self.assertRaises(ValueError):
            cw.parse_dropped_payload({"name": "a.xyz", "content_b64": "!!!not base64!!!"})

    def test_empty_file_is_rejected(self):
        with self.assertRaises(ValueError):
            cw.parse_dropped_payload(self._payload("a.xyz", b""))

    def test_too_large_file_is_rejected(self):
        with self.assertRaises(ValueError):
            cw.parse_dropped_payload(self._payload("a.xyz", b"x" * 100), max_bytes=50)

    def test_malformed_payload_is_rejected(self):
        for bad in (None, "text", {"name": "a.xyz"}, {"content_b64": "AAAA"}):
            with self.assertRaises(ValueError):
                cw.parse_dropped_payload(bad)


class TestDropZoneHtml(unittest.TestCase):
    def test_contains_callback_extensions_and_size_limit(self):
        html_text = cw.build_drop_zone_html("qchem_cb_drop", uid="qchem_drop_t")
        self.assertIn("qchem_cb_drop", html_text)
        for ext in (".xyz", ".com", ".gjf", ".pdb"):
            self.assertIn(ext, html_text)
        self.assertIn(str(cw.MAX_DROPPED_FILE_BYTES), html_text)

    def test_all_placeholders_are_replaced(self):
        html_text = cw.build_drop_zone_html("qchem_cb_drop", uid="qchem_drop_t")
        self.assertNotRegex(html_text, r"__[A-Z_]+__")

    def test_unsafe_callback_name_is_rejected(self):
        with self.assertRaises(ValueError):
            cw.build_drop_zone_html("bad name'")


class TestCheckSafeId(unittest.TestCase):
    def test_alphanumerics_and_underscores_are_accepted(self):
        self.assertEqual(cw.check_safe_id("qchem_cb_1", "x"), "qchem_cb_1")

    def test_other_characters_are_rejected(self):
        for bad in ("a b", "a-b", "a'b", "", None, 3):
            with self.assertRaises(ValueError):
                cw.check_safe_id(bad, "x")


if __name__ == "__main__":
    unittest.main()
