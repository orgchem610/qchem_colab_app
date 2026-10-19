"""
qchem_colab_app.gui.energy_plot
-------------------------------
クリックできるエネルギー収束グラフ(SVG)と、そのための目盛りの計算。
計算エンジン(PySCF/UMA等)には依存しない、画面の層の部品。

提供するもの:
    - nice_ticks()             : 軸の読みやすい目盛り
    - build_energy_plot_html() : グラフのHTML(クリックでPython側の関数を呼ぶJavaScript込み)

エネルギーの単位換算(HARTREE_TO_KCAL_MOL)と相対エネルギー(relative_energies_kcal)は、
バックエンドからも使うため、common_backend/energy.py にある(v0.2.2で、このファイルから分けた)。

設計方針(なぜこの方式にしたか):
    - Plotly の FigureWidget は、Colab上でグラフの枠だけ表示されて点が表示されない事例があり、
      Output内ではplotlyのインタラクティブ表示が描画されないことがあった。
    - そこで、外部ライブラリ(Plotly.js等)に一切頼らず、グラフを素のSVGで描き、
      「ブラウザ側のJavaScriptが、Colabの google.colab.kernel.invokeFunction でPython側の関数を
      呼ぶ」というColab公式の仕組み(gui/colab_widgets.py の register_callback)だけを使う。
      クリック連携が動かない環境でも「点そのもの」は必ず表示される。

注意:
    JavaScriptを含むHTMLは、IPython.display.display(HTML(...)) で表示すること
    (ipywidgets.HTML ウィジェットの value に入れるとscriptが実行されない)。
"""

import html
import math
import uuid

from qchem_colab_app.common_backend.energy import relative_energies_kcal
from qchem_colab_app.gui.colab_widgets import check_safe_id


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
    uid = check_safe_id(uid or f"qchem_plot_{uuid.uuid4().hex}", "uid")
    if callback_name is not None:
        check_safe_id(callback_name, "callback_name")

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
