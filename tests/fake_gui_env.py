"""
tests/fake_gui_env.py
---------------------
common/gui_parts.py などのGUI部品を、ipywidgets・Google Colab・ブラウザなしでテストするための、
簡易な代用品(ipywidgets / IPython.display / google.colab)。

本物のウィジェットの「値が変わると observe に登録した関数が呼ばれる」
「with Output(): の中の display / print が、その Output に溜まる」といった動作だけを再現する。
本物のipywidgetsやColabでの見た目・通信までは再現しないため、実機確認の代わりにはならない。

使い方:
    with fake_gui_env(colab=True) as env:
        gui_parts = env.import_module("common.gui_parts")
        ...
env.callbacks : Colabに登録されたJavaScriptから呼べる関数(名前 -> 関数)
env.downloaded: colab.files.download() に渡されたファイル名のリスト
"""

import contextlib
import importlib
import sys
import types

_MODULES = ("ipywidgets", "IPython", "IPython.display", "google", "google.colab",
            "google.colab.output", "google.colab.files")
_REPO_MODULES = ("common.gui_parts", "common.colab_widgets")


class _Env:
    def __init__(self, colab):
        self.colab = colab
        self.callbacks = {}
        self.downloaded = []
        self.output_stack = []

    def import_module(self, name):
        return importlib.import_module(name)


def _build_ipywidgets(env):
    m = types.ModuleType("ipywidgets")

    class Layout:
        def __init__(self, **kw):
            pass

    class _W:
        def __init__(self, **kw):
            object.__setattr__(self, "_observers", [])
            object.__setattr__(self, "_initializing", True)
            for key, value in kw.items():
                if key not in ("layout", "style"):
                    object.__setattr__(self, key, value)
            object.__setattr__(self, "_initializing", False)

        def observe(self, fn, names=None):
            self._observers.append(fn)

        def __setattr__(self, key, value):
            old = getattr(self, key, None)
            object.__setattr__(self, key, value)
            if key == "value" and not self._initializing and old != value:
                for fn in list(self._observers):
                    fn({"name": "value", "old": old, "new": value})

    class HTML(_W):
        def __init__(self, value="", **kw):
            super().__init__(value=value, **kw)

    class Dropdown(_W):
        def __init__(self, options=(), **kw):
            super().__init__(options=options, **kw)
            object.__setattr__(self, "value", options[0][1] if options else None)

        def __setattr__(self, key, value):
            _W.__setattr__(self, key, value)
            if key == "options" and not self._initializing:
                object.__setattr__(self, "value", value[0][1] if value else None)

    class Text(_W):
        def __init__(self, **kw):
            kw.setdefault("value", "")
            super().__init__(**kw)

    class FileUpload(_W):
        def __init__(self, **kw):
            super().__init__(value=(), **kw)

    class Button(_W):
        def __init__(self, **kw):
            kw.setdefault("disabled", False)
            super().__init__(**kw)
            object.__setattr__(self, "_handlers", [])

        def on_click(self, fn):
            self._handlers.append(fn)

        def click(self):
            for fn in self._handlers:
                fn(self)

    class IntSlider(_W):
        def __setattr__(self, key, value):
            if key == "max" and not self._initializing:
                object.__setattr__(self, "max", value)
                if self.value > value:
                    _W.__setattr__(self, "value", value)   # 本物と同様、範囲外の値は丸められる
                return
            _W.__setattr__(self, key, value)

    class Output(_W):
        def __init__(self, **kw):
            super().__init__(**kw)
            object.__setattr__(self, "outputs", [])

        def __enter__(self):
            env.output_stack.append(self)
            return self

        def __exit__(self, *exc):
            env.output_stack.pop()
            return False

    class VBox(_W):
        def __init__(self, children=(), **kw):
            super().__init__(children=list(children), **kw)

    class HBox(VBox):
        pass

    for cls in (Layout, HTML, Dropdown, Text, FileUpload, Button, IntSlider, Output, VBox, HBox):
        setattr(m, cls.__name__, cls)
    return m


def _build_ipython_display(env):
    m = types.ModuleType("IPython.display")

    class HTML:
        def __init__(self, data):
            self.data = data

    class JSON:
        def __init__(self, data):
            self.data = data

    def display(obj):
        if env.output_stack:
            env.output_stack[-1].outputs.append(obj)

    def clear_output(wait=False):
        if env.output_stack:
            env.output_stack[-1].outputs.clear()

    m.HTML, m.JSON, m.display, m.clear_output = HTML, JSON, display, clear_output
    return m


@contextlib.contextmanager
def fake_gui_env(colab=True):
    """ipywidgets などを代用品に差し替えたうえで、common.gui_parts を読み込み直せる状態にする。"""
    env = _Env(colab)
    saved = {name: sys.modules.get(name) for name in _MODULES + _REPO_MODULES}

    sys.modules["ipywidgets"] = _build_ipywidgets(env)
    ipython = types.ModuleType("IPython")
    ipython_display = _build_ipython_display(env)
    ipython.display = ipython_display
    sys.modules["IPython"] = ipython
    sys.modules["IPython.display"] = ipython_display

    if colab:
        google = types.ModuleType("google")
        gcolab = types.ModuleType("google.colab")
        output = types.ModuleType("google.colab.output")
        files = types.ModuleType("google.colab.files")
        output.register_callback = lambda name, fn: env.callbacks.__setitem__(name, fn)
        files.download = lambda path: env.downloaded.append(path.replace("\\", "/").split("/")[-1])
        gcolab.output, gcolab.files = output, files
        google.colab = gcolab
        sys.modules.update({"google": google, "google.colab": gcolab,
                            "google.colab.output": output, "google.colab.files": files})
    else:
        for name in ("google", "google.colab", "google.colab.output", "google.colab.files"):
            sys.modules[name] = None          # import すると ImportError になる(Colab以外の環境)

    for name in _REPO_MODULES:
        sys.modules.pop(name, None)
    try:
        yield env
    finally:
        for name, module in saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
        for name in _REPO_MODULES:
            if saved[name] is None:
                sys.modules.pop(name, None)
