"""
qchem_colab_app.gui.plot_common
-------------------------------
特定の計算エンジン(PySCF等)に依存しない、汎用的な可視化関数群(画面の層の部品)。

ここに置く関数の条件: 引数がPySCFのMole/SCFオブジェクトそのものではなく、
プレーンなPythonの値(元素記号のリスト・座標のリスト・エネルギーの数列等)
であること。これにより、将来UMAベースの計算エンジンを追加した際にも
(pyscf_backend側のコードに一切触れず)そのままインポートして再利用できる。

py3Dmol(構造・振動アニメーション・原子電荷の色分け)を用いている。

    - render_single_structure() : 1つの構造の3D表示
    - render_vibration()        : 振動アニメーション
    - render_charges()          : 原子電荷で色分けした半透明の球と、数値ラベルつきの3D表示
      (add_atom_charge_labels / add_atom_charge_spheres / _charge_gradient_color は、その部品)
    - atomic_charges_table_html(): 原子電荷のHTML表

原子電荷の関数は、v0.2.2で、pyscf_backend/visualizer_pyscf.py から、ここに移した。
引数を、PySCFの Mole ではなく、プレーンな(元素記号, 座標, (元素記号, 電荷)の組)にしたため、
電荷の値を出すエンジン(現在はPySCF版)から独立している。

エネルギー収束グラフは、このモジュールではなく gui/energy_plot.py の
build_energy_plot_html()(自前のSVG)で描いている。以前はここにplotly版の
グラフ関数もあったが、使われなくなったため削除した(Gitの履歴に残っている)。
"""

import numpy as np

# Bondiのファンデルワールス半径(Å)。主要な有機元素+アルカリ/アルカリ土類/
# ハロゲン程度をカバー。表にない元素は _DEFAULT_VDW_RADIUS を使う。
_VDW_RADII = {
    "H": 1.20, "He": 1.40, "Li": 1.82, "Be": 1.53, "B": 1.92,
    "C": 1.70, "N": 1.55, "O": 1.52, "F": 1.47, "Ne": 1.54,
    "Na": 2.27, "Mg": 1.73, "Al": 1.84, "Si": 2.10, "P": 1.80,
    "S": 1.80, "Cl": 1.75, "Ar": 1.88, "K": 2.75, "Ca": 2.31,
    "Br": 1.85, "I": 1.98,
}
_DEFAULT_VDW_RADIUS = 1.70


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


def atomic_charges_table_html(charges):
    """原子電荷 [(元素記号, 電荷), ...] を、簡単なHTML表に整形する。"""
    rows = "".join(
        f"<tr><td style='padding:2px 10px;text-align:right'>{i + 1}</td>"
        f"<td style='padding:2px 10px'>{sym}</td>"
        f"<td style='padding:2px 10px;text-align:right'>{chg:+.3f}</td></tr>"
        for i, (sym, chg) in enumerate(charges)
    )
    return (
        "<table style='border-collapse:collapse'>"
        "<tr><th style='padding:2px 10px'>原子番号</th>"
        "<th style='padding:2px 10px'>元素</th>"
        "<th style='padding:2px 10px'>Mulliken電荷</th></tr>"
        f"{rows}</table>"
    )


def add_atom_charge_labels(view, coords, charges, font_size=12):
    """3D構造上の各原子位置に、電荷の数値ラベルを直接描画する。

    coords は Å 単位の座標のリスト、charges は [(元素記号, 電荷), ...](原子と同じ順)。
    正電荷(電子が少ない)は青系、負電荷(電子が多い)は赤系の背景色にして、
    静電ポテンシャルマップ等でよく使われる配色(赤=電子リッチ/負、
    青=電子プア/正)に合わせ、符号による見分けがつきやすいようにしている。
    """
    for (_, chg), pos in zip(charges, coords):
        bg_color = "#5b9bff" if chg >= 0 else "#ff5b5b"  # 正=青系、負=赤系
        view.addLabel(f"{chg:+.2f}", {
            "position": {"x": float(pos[0]), "y": float(pos[1]), "z": float(pos[2])},
            "backgroundColor": bg_color,
            "backgroundOpacity": 0.85,
            "fontColor": "white",
            "fontSize": font_size,
            "showBackground": True,
            "inFront": True,
        })
    return view


def _charge_gradient_color(charge, max_abs_charge):
    """電荷の値を、青(正)-緑(中性付近)-赤(負)のグラデーション色に変換する。

    その分子の中での最大|電荷|(max_abs_charge)を基準に -1〜+1 に正規化し、
    0(中性)からの離れ具合に応じて緑から青(正)または赤(負)へ線形補間する。
    """
    neutral = (0x33, 0xcc, 0x33)   # 緑(中性付近)
    positive = (0x22, 0x55, 0xff)  # 青(正電荷)
    negative = (0xff, 0x22, 0x22)  # 赤(負電荷)

    if max_abs_charge <= 1e-6:
        t = 0.0
    else:
        t = max(-1.0, min(1.0, charge / max_abs_charge))

    end = positive if t >= 0 else negative
    frac = abs(t)
    rgb = tuple(int(round(neutral[i] + (end[i] - neutral[i]) * frac)) for i in range(3))
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def add_atom_charge_spheres(view, coords, charges, opacity=0.85, size_variation=0.2):
    """原子ごとに、Mulliken電荷の値に応じたグラデーション色の半透明の球を重ねて表示する。

    coords は Å 単位の座標のリスト、charges は [(元素記号, 電荷), ...](原子と同じ順)。
    正電荷=青、中性付近=緑、負電荷=赤、というグラデーションになるよう
    _charge_gradient_color() で色を決めている。球の大きさは元素ごとの
    ファンデルワールス半径を基準にし、電荷の絶対値が大きいほどわずかに(既定で±10%)
    大きくなるようにしている(size_variationで調整幅を変更可能)。

    厳密には「全電子密度」は常に正の値であり符号を持たないため、
    電子密度そのものを正負で塗り分けることは物理的にできない。そのため、
    正負の符号を持つ量として代わりにMulliken電荷を使っている。

    なお、より厳密に「表面を電荷(静電ポテンシャル)で塗り分ける」には
    pyscf.tools.cubegen.mep() で計算した静電ポテンシャルを、密度の等値面に
    2つ目の物性値として重ね書きする手法(いわゆるESPマッピング)が本来のやり方だが、
    3Dmol.js側の対応APIの詳細を実機検証できておらず信頼性に不安があるため、
    確実に動作するこの球表示で対応している。
    """
    max_abs_charge = max((abs(c) for _, c in charges), default=0.0) or 1.0
    for (sym, chg), pos in zip(charges, coords):
        color = _charge_gradient_color(chg, max_abs_charge)
        vdw_radius = _VDW_RADII.get(sym, _DEFAULT_VDW_RADIUS)
        charge_frac = min(abs(chg), max_abs_charge) / max_abs_charge
        radius = vdw_radius * (1.0 - size_variation / 2 + size_variation * charge_frac)
        view.addSphere({
            "center": {"x": float(pos[0]), "y": float(pos[1]), "z": float(pos[2])},
            "radius": radius,
            "color": color,
            "opacity": opacity,
        })
    return view


def render_charges(symbols, coords, charges, show_labels=True, width=500, height=400):
    """構造(ball and stick)+ 電荷で色分けした半透明の球 + (任意で)数値ラベルを表示する。

    symbols は元素記号のリスト、coords は Å 単位の座標のリスト、charges は
    [(元素記号, 電荷), ...](原子と同じ順)。
    球の色は、正電荷=青、中性付近=緑、負電荷=赤となるグラデーションで、
    その分子の中での最大|電荷|を基準に正規化している(add_atom_charge_spheres参照)。
    数値ラベルは show_labels=False で非表示にできる(原子数が多い分子では
    ラベルが重なって見づらくなるための対応)。
    """
    import py3Dmol

    lines = [str(len(symbols)), "structure for atomic charge visualization"]
    for sym, pos in zip(symbols, coords):
        lines.append(f"{sym} {pos[0]:.6f} {pos[1]:.6f} {pos[2]:.6f}")
    xyz_block = "\n".join(lines)

    view = py3Dmol.view(width=width, height=height)
    view.addModel(xyz_block, "xyz")
    view.setStyle({"stick": {}, "sphere": {"scale": 0.3}})
    add_atom_charge_spheres(view, coords, charges)
    if show_labels:
        add_atom_charge_labels(view, coords, charges)
    view.zoomTo()
    return view
