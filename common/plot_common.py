"""
common.plot_common
--------------------------
特定の計算エンジン(PySCF等)に依存しない、汎用的な可視化関数群。

ここに置く関数の条件: 引数がPySCFのMole/SCFオブジェクトそのものではなく、
プレーンなPythonの値(元素記号のリスト・座標のリスト・エネルギーの数列等)
であること。これにより、将来UMAベースの計算エンジンを追加した際にも
(qcapp側のコードに一切触れず)そのままインポートして再利用できる。

py3Dmol(構造・軌跡・振動アニメーション)とplotly(エネルギー収束グラフ)を
用いている。

1 Hartree = 627.5094740631 kcal/mol (定数として直接埋め込み)
"""

import numpy as np

_HARTREE2KCAL = 627.5094740631


def plot_energy_convergence(energies):
    """構造最適化のエネルギー収束グラフ(plotly.graph_objects.Figure)を作る。

    絶対エネルギー(Hartree)は値の変化が小数点以下にしか現れず見づらいため、
    最終ステップを基準とした相対エネルギー(kcal/mol)としてプロットする。

    タイトル・軸ラベルは英語表記にしている。PNG書き出しに使っている
    kaleido(内蔵のヘッドレスChromium)がCJK(日本語等)フォントを
    持たない環境だと、日本語部分が文字化けして表示されるため
    (半角英数字は正しく表示される)。
    """
    import plotly.graph_objects as go

    fig = go.Figure()
    if not energies:
        fig.update_layout(title="No energy history available")
        return fig

    e_final = energies[-1]
    rel = [(e - e_final) * _HARTREE2KCAL for e in energies]
    fig.add_trace(go.Scatter(x=list(range(len(energies))), y=rel, mode="lines+markers", name="Relative Energy"))
    fig.update_layout(
        title="Energy Convergence During Geometry Optimization",
        xaxis_title="Optimization Step",
        yaxis_title="Relative Energy (kcal/mol, vs. final structure)",
        template="plotly_white",
    )
    return fig


def energy_convergence_png(energies, width=700, height=400, scale=2):
    """plot_energy_convergence() の図を、PNG画像のバイト列に変換する。

    Google Colab上のipywidgets.Output()内では、plotlyの図をdisplay(fig)や
    display(HTML(fig.to_html(...)))のどちらで表示しようとしても描画されない
    (グラフの領域自体が確保されない)ケースが確認された。plotlyのインタラク
    ティブ表示はJavaScriptの実行に依存しており、Colabの出力領域のサンドボックス
    環境でそのJavaScriptが実行されないことが原因と考えられる。
    そこで、JavaScript実行に一切依存しない静的PNG画像に変換して埋め込む方式に
    変更した(kaleidoパッケージを使用)。対話性(ホバーでの数値表示等)は
    失われるが、確実に表示されることを優先している。

    注意: widthとheightは、plotly自身にレイアウト(文字サイズ・余白・
    目盛りの間隔等)を計算させるための「本来のグラフサイズ」であり、
    この値を小さくするとグラフ全体は縮むがフォントサイズ等は縮まないため、
    文字が重なる/はみ出るなどレイアウトが崩れる。画面上での表示サイズを
    小さくしたい場合は、この関数の戻り値(PNGの生データ)はそのままに、
    表示側(IPython.display.Image の width/height 引数)で縮小すること。
    """
    fig = plot_energy_convergence(energies)
    return fig.to_image(format="png", width=width, height=height, scale=scale)


def energy_convergence_html(energies):
    """(フォールバック用) plot_energy_convergence() の図を埋め込みHTML文字列に
    変換する。kaleidoが使えない環境向けの代替手段として残している。
    """
    fig = plot_energy_convergence(energies)
    return fig.to_html(include_plotlyjs=True, full_html=False)


def render_trajectory(symbols, coords_history, energies=None, width=500, height=400):
    """最適化トラジェクトリをpy3Dmolのアニメーションとして表示するviewを作る。"""
    import py3Dmol
    from common import writer_xyz

    comments = None
    if energies:
        comments = [f"step {i}  E={e:.6f} Ha" for i, e in enumerate(energies)]
    xyz_multi = writer_xyz.multiframe_xyz_string(symbols, coords_history, comments)

    view = py3Dmol.view(width=width, height=height)
    view.addModelsAsFrames(xyz_multi, "xyz")
    view.setStyle({"stick": {}, "sphere": {"scale": 0.3}})
    view.zoomTo()
    view.animate({"loop": "forward", "reps": 0, "interval": 200})
    return view


def render_vibration(symbols, final_coords, frequencies_cm1, normal_modes, mode_index=0,
                      amplitude=0.6, n_frames=20, width=500, height=400):
    """指定した基準振動モードの変位アニメーションを作る。

    Molden等を経由せず、正規化した変位ベクトルに沿って原子を
    正弦的に振動させた複数フレームのxyzを直接組み立て、
    py3Dmolでループ再生する方式を採っている。

    frequencies_cm1・normal_modesはプレーンな配列で渡す想定
    (PySCFのhessian.thermoが返す形式に限らず、将来UMA側で計算した
    振動数・法線モードもこの関数にそのまま渡せる)。

    Returns
    -------
    (view, label) のタプル。label には振動数(cm^-1)の説明文が入る。
    """
    import py3Dmol
    from common import writer_xyz

    coords0 = np.array(final_coords, dtype=float)
    mode = np.array(normal_modes[mode_index], dtype=float)
    if mode.shape != coords0.shape:
        mode = mode.reshape(coords0.shape)

    max_disp = np.max(np.linalg.norm(mode, axis=1))
    if max_disp > 1e-8:
        mode = mode / max_disp

    frames = []
    for i in range(n_frames):
        phase = 2.0 * np.pi * i / n_frames
        disp = coords0 + amplitude * np.sin(phase) * mode
        frames.append(disp.tolist())

    xyz_multi = writer_xyz.multiframe_xyz_string(symbols, frames)
    view = py3Dmol.view(width=width, height=height)
    view.addModelsAsFrames(xyz_multi, "xyz")
    view.setStyle({"stick": {}, "sphere": {"scale": 0.3}})
    view.zoomTo()
    view.animate({"loop": "backAndForth", "reps": 0, "interval": 60})

    freq_value = frequencies_cm1[mode_index]
    label = f"振動数 {freq_value:.1f} cm\u207b\u00b9" + ("(虚振動)" if freq_value < 0 else "")
    return view, label
