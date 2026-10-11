"""
common.colab_widgets
--------------------
Google Colab 上で「ブラウザ側(JavaScript)」と「Python側」をつなぐ部品群。
計算エンジン(PySCF/UMA等)には依存しないため、common/ に置いている。

提供するもの:
    1. ファイルのドラッグ&ドロップ領域
         build_drop_zone_html() / parse_dropped_payload()
    2. クリックできるエネルギーグラフ(SVG)
         build_energy_plot_html() / relative_energies_kcal()
    3. Colabのコールバック登録の薄いラッパー
         register_callback() / is_colab()

設計方針(なぜこの方式にしたか):
    - ipywidgets.FileUpload は、環境によってはドロップ操作を受け付けない。
    - Plotly の FigureWidget は、Colab上でグラフの枠だけ表示されて点が
      表示されない事例があり、requirements.txt にも「Output内ではplotlyの
      インタラクティブ表示が描画されないことがあった」と記録されている。
    - そこで、外部ライブラリ(Plotly.js等)に一切頼らず、
        「ブラウザ側のJavaScriptが、Colabの google.colab.kernel.invokeFunction
          でPython側の関数を呼ぶ」
      という Colab 公式の仕組みだけを使う。グラフは素のSVGで描くため、
      クリック連携が動かない環境でも「点そのもの」は必ず表示される。

注意:
    JavaScriptを含むHTMLは、IPython.display.display(HTML(...)) で表示すること
    (ipywidgets.HTML ウィジェットの value に入れるとscriptが実行されない)。
"""

import base64
import binascii
import html
import math
import os
import re
import uuid

HARTREE_TO_KCAL_MOL = 627.5094740631

ALLOWED_STRUCTURE_EXTENSIONS = (".xyz", ".com", ".gjf", ".pdb")
MAX_DROPPED_FILE_BYTES = 5 * 1024 * 1024  # 5 MB(構造ファイルとしては十分大きい)

_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


# -----------------------------------------------------------------------------
# Colab連携の共通部品
# -----------------------------------------------------------------------------

def is_colab():
    """Google Colab上で実行されているかどうか。"""
    try:
        import google.colab  # noqa: F401
        return True
    except ImportError:
        return False


def register_callback(func, prefix="qchem_cb"):
    """JavaScriptから呼べるPython関数としてfuncを登録し、その登録名を返す。

    Colab以外の環境では何もせず None を返す(呼び出し側は None のとき
    ドロップ領域などを出さず、通常のウィジェットだけで動くようにする)。
    """
    try:
        from google.colab import output
    except ImportError:
        return None
    name = f"{prefix}_{uuid.uuid4().hex}"
    output.register_callback(name, func)
    return name


def _check_safe_id(value, label):
    if not isinstance(value, str) or not _SAFE_ID_PATTERN.match(value):
        raise ValueError(f"{label}には英数字とアンダースコアのみ使用できます: {value!r}")
    return value


# -----------------------------------------------------------------------------
# 1. ドラッグ&ドロップ領域
# -----------------------------------------------------------------------------

def parse_dropped_payload(payload, allowed_extensions=ALLOWED_STRUCTURE_EXTENSIONS,
                          max_bytes=MAX_DROPPED_FILE_BYTES):
    """JavaScriptから渡された辞書を検証し、(ファイル名, 中身のbytes)を返す。

    payload は {"name": "xxx.xyz", "content_b64": "<base64文字列>"} の形。
    問題があれば、利用者にそのまま表示できる日本語メッセージの ValueError を送出する。
    """
    if not isinstance(payload, dict) or "name" not in payload or "content_b64" not in payload:
        raise ValueError("ファイル情報を正しく受け取れませんでした。もう一度ドロップしてください。")

    # パス区切りが混ざっていても、ファイル名部分だけを使う
    name = os.path.basename(str(payload["name"]).replace("\\", "/"))
    extension = os.path.splitext(name)[1].lower()
    if extension not in allowed_extensions:
        raise ValueError(f"対応形式は {', '.join(allowed_extensions)} です(受け取ったファイル: {name})。")

    try:
        content = base64.b64decode(payload["content_b64"], validate=True)
    except (binascii.Error, ValueError, TypeError):
        raise ValueError("ファイルの中身を読み取れませんでした。もう一度ドロップしてください。")

    if not content:
        raise ValueError("空のファイルはアップロードできません。")
    if len(content) > max_bytes:
        raise ValueError(
            f"ファイルが大きすぎます({len(content) / 1024 / 1024:.1f} MB。"
            f"上限は {max_bytes / 1024 / 1024:.0f} MB です)。")
    return name, content


_DROP_ZONE_TEMPLATE = """
<div id="__UID__" style="border:2px dashed #5b8def;border-radius:8px;padding:16px;
     max-width:520px;text-align:center;color:#315a9e;background:#f7faff;cursor:pointer;
     font-family:sans-serif;font-size:14px">
  <div>ここへ構造ファイルをドラッグ＆ドロップ<br>(または、この枠をクリックしてファイルを選択)</div>
  <div style="font-size:12px;margin-top:4px">__EXTENSIONS__</div>
  <div id="__UID__-msg" style="margin-top:8px;font-size:12px;color:#555;min-height:16px"></div>
  <input id="__UID__-input" type="file" accept="__ACCEPT__" style="display:none">
</div>
<script>
(function () {
  var zone = document.getElementById('__UID__');
  var input = document.getElementById('__UID__-input');
  var msg = document.getElementById('__UID__-msg');
  if (!zone || zone.getAttribute('data-ready')) { return; }
  zone.setAttribute('data-ready', '1');

  function say(text, ok) {
    msg.textContent = text;
    msg.style.color = (ok === true) ? '#167a2e' : (ok === false ? '#b42318' : '#555');
  }

  var allowed = '__ACCEPT__'.split(',');
  function send(file) {
    if (!file) { return; }
    var dot = file.name.lastIndexOf('.');
    var ext = dot >= 0 ? file.name.substring(dot).toLowerCase() : '';
    if (allowed.indexOf(ext) < 0) {
      say('対応形式は __EXTENSIONS__ です(受け取ったファイル: ' + file.name + ')。', false);
      return;
    }
    if (file.size > __MAX_BYTES__) {
      say('ファイルが大きすぎます(上限 __MAX_MB__ MB)。', false);
      return;
    }
    var reader = new FileReader();
    reader.onerror = function () { say('ファイルの読み込みに失敗しました。', false); };
    reader.onload = function () {
      var text = String(reader.result);
      var encoded = text.substring(text.indexOf(',') + 1);
      if (!(window.google && google.colab && google.colab.kernel &&
            google.colab.kernel.invokeFunction)) {
        say('Colabのカーネルと通信できません。下の「ファイルを選択」ボタンをご利用ください。', false);
        return;
      }
      say(file.name + ' を送信中…');
      google.colab.kernel.invokeFunction('__CALLBACK__',
          [{name: file.name, content_b64: encoded}], {})
        .then(function () {
          say('送信しました: ' + file.name + '(受信結果はこの下の表示でご確認ください)', true);
        })
        .catch(function (e) {
          say('送信に失敗しました: ' + e + '。下の「ファイルを選択」ボタンをご利用ください。', false);
        });
    };
    reader.readAsDataURL(file);
  }

  ['dragenter', 'dragover'].forEach(function (ev) {
    zone.addEventListener(ev, function (e) {
      e.preventDefault(); zone.style.background = '#e8f0fe';
    });
  });
  ['dragleave', 'drop'].forEach(function (ev) {
    zone.addEventListener(ev, function (e) {
      e.preventDefault(); zone.style.background = '#f7faff';
    });
  });
  zone.addEventListener('drop', function (e) {
    var files = e.dataTransfer && e.dataTransfer.files;
    send(files && files[0]);
  });
  zone.addEventListener('click', function () { input.click(); });
  input.addEventListener('change', function () { send(input.files && input.files[0]); });
})();
</script>
"""


def build_drop_zone_html(callback_name, uid=None,
                         extensions=ALLOWED_STRUCTURE_EXTENSIONS,
                         max_bytes=MAX_DROPPED_FILE_BYTES):
    """ドロップ領域のHTML(JavaScript込み)を返す。display(HTML(...))で表示すること。

    ドロップされたファイルは、register_callback()で登録した関数
    (callback_name)に {"name":..., "content_b64":...} として渡される。
    """
    _check_safe_id(callback_name, "callback_name")
    uid = _check_safe_id(uid or f"qchem_drop_{uuid.uuid4().hex}", "uid")
    replacements = {
        "__UID__": uid,
        "__CALLBACK__": callback_name,
        "__EXTENSIONS__": html.escape(" / ".join(extensions)),
        "__ACCEPT__": html.escape(",".join(extensions)),
        "__MAX_BYTES__": str(int(max_bytes)),
        "__MAX_MB__": f"{max_bytes / 1024 / 1024:.0f}",
    }
    out = _DROP_ZONE_TEMPLATE
    for key, value in replacements.items():
        out = out.replace(key, value)
    return out


# -----------------------------------------------------------------------------
# 2. クリックできるエネルギーグラフ(SVG)
# -----------------------------------------------------------------------------

def relative_energies_kcal(energies_hartree):
    """最後の点(=最適化後の最安定点)を基準にした相対エネルギー[kcal/mol]のリスト。

    gui.pyの構造表示ラベル(ステップ n: 相対エネルギー ...)と同じ基準。
    """
    energies = [float(e) for e in energies_hartree]
    if not energies:
        raise ValueError("エネルギーが1点も記録されていないため、グラフを描画できません。")
    if not all(math.isfinite(e) for e in energies):
        raise ValueError("エネルギーに数値でない値(NaN/inf)が含まれているため、グラフを描画できません。")
    reference = energies[-1]
    return [(e - reference) * HARTREE_TO_KCAL_MOL for e in energies]


def _nice_step(raw_step):
    """raw_step以上で、1・2・5 × 10^n のうち最小のきりの良い刻み幅を返す。"""
    exponent = math.floor(math.log10(raw_step))
    base = 10 ** exponent
    for multiplier in (1, 2, 5, 10):
        if multiplier * base >= raw_step:
            return multiplier * base
    return 10 * base  # 到達しないが念のため


def nice_ticks(vmin, vmax, target=5, integer_only=False):
    """[vmin, vmax]の内側に収まる、きりの良い目盛り値のリストと刻み幅を返す。"""
    span = vmax - vmin
    if span <= 0:
        return [vmin], 1.0
    step = _nice_step(span / max(target, 1))
    if integer_only:
        step = max(1.0, math.ceil(step))
    first = math.ceil(vmin / step - 1e-9) * step
    ticks = []
    k = 0
    while True:
        value = first + k * step
        if value > vmax + step * 1e-9:
            break
        ticks.append(value)
        k += 1
        if k > 1000:  # 異常入力時の保険
            break
    return ticks, step


def _format_tick(value, step):
    decimals = 0 if step >= 1 else int(-math.floor(math.log10(step) + 1e-9))
    decimals = max(0, min(decimals, 6))
    text = f"{value:.{decimals}f}"
    if text.startswith("-") and float(text) == 0:  # "-0" や "-0.0" を避ける
        text = text[1:]
    return text


_FONT = "Arial, 'Hiragino Sans', 'Noto Sans CJK JP', 'Yu Gothic', sans-serif"

_PLOT_SCRIPT_TEMPLATE = """
<script>
(function () {
  var root = document.getElementById('__UID__');
  var sel = document.getElementById('__UID__-sel');
  var status = document.getElementById('__UID__-status');
  if (!root || root.getAttribute('data-ready')) { return; }
  root.setAttribute('data-ready', '1');
  var hits = root.querySelectorAll('.qc-hit');
  function hasKernel() {
    return window.google && google.colab && google.colab.kernel &&
           google.colab.kernel.invokeFunction;
  }
  function bind(el) {
    el.addEventListener('click', function () {
      var i = parseInt(el.getAttribute('data-i'), 10);
      sel.setAttribute('transform',
          'translate(' + el.getAttribute('cx') + ',' + el.getAttribute('cy') + ')');
      if (!hasKernel()) {
        status.textContent = 'Colabのカーネルと通信できません。スライダーで構造を切り替えてください。';
        return;
      }
      status.textContent = 'ステップ ' + i + ' の構造を読み込み中…';
      google.colab.kernel.invokeFunction('__CALLBACK__', [i], {})
        .then(function () { status.textContent = 'ステップ ' + i + ' の構造を表示しました。'; })
        .catch(function (e) {
          status.textContent = 'Python側との通信に失敗しました(' + e + ')。スライダーをご利用ください。';
        });
    });
  }
  for (var k = 0; k < hits.length; k++) { bind(hits[k]); }
})();
</script>
"""


def build_energy_plot_html(energies_hartree, selected_index=None, callback_name=None,
                           uid=None, width=640, height=360):
    """エネルギー収束グラフ(SVG)のHTMLを返す。display(HTML(...))で表示すること。

    Parameters
    ----------
    energies_hartree : 各最適化ステップの全エネルギー[Hartree]
    selected_index   : 赤い菱形で強調する点の番号(省略時は最後の点)
    callback_name    : 指定すると、点をクリックしたとき Python側の
                       callback(点の番号:int) が呼ばれる。省略すると静的な図になる。
    """
    values = relative_energies_kcal(energies_hartree)
    n = len(values)
    if selected_index is None:
        selected_index = n - 1
    selected_index = max(0, min(int(selected_index), n - 1))
    uid = _check_safe_id(uid or f"qchem_plot_{uuid.uuid4().hex}", "uid")
    if callback_name is not None:
        _check_safe_id(callback_name, "callback_name")

    # --- 座標系 ---------------------------------------------------------
    margin_left, margin_right, margin_top, margin_bottom = 74, 20, 16, 54
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    if n == 1:
        x0, x1 = -0.5, 0.5
    else:
        pad_x = max(0.35, 0.04 * (n - 1))
        x0, x1 = -pad_x, (n - 1) + pad_x

    y_min, y_max = min(values), max(values)
    y_span = y_max - y_min
    if y_span < 1e-9:
        y0, y1 = y_min - 0.5, y_max + 0.5
    else:
        y0, y1 = y_min - 0.08 * y_span, y_max + 0.08 * y_span

    def px(x):
        return margin_left + (x - x0) / (x1 - x0) * plot_w

    def py(y):
        return margin_top + (y1 - y) / (y1 - y0) * plot_h

    pts = [(px(i), py(v)) for i, v in enumerate(values)]

    # --- SVG本体 --------------------------------------------------------
    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" style="max-width:100%;height:auto" font-family="{_FONT}" '
        f'font-size="12">')
    parts.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>')
    parts.append(
        f'<rect x="{margin_left}" y="{margin_top}" width="{plot_w}" height="{plot_h}" '
        f'fill="none" stroke="#000000" stroke-width="1"/>')

    # 目盛り(外向き・グリッド線なし。ColabReactionのグラフに合わせた体裁)
    x_ticks, x_step = nice_ticks(0, n - 1, target=8, integer_only=True)
    for t in x_ticks:
        x = px(t)
        parts.append(
            f'<line x1="{x:.1f}" y1="{margin_top + plot_h}" x2="{x:.1f}" '
            f'y2="{margin_top + plot_h + 5}" stroke="#000000"/>')
        parts.append(
            f'<text x="{x:.1f}" y="{margin_top + plot_h + 19}" text-anchor="middle" '
            f'fill="#000000">{_format_tick(t, x_step)}</text>')
    y_ticks, y_step = nice_ticks(y0, y1, target=5)
    for t in y_ticks:
        y = py(t)
        parts.append(
            f'<line x1="{margin_left - 5}" y1="{y:.1f}" x2="{margin_left}" y2="{y:.1f}" '
            f'stroke="#000000"/>')
        parts.append(
            f'<text x="{margin_left - 9}" y="{y + 4:.1f}" text-anchor="end" '
            f'fill="#000000">{_format_tick(t, y_step)}</text>')

    # 軸ラベル
    parts.append(
        f'<text x="{margin_left + plot_w / 2:.1f}" y="{height - 10}" text-anchor="middle" '
        f'font-size="13" fill="#000000">最適化ステップ</text>')
    parts.append(
        f'<text transform="translate(16,{margin_top + plot_h / 2:.1f}) rotate(-90)" '
        f'text-anchor="middle" font-size="13" fill="#000000">相対エネルギー (kcal/mol)</text>')

    # 点どうしを結ぶ細い線(最適化の順序が分かるように)
    if n >= 2:
        poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        parts.append(
            f'<polyline points="{poly}" fill="none" stroke="#9db7e8" stroke-width="1.5"/>')

    # プロットの点
    for x, y in pts:
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#1f77b4" '
            f'stroke="#ffffff" stroke-width="1"/>')

    # 選択中の点(赤い菱形。クリックでJavaScriptがtransformを書き換えて移動させる)
    sx, sy = pts[selected_index]
    parts.append(
        f'<g id="{uid}-sel" transform="translate({sx:.1f},{sy:.1f})" pointer-events="none">'
        f'<polygon points="0,-8 8,0 0,8 -8,0" fill="#e11d1d" stroke="#ffffff" '
        f'stroke-width="1"/></g>')

    # クリック判定用の透明な大きい円(最前面。ホバーで数値のツールチップも出す)
    cursor = "pointer" if callback_name else "default"
    for i, ((x, y), v) in enumerate(zip(pts, values)):
        tip = html.escape(f"ステップ {i} / 相対エネルギー {v:+.2f} kcal/mol")
        parts.append(
            f'<circle class="qc-hit" data-i="{i}" cx="{x:.1f}" cy="{y:.1f}" r="11" '
            f'fill="#000000" fill-opacity="0" pointer-events="all" '
            f'style="cursor:{cursor}"><title>{tip}</title></circle>')
    parts.append("</svg>")

    wrapper = [f'<div id="{uid}" style="font-family:{_FONT}">']
    wrapper.append("".join(parts))
    if callback_name:
        wrapper.append(
            f'<div id="{uid}-status" style="font-size:12px;color:#555;min-height:16px"></div>')
    wrapper.append("</div>")
    out = "".join(wrapper)
    if callback_name:
        script = _PLOT_SCRIPT_TEMPLATE.replace("__UID__", uid).replace("__CALLBACK__", callback_name)
        out += script
    return out
