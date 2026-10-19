"""
qchem_colab_app.gui.plot_common
-------------------------------
特定の計算エンジン(PySCF等)に依存しない、汎用的な可視化関数群(画面の層の部品)。

ここに置く関数の条件: 引数がPySCFのMole/SCFオブジェクトそのものではなく、
プレーンなPythonの値(元素記号のリスト・座標のリスト・エネルギーの数列等)
であること。これにより、将来UMAベースの計算エンジンを追加した際にも
(pyscf_backend側のコードに一切触れず)そのままインポートして再利用できる。

py3Dmol(構造・振動アニメーション)を用いている。

エネルギー収束グラフは、このモジュールではなく gui/energy_plot.py の
build_energy_plot_html()(自前のSVG)で描いている。以前はここにplotly版の
グラフ関数もあったが、使われなくなったため削除した(Gitの履歴に残っている)。
"""

import numpy as np


def render_single_structure(symbols, coords, width=500, height=400):
    """1つの構造だけをball and stickで表示するviewを作る(アニメーションなし)。

    エネルギープロット上の特定の点をクリックした際に、その点に対応する
    構造だけを表示する用途を想定している。
    """
    import py3Dmol

    lines = [str(len(symbols)), "single structure"]
    for sym, pos in zip(symbols, coords):
        lines.append(f"{sym} {pos[0]:.6f} {pos[1]:.6f} {pos[2]:.6f}")
    xyz_block = "\n".join(lines)

    view = py3Dmol.view(width=width, height=height)
    view.addModel(xyz_block, "xyz")
    view.setStyle({"stick": {}, "sphere": {"scale": 0.3}})
    view.zoomTo()
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
    from qchem_colab_app.common_backend import writer_xyz

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
