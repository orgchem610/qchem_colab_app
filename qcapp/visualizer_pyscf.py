"""
qcapp.visualizer_pyscf
------------------------------
PySCFのMole/SCFオブジェクトに直接依存する可視化関数群。

分子軌道(cubeファイル)・Mulliken電荷など、PySCF固有のデータ構造を
扱うためここに置いている。UMA版では別の方法で同等の情報を得る必要があり、
これらの関数をそのまま再利用することはできない
(common.plot_common側の関数とは対照的)。

将来のリファクタリング候補: render_charges/add_atom_charge_labels/
add_atom_charge_spheres は、実際にはPySCFの`mol`オブジェクトから
`atom_symbol()`/`atom_coords()`を呼んでいるだけで、計算そのものへの
依存は無い。引数をmolオブジェクトではなくプレーンな(symbols, coords)に
変更すれば、common側に移してUMA版とも共有できる。
"""

import os
import tempfile

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
    view.setStyle({"stick": {}, "sphere": {"scale": 0.3}})
    view.addVolumetricData(cube_data, "cube", {"isoval": isoval, "color": "blue", "opacity": 0.75})
    view.addVolumetricData(cube_data, "cube", {"isoval": -isoval, "color": "red", "opacity": 0.75})
    view.zoomTo()
    return view


def compute_mulliken_charges(mol, mf):
    """Mulliken電荷を原子ごとに計算する。戻り値は [(元素記号, 電荷), ...]。"""
    _, atomic_charges = mf.mulliken_pop(verbose=0)
    symbols = [mol.atom_symbol(i) for i in range(mol.natm)]
    return list(zip(symbols, [float(c) for c in atomic_charges]))


def compute_esp_at_atoms(mol, mf, n_directions=6):
    """各原子の「表面付近」における静電ポテンシャル(ESP)を計算する。

    戻り値は [(元素記号, ESP値[Hartree/e]), ...] で、compute_mulliken_charges()
    と同じ形式・同じ原子順序。

    静電ポテンシャルは V(r) = Σ_A Z_A/|r-R_A| - ∫ρ(r')/|r-r'| dr' で定義され、
    これは pyscf.tools.cubegen.mep() が実際に使っている式そのものである
    (PySCF公式ソースコードで確認済み)。ただし mep() は格子(グリッド)上の値を
    計算するもので、原子核の真上(r = R_A)では自分自身の核による項が
    発散して評価できない。そのため、各原子の位置からファンデルワールス半径
    だけ離れた点(その原子の「表面」に相当)を n_directions 方向でサンプリングし、
    その平均値をその原子の代表的なESP値としている。

    3Dmol.js側の不確実な「等値面に2つ目の物性値を重ねて色付けする」機能には
    依存せず、既に動作確認済みの球表示(add_atom_charge_spheresと同じ仕組み)の
    色だけをこの値で決める設計にしているため、以前検討した手法より実装・動作の
    リスクが小さい。
    """
    from pyscf import df, gto, lib

    dm = mf.make_rdm1()
    if isinstance(dm, (tuple, list)):
        dm = dm[0] + dm[1]  # UHFの場合はalpha+beta密度を合算
    dm = np.asarray(dm)

    # 6方向(±x, ±y, ±z)を既定とする。必要なら増減可能。
    base_directions = np.array([
        [1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1],
    ], dtype=float)
    directions = base_directions[:n_directions] if n_directions <= 6 else base_directions

    symbols = [mol.atom_symbol(i) for i in range(mol.natm)]
    all_sample_points = []
    for i in range(mol.natm):
        center = mol.atom_coord(i)  # Bohr単位(PySCF内部座標)
        vdw_bohr = _VDW_RADII.get(symbols[i], _DEFAULT_VDW_RADIUS) / 0.529177210903
        for d in directions:
            all_sample_points.append(center + d * vdw_bohr)
    coords = np.array(all_sample_points)

    # 核による寄与(cubegen.mep()と同じ式)
    vnuc = np.zeros(len(coords))
    for i in range(mol.natm):
        r = mol.atom_coord(i)
        z = mol.atom_charge(i)
        rp = r - coords
        vnuc += z / np.linalg.norm(rp, axis=1)

    # 電子密度による寄与(cubegen.mep()と同じ式)
    vele = np.empty_like(vnuc)
    for p0, p1 in lib.prange(0, vele.size, 600):
        fakemol = gto.fakemol_for_charges(coords[p0:p1])
        ints = df.incore.aux_e2(mol, fakemol)
        vele[p0:p1] = np.einsum("ijp,ij->p", ints, dm)

    mep_samples = (vnuc - vele).reshape(mol.natm, len(directions))
    mep_per_atom = mep_samples.mean(axis=1)
    return list(zip(symbols, [float(v) for v in mep_per_atom]))


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
    """3D構造上の各原子位置に、電荷の数値ラベルを直接描画する。

    正電荷(電子が少ない)は青系、負電荷(電子が多い)は赤系の背景色にして、
    静電ポテンシャルマップ等でよく使われる配色(赤=電子リッチ/負、
    青=電子プア/正)に合わせ、符号による見分けがつきやすいようにしている。
    """
    coords = mol.atom_coords(unit="Angstrom")
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


def _minmax_gradient_color(value, v_min, v_max):
    """値を、青(低い)-緑(中間)-赤(高い)のグラデーション色に変換する。

    _charge_gradient_color()とは異なり、0を中心とした対称な正規化ではなく、
    実際の最小値・最大値の範囲で単純に0〜1に正規化する
    (静電ポテンシャル(ESP)の値は0を挟んで対称とは限らないため)。
    """
    blue = (0x22, 0x55, 0xff)   # 低い
    green = (0x33, 0xcc, 0x33)  # 中間
    red = (0xff, 0x22, 0x22)    # 高い

    if v_max - v_min <= 1e-12:
        t = 0.5
    else:
        t = max(0.0, min(1.0, (value - v_min) / (v_max - v_min)))

    if t < 0.5:
        frac = t / 0.5
        start, end = blue, green
    else:
        frac = (t - 0.5) / 0.5
        start, end = green, red
    rgb = tuple(int(round(start[i] + (end[i] - start[i]) * frac)) for i in range(3))
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def add_atom_esp_spheres(view, mol, esp_values, opacity=0.85, size_variation=0.2):
    """原子ごとに、静電ポテンシャル(ESP)の値に応じたグラデーション色の
    半透明の球を重ねて表示する(値が低いほど青、高いほど赤、中間は緑)。

    球の大きさ・不透明度の考え方はadd_atom_charge_spheres()と同じ
    (ファンデルワールス半径基準)。
    """
    coords = mol.atom_coords(unit="Angstrom")
    values = [v for _, v in esp_values]
    v_min, v_max = min(values), max(values)
    for (sym, val), pos in zip(esp_values, coords):
        color = _minmax_gradient_color(val, v_min, v_max)
        vdw_radius = _VDW_RADII.get(sym, _DEFAULT_VDW_RADIUS)
        frac = 0.5 if v_max - v_min <= 1e-12 else (val - v_min) / (v_max - v_min)
        radius = vdw_radius * (1.0 - size_variation / 2 + size_variation * frac)
        view.addSphere({
            "center": {"x": float(pos[0]), "y": float(pos[1]), "z": float(pos[2])},
            "radius": radius,
            "color": color,
            "opacity": opacity,
        })
    return view


def add_atom_charge_spheres(view, mol, charges, opacity=0.85, size_variation=0.2):
    """原子ごとに、Mulliken電荷の値に応じたグラデーション色の半透明の球を重ねて表示する。

    正電荷=青、中性付近=緑、負電荷=赤、というグラデーションになるよう
    _charge_gradient_color() で色を決めている。球の大きさは元素ごとの
    ファンデルワールス半径を基準にし(「小さすぎて見えない」という指摘への
    対応)、電荷の絶対値が大きいほどわずかに(既定で±10%)大きくなるように
    している(size_variationで調整幅を変更可能)。

    厳密には「全電子密度」は常に正の値であり符号を持たないため、
    電子密度そのものを正負で塗り分けることは物理的にできない。そのため、
    正負の符号を持つ量として代わりにMulliken電荷を使っている。

    なお、より厳密に「表面を電荷(静電ポテンシャル)で塗り分ける」には
    pyscf.tools.cubegen.mep() で計算した静電ポテンシャルを、密度の等値面に
    2つ目の物性値として重ね書きする手法(いわゆるESPマッピング)が本来の
    やり方だが、3Dmol.js側の対応APIの詳細を実機検証できておらず信頼性に
    不安があるため、今回は確実に動作するこの球表示で対応している。
    """
    coords = mol.atom_coords(unit="Angstrom")
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


def render_charges(mol, charges, esp_values=None, show_labels=True, width=500, height=400):
    """構造(ball and stick)+ 電荷で色分けした半透明の球 + (任意で)数値ラベルを表示する。

    esp_values(compute_esp_at_atoms()の戻り値)が渡された場合は、球の色を
    Mulliken電荷ではなく静電ポテンシャル(ESP、低い=青→中間=緑→高い=赤)で
    決める。esp_valuesを渡さない場合はこれまで通りMulliken電荷で色を決める。
    どちらの場合も、原子上の数値ラベル(show_labels=True時)は常にMulliken電荷
    (charges引数)の値を表示する。
    """
    import py3Dmol

    symbols = [mol.atom_symbol(i) for i in range(mol.natm)]
    coords = mol.atom_coords(unit="Angstrom")
    lines = [str(len(symbols)), "structure for atomic charge visualization"]
    for sym, pos in zip(symbols, coords):
        lines.append(f"{sym} {pos[0]:.6f} {pos[1]:.6f} {pos[2]:.6f}")
    xyz_block = "\n".join(lines)

    view = py3Dmol.view(width=width, height=height)
    view.addModel(xyz_block, "xyz")
    view.setStyle({"stick": {}, "sphere": {"scale": 0.3}})
    if esp_values is not None:
        add_atom_esp_spheres(view, mol, esp_values)
    else:
        add_atom_charge_spheres(view, mol, charges)
    if show_labels:
        add_atom_charge_labels(view, mol, charges)
    view.zoomTo()
    return view


def render_density(mol, mf, isovals=(0.002, 0.02, 0.2), width=500, height=400):
    """(現在gui.pyからは未使用。将来また使う可能性を考えて残している)

    全電子密度を、淡色(低密度)から濃色(高密度)へのグラデーションになるよう
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
    colors = ["#ffcc00", "#ff5500", "#880000"]
    opacities = [0.55, 0.75, 0.92]

    view = py3Dmol.view(width=width, height=height)
    view.addModel(cube_data, "cube")
    view.setStyle({"stick": {}})
    for isoval, color, opacity in zip(isovals, colors, opacities):
        view.addVolumetricData(cube_data, "cube", {"isoval": isoval, "color": color, "opacity": opacity})
    view.zoomTo()
    return view
