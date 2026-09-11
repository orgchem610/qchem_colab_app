"""
qcapp.visualizer
-----------------
py3Dmol(構造・軌跡・振動アニメーション・分子軌道・電荷密度の3D表示)と
plotly(エネルギー収束グラフ)を用いた、ノートブック内でのビジュアライザー。

1 Hartree = 627.5094740631 kcal/mol (定数として直接埋め込み)
"""

import os
import tempfile

import numpy as np

_HARTREE2KCAL = 627.5094740631


def plot_energy_convergence(energies):
    """構造最適化のエネルギー収束グラフ(plotly.graph_objects.Figure)を作る。

    絶対エネルギー(Hartree)は値の変化が小数点以下にしか現れず見づらいため、
    最終ステップを基準とした相対エネルギー(kcal/mol)としてプロットする。
    """
    import plotly.graph_objects as go

    fig = go.Figure()
    if not energies:
        fig.update_layout(title="エネルギー履歴がありません")
        return fig

    e_final = energies[-1]
    rel = [(e - e_final) * _HARTREE2KCAL for e in energies]
    fig.add_trace(go.Scatter(x=list(range(len(energies))), y=rel, mode="lines+markers", name="相対エネルギー"))
    fig.update_layout(
        title="構造最適化におけるエネルギー収束",
        xaxis_title="最適化ステップ",
        yaxis_title="相対エネルギー (kcal/mol, 最終構造を基準)",
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
    from qcapp import writer_xyz

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

    Returns
    -------
    (view, label) のタプル。label には振動数(cm^-1)の説明文が入る。
    """
    import py3Dmol
    from qcapp import writer_xyz

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


def get_homo_lumo_indices(mf):
    """収束済みSCFオブジェクトからHOMO/LUMOの軌道インデックスを求める(閉殻を想定)。"""
    mo_occ = mf.mo_occ
    if isinstance(mo_occ, (tuple, list)):
        mo_occ = mo_occ[0]  # UHFの場合はひとまずalphaチャンネルを使う
    occ_indices = np.nonzero(np.asarray(mo_occ) > 0)[0]
    homo_idx = int(occ_indices[-1]) if len(occ_indices) else 0
    lumo_idx = homo_idx + 1
    return homo_idx, lumo_idx


def _mo_coeff_for_cube(mf, orbital_index):
    mo_coeff = mf.mo_coeff
    if isinstance(mo_coeff, (tuple, list)):
        mo_coeff = mo_coeff[0]  # UHFの場合はひとまずalphaチャンネルを使う
    return mo_coeff[:, orbital_index]


def _max_abs_from_cube_file(cube_path):
    """cubeファイルを直接読み、格子点上の値の最大絶対値を求める(フォールバック用)。

    cube形式は「2行のコメント」「原子数と原点」「3方向の軸情報」
    「原子リスト(原子数分)」に続けて、格子点の値がスペース/改行区切りで
    並ぶ。値本体だけを数値として読み取る。
    """
    with open(cube_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    natm = abs(int(lines[2].split()[0]))
    header_lines = 2 + 1 + 3 + natm  # コメント2 + 原子数行 + 軸3行 + 原子natm行
    values = []
    for line in lines[header_lines:]:
        values.extend(float(tok) for tok in line.split())
    return max(abs(v) for v in values) if values else 0.0


def render_orbital(mol, mf, orbital_index, isoval_fraction=0.12, width=500, height=400):
    """指定した分子軌道(例: HOMO, LUMO)をcubeファイル経由で等値面表示する。

    isoval(等値面の閾値)は固定値ではなく、その軌道自身の格子点上での
    最大絶対値に対する割合(既定12%)として動的に決めている。HOMOとLUMOでは
    振幅の広がり方(ピーク値の大きさ)が異なることが多く、固定のisoval
    (例: 0.02)だとLUMO側が分子全体を覆うように大きく表示されすぎることが
    あったため、この方式に変更した。
    """
    import py3Dmol
    from pyscf.tools import cubegen

    tmpdir = tempfile.mkdtemp()
    cube_path = os.path.join(tmpdir, "orbital.cube")
    grid = cubegen.orbital(mol, cube_path, _mo_coeff_for_cube(mf, orbital_index))
    if grid is not None:
        max_abs = float(np.max(np.abs(np.asarray(grid))))
    else:
        max_abs = _max_abs_from_cube_file(cube_path)
    isoval = max(max_abs * isoval_fraction, 1e-4)

    with open(cube_path, "r", encoding="utf-8") as f:
        cube_data = f.read()

    view = py3Dmol.view(width=width, height=height)
    view.addModel(cube_data, "cube")
    view.setStyle({"stick": {}})
    view.addVolumetricData(cube_data, "cube", {"isoval": isoval, "color": "blue", "opacity": 0.75})
    view.addVolumetricData(cube_data, "cube", {"isoval": -isoval, "color": "red", "opacity": 0.75})
    view.zoomTo()
    return view


def compute_mulliken_charges(mol, mf):
    """Mulliken電荷を原子ごとに計算する。戻り値は [(元素記号, 電荷), ...]。"""
    _, atomic_charges = mf.mulliken_pop(verbose=0)
    symbols = [mol.atom_symbol(i) for i in range(mol.natm)]
    return list(zip(symbols, [float(c) for c in atomic_charges]))


def atomic_charges_table_html(charges):
    """compute_mulliken_charges() の結果を簡単なHTML表に整形する。"""
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


def add_atom_charge_labels(view, mol, charges, font_size=12):
    """3D構造上の各原子位置に、電荷の数値ラベルを直接描画する。"""
    coords = mol.atom_coords(unit="Angstrom")
    for (_, chg), pos in zip(charges, coords):
        view.addLabel(f"{chg:+.2f}", {
            "position": {"x": float(pos[0]), "y": float(pos[1]), "z": float(pos[2])},
            "backgroundColor": "white",
            "backgroundOpacity": 0.65,
            "fontColor": "black",
            "fontSize": font_size,
            "showBackground": True,
            "inFront": True,
        })
    return view


def render_density(mol, mf, isovals=(0.002, 0.02, 0.2), width=500, height=400):
    """全電子密度を、淡色(低密度)から濃色(高密度)へのグラデーションになるよう
    3段階の等値面を重ねて表示する。

    軌道(render_orbital)とは異なり、電子密度は原子核付近で桁違いに大きく
    分子表面付近では非常に小さいという、極端に広いダイナミックレンジを持つ。
    そのため軌道と同じ「最大値に対する割合」で等値面を決めると、3段階とも
    ほぼ同じ(核付近のごく小さな)範囲に収まってしまい、見た目上グラデーション
    にならないことがある。電子密度の可視化では、原子単位(e/bohr^3)での
    絶対値として 0.002 / 0.02 / 0.2 前後の値を使うのが一般的であるため
    (0.002は分子表面(van der Waals表面相当)を表す値としてよく使われる)、
    これらを既定値として採用する。
    """
    import py3Dmol
    from pyscf.tools import cubegen

    dm = mf.make_rdm1()
    if isinstance(dm, (tuple, list)):
        dm = dm[0] + dm[1]  # UHFの場合はalpha+beta密度を合算

    tmpdir = tempfile.mkdtemp()
    cube_path = os.path.join(tmpdir, "density.cube")
    cubegen.density(mol, cube_path, dm)

    with open(cube_path, "r", encoding="utf-8") as f:
        cube_data = f.read()

    # (色, 不透明度) の組。淡い黄色(低密度・分子表面付近)
    # → オレンジ → 濃い赤(高密度・原子核付近)の順。
    colors = ["#fff2b2", "#ff9900", "#cc0000"]
    opacities = [0.18, 0.45, 0.85]

    view = py3Dmol.view(width=width, height=height)
    view.addModel(cube_data, "cube")
    view.setStyle({"stick": {}})
    for isoval, color, opacity in zip(isovals, colors, opacities):
        view.addVolumetricData(cube_data, "cube", {"isoval": isoval, "color": color, "opacity": opacity})
    view.zoomTo()
    return view
