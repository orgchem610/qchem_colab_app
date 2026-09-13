"""
qcapp.io_reader
----------------
構造ファイルの読み込みと、計算実行前の入力チェックをまとめたモジュール。

【今回のプロトタイプのスコープ】
    標準的な .xyz 形式のみをサポートします(外部ライブラリに依存しない
    自前の最小パーサーです)。
    .mol / .sdf / .pdb / .com / .gjf などへの対応は、このモジュールを
    拡張するか、ASE/RDKit等の導入を検討する段階で追加してください。
    read_structure() が返す Structure の形さえ変えなければ、
    engine.py より後段のコードには影響しません。
"""

from dataclasses import dataclass
import math
import re

# 元素記号 -> 原子番号 の対応表(H〜Xe程度まで用意)
ATOMIC_NUMBERS = {
    "H": 1, "He": 2, "Li": 3, "Be": 4, "B": 5, "C": 6, "N": 7, "O": 8, "F": 9, "Ne": 10,
    "Na": 11, "Mg": 12, "Al": 13, "Si": 14, "P": 15, "S": 16, "Cl": 17, "Ar": 18,
    "K": 19, "Ca": 20, "Sc": 21, "Ti": 22, "V": 23, "Cr": 24, "Mn": 25, "Fe": 26,
    "Co": 27, "Ni": 28, "Cu": 29, "Zn": 30, "Ga": 31, "Ge": 32, "As": 33, "Se": 34,
    "Br": 35, "Kr": 36, "Rb": 37, "Sr": 38, "Y": 39, "Zr": 40, "Nb": 41, "Mo": 42,
    "Tc": 43, "Ru": 44, "Rh": 45, "Pd": 46, "Ag": 47, "Cd": 48, "In": 49, "Sn": 50,
    "Sb": 51, "Te": 52, "I": 53, "Xe": 54,
}

# 現時点で「遷移金属」として扱う元素(3d, 4d, 5dの一部)。
# 3-21G/HFのプロトタイプではこれらの元素は未対応であることをユーザーに伝えるために使う。
TRANSITION_METAL_SYMBOLS = set(
    "Sc Ti V Cr Mn Fe Co Ni Cu Zn".split()
    + "Y Zr Nb Mo Tc Ru Rh Pd Ag Cd".split()
    + "Hf Ta W Re Os Ir Pt Au Hg".split()
)


class StructureError(ValueError):
    """構造・電荷・スピン多重度の入力に問題があるときの例外。
    メッセージはそのままGUI上にエラーメッセージとして表示する前提で、
    日本語で分かりやすく書いています。
    """
    pass


@dataclass
class Structure:
    symbols: list   # 元素記号のリスト 例: ["O", "H", "H"]
    coords: list    # [[x, y, z], ...] 単位はÅ(オングストローム)
    comment: str = ""  # xyzファイル2行目のコメント


def read_xyz(filepath: str) -> Structure:
    """標準的な .xyz 形式のファイルを読み込む。

    フォーマット:
        1行目: 原子数
        2行目: コメント(何でもよい)
        3行目以降: 元素記号 x y z   (空白区切り、単位はÅ)
    """
    with open(filepath, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f]

    if len(lines) < 3:
        raise StructureError(
            f"'{filepath}' の内容が短すぎます。標準的な.xyzファイル"
            "(1行目:原子数, 2行目:コメント, 3行目以降:元素記号と座標)か確認してください。"
        )

    try:
        natoms = int(lines[0].strip())
    except ValueError:
        raise StructureError(
            f"'{filepath}' の1行目 ('{lines[0]}') が原子数(整数)として読み取れません。"
            "標準的な.xyzファイル形式か確認してください。"
        )

    comment = lines[1].strip()
    atom_lines = [l for l in lines[2:] if l.strip() != ""]

    if len(atom_lines) < natoms:
        raise StructureError(
            f"'{filepath}' の1行目には原子数 {natoms} と書かれていますが、"
            f"実際に読み取れた原子の行数は {len(atom_lines)} 行でした。"
            "ファイルが途中で切れていないか確認してください。"
        )

    symbols, coords = [], []
    for i, line in enumerate(atom_lines[:natoms], start=3):
        parts = re.split(r"\s+", line.strip())
        if len(parts) < 4:
            raise StructureError(
                f"'{filepath}' の{i}行目 ('{line}') が「元素記号 x y z」の形式として"
                "読み取れません。"
            )
        symbol = parts[0][0].upper() + parts[0][1:].lower() if len(parts[0]) > 1 else parts[0].upper()
        if symbol not in ATOMIC_NUMBERS:
            raise StructureError(
                f"'{filepath}' の{i}行目にある元素記号 '{parts[0]}' を認識できません。"
                "対応している元素か、スペルミスがないか確認してください。"
            )
        try:
            x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
        except ValueError:
            raise StructureError(f"'{filepath}' の{i}行目 ('{line}') の座標を数値として読み取れません。")
        symbols.append(symbol)
        coords.append([x, y, z])

    return Structure(symbols=symbols, coords=coords, comment=comment)


def validate_structure(structure: Structure, min_distance: float = 0.4) -> None:
    """原子数・原子間距離の妥当性をチェックする。問題があれば StructureError を送出する。"""
    n = len(structure.symbols)
    if n == 0:
        raise StructureError("構造に原子が1つも含まれていません。")

    for i in range(n):
        xi, yi, zi = structure.coords[i]
        for j in range(i + 1, n):
            xj, yj, zj = structure.coords[j]
            d = math.sqrt((xi - xj) ** 2 + (yi - yj) ** 2 + (zi - zj) ** 2)
            if d < min_distance:
                raise StructureError(
                    f"{i + 1}番目の原子({structure.symbols[i]})と"
                    f"{j + 1}番目の原子({structure.symbols[j]})の距離が"
                    f"{d:.3f} Åしかありません(しきい値 {min_distance} Å)。"
                    "構造ファイルの座標が正しいか確認してください。"
                )


def contains_transition_metal(structure: Structure) -> bool:
    """アップロードされた構造に遷移金属元素が含まれているかを判定する。

    現時点(HF/3-21Gのみのプロトタイプ)では未対応の元素が含まれていることを
    GUI側で明示的にエラー表示するために使用する。
    """
    return any(s in TRANSITION_METAL_SYMBOLS for s in structure.symbols)


def validate_charge_and_multiplicity(structure: Structure, charge: int, multiplicity: int) -> None:
    """電荷とスピン多重度の整合性をチェックする。

    - スピン多重度は1以上の整数でなければならない
    - 全電子数と多重度の偶奇が一致しなければ、その組み合わせは化学的に成立しない
    """
    if multiplicity < 1:
        raise StructureError(
            f"スピン多重度は1以上の整数を指定してください(入力値: {multiplicity})。"
            "不対電子のない閉殻分子であれば1を指定してください。"
        )

    total_electrons = sum(ATOMIC_NUMBERS[s] for s in structure.symbols) - charge
    if total_electrons < 0:
        raise StructureError(
            f"電荷 {charge:+d} が大きすぎて、電子数が負の値({total_electrons})になります。"
            "電荷の設定を見直してください。"
        )

    n_unpaired = multiplicity - 1
    if total_electrons < n_unpaired or (total_electrons - n_unpaired) % 2 != 0:
        raise StructureError(
            f"電荷({charge:+d})とスピン多重度({multiplicity})の組み合わせが"
            f"化学的に成立しません(このときの全電子数は{total_electrons}個です)。\n"
            "目安: 全電子数が偶数ならスピン多重度は1,3,5...(奇数)、"
            "全電子数が奇数ならスピン多重度は2,4,6...(偶数)を指定してください。"
        )
