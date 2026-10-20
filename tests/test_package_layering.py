"""
tests/test_package_layering.py
------------------------------
リポジトリのパッケージ構成と、パッケージどうしの依存の向きの検査。

    ノートブック → gui → pyscf_backend・uma_backend → common_backend

Pythonでは、パッケージを分けても依存の向きは強制されないため、ソースコードのimport文を調べて確かめる
(ソースを構文解析するだけで、ipywidgetsなどがインストールされていなくても動く)。
新しいパッケージを足したときは、このファイルの LAYERS に、許す依存先を書き加えること。
"""

import ast
import json
import os
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PACKAGE = "qchem_colab_app"
PACKAGE_DIR = os.path.join(ROOT, PACKAGE)
NOTEBOOKS = ("ColabApp.ipynb", "ColabApp_UMA.ipynb")

# 各パッケージが、importしてよいパッケージ(qchem_colab_app の中)
LAYERS = {
    "common_backend": set(),
    "pyscf_backend": {"common_backend"},
    "uma_backend": {"common_backend"},
    "gui": {"common_backend", "pyscf_backend", "uma_backend"},
}

# gui の中で、計算エンジンのパッケージを呼び出してよい「画面」と、その呼び先
GUI_SCREENS = {"pyscf_screen": {"pyscf_backend"}, "uma_screen": {"uma_backend"}}

# 画面の層の外(バックエンド)で、importしてはいけないライブラリ
BACKEND_FORBIDDEN_LIBRARIES = {"ipywidgets", "IPython"}


def _python_files(package):
    for dirpath, dirnames, filenames in os.walk(os.path.join(PACKAGE_DIR, package)):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for name in sorted(filenames):
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def _imports(source):
    """ソースのimport文(関数の中のものも含む)から、(読み込むモジュール名, 読み込む名前のリスト, 相対か)を返す。"""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((alias.name, [], False))
        elif isinstance(node, ast.ImportFrom):
            found.append((node.module or "", [a.name for a in node.names], node.level > 0))
    return found


def _project_targets(module, names):
    """import文が指す、qchem_colab_app の中のパッケージ名(と、そのモジュール名)の集合を返す。"""
    parts = module.split(".")
    if parts[0] != PACKAGE:
        return set()
    if len(parts) == 1:                              # from qchem_colab_app import gui
        return {(name, None) for name in names}
    return {(parts[1], parts[2] if len(parts) > 2 else None)}


class TestRepositoryLayout(unittest.TestCase):
    def test_no_python_files_in_the_repository_root(self):
        # ルートに置くのは、ノートブック(エントリーポイント)・設定・文書だけ
        python_files = [n for n in os.listdir(ROOT) if n.endswith(".py")]
        self.assertEqual(python_files, [])

    def test_the_top_level_package_has_exactly_the_expected_subpackages(self):
        subpackages = sorted(
            n for n in os.listdir(PACKAGE_DIR)
            if os.path.isdir(os.path.join(PACKAGE_DIR, n)) and n != "__pycache__")
        self.assertEqual(subpackages, sorted(LAYERS))
        for name in subpackages:
            self.assertTrue(os.path.isfile(os.path.join(PACKAGE_DIR, name, "__init__.py")), name)

    def test_package_init_files_import_nothing_from_the_project(self):
        # パッケージを読み込んだだけで、重いライブラリ(ipywidgets など)が必要にならないように。
        # また、他のモジュールの名前を別名として公開(再エクスポート)しないように
        paths = [os.path.join(PACKAGE_DIR, "__init__.py")]
        paths += [os.path.join(PACKAGE_DIR, name, "__init__.py") for name in sorted(LAYERS)]
        for path in paths:
            with open(path, encoding="utf-8") as f:
                self.assertEqual(_imports(f.read()), [], path)


class TestDependencyDirection(unittest.TestCase):
    def test_every_package_imports_only_what_its_layer_allows(self):
        violations = []
        for package, allowed in LAYERS.items():
            for path in _python_files(package):
                with open(path, encoding="utf-8") as f:
                    for module, names, relative in _imports(f.read()):
                        if relative:
                            violations.append(f"{path}: 相対importは使わない({module})")
                            continue
                        for target, _ in _project_targets(module, names):
                            if target != package and target not in allowed:
                                violations.append(f"{os.path.relpath(path, ROOT)}: {package} は {target} をimportしない")
        self.assertEqual(violations, [])

    def test_backends_do_not_use_the_screen_libraries(self):
        violations = []
        for package in ("common_backend", "pyscf_backend", "uma_backend"):
            for path in _python_files(package):
                with open(path, encoding="utf-8") as f:
                    for module, _, _ in _imports(f.read()):
                        if module.split(".")[0] in BACKEND_FORBIDDEN_LIBRARIES:
                            violations.append(f"{os.path.relpath(path, ROOT)}: {module}")
        self.assertEqual(violations, [])

    def test_only_the_screens_call_a_calculation_package(self):
        # gui の共通の部品(parts・inputs・outputs・colab_widgets・energy_plot・plot_common)は、
        # pyscf_backend・uma_backend をimportしない。各画面は、自分の計算エンジンだけをimportする。
        violations = []
        for path in _python_files("gui"):
            module_name = os.path.splitext(os.path.basename(path))[0]
            allowed_engines = GUI_SCREENS.get(module_name, set())
            with open(path, encoding="utf-8") as f:
                for module, names, _ in _imports(f.read()):
                    for target, _ in _project_targets(module, names):
                        if target in ("pyscf_backend", "uma_backend") and target not in allowed_engines:
                            violations.append(f"gui/{module_name}.py は {target} をimportしない")
        self.assertEqual(violations, [])


class TestNotebooks(unittest.TestCase):
    """ノートブックが読み込んでよいのは、gui の画面と、環境準備用の uma_backend.uma_hf だけ。"""

    @staticmethod
    def _code(name):
        with open(os.path.join(ROOT, name), encoding="utf-8") as f:
            notebook = json.load(f)
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                lines = [ln for ln in "".join(cell["source"]).splitlines()
                         if not ln.lstrip().startswith(("!", "%"))]
                yield "\n".join(lines)

    def test_notebooks_import_only_gui_screens_and_the_environment_setup(self):
        violations = []
        for name in NOTEBOOKS:
            for source in self._code(name):
                for module, names, _ in _imports(source):
                    for target, sub in _project_targets(module, names):
                        if target == "gui":
                            continue
                        if target == "uma_backend" and (sub == "uma_hf" or names == ["uma_hf"]):
                            continue
                        violations.append(f"{name}: {module} {names}")
        self.assertEqual(violations, [])

    def test_each_notebook_imports_its_own_screen(self):
        expected = {"ColabApp.ipynb": "pyscf_screen", "ColabApp_UMA.ipynb": "uma_screen"}
        for name, screen in expected.items():
            screens = []
            for source in self._code(name):
                for module, names, _ in _imports(source):
                    if module == f"{PACKAGE}.gui":
                        screens += names
            self.assertEqual(screens, [screen], name)


if __name__ == "__main__":
    unittest.main()
