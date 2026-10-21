"""
common_backend.cube
-------------------
Gaussian cube形式のファイルを読み取る関数。計算エンジン(PySCF等)にも画面にも依存しない
(標準ライブラリだけで動く)。

cube形式は「2行のコメント」「原子数と原点」「3方向の軸情報」「原子リスト(原子数分)」に続けて、
格子点の値がスペース/改行区切りで並ぶ。

(v0.2.2で、pyscf_backend/visualizer_pyscf.py の内部関数から、この共通部品に移した。)
"""


def max_abs_value(cube_path):
    """cubeファイルを直接読み、格子点上の値の最大絶対値を求める。

    ヘッダー(コメント2行・原子数行・軸3行・原子リスト)を読み飛ばし、値の本体だけを数値として読み取る。
    値が1つもないときは 0.0 を返す。
    """
    with open(cube_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    natm = abs(int(lines[2].split()[0]))
    header_lines = 2 + 1 + 3 + natm  # コメント2 + 原子数行 + 軸3行 + 原子natm行
    values = []
    for line in lines[header_lines:]:
        values.extend(float(tok) for tok in line.split())
    return max(abs(v) for v in values) if values else 0.0
