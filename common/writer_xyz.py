"""
common.writer_xyz
-----------------
単一フレーム(最終構造用)および多フレーム(最適化トラジェクトリ用)の
.xyzファイル・文字列を書き出すモジュール。外部ライブラリに依存しない。

計算エンジン(qcapp=PySCF, 将来のuma_app等)に依存しない共通コードのため、
qcapp側のバージョン番号やモジュール固有の文言をここに埋め込まないこと
(comment引数はNoneならごく簡単な既定文言を使い、エンジン側の詳しい情報
[バージョン・手法名など]を含めたい場合は呼び出し側で組み立てて渡す)。

「最終構造をColabReactionにそのまま渡せる形式でダウンロードできるように」
という要望に対応するため、write_final_structure() が書き出すファイルは、
ColabReactionがreactant/productとして受け付ける標準的な.xyz形式
そのものにしている(独自拡張は入れていない)。
"""


def _format_xyz_block(symbols, coords, comment=""):
    lines = [str(len(symbols)), comment]
    for sym, xyz in zip(symbols, coords):
        x, y, z = xyz
        lines.append(f"{sym:<2s} {x:20.12f} {y:20.12f} {z:20.12f}")
    return "\n".join(lines)


def write_final_structure(symbols, coords, filepath, comment="Optimized structure"):
    """最終構造を単一フレームの標準.xyzとして書き出す。

    このファイルはColabReactionのreactant/productとしてそのまま
    アップロードできることを想定している。comment(バージョン・手法名等)は
    呼び出し側(qcapp側やuma_app側)で組み立てて渡すこと。
    """
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(_format_xyz_block(symbols, coords, comment) + "\n")


def write_trajectory(symbols, coords_history, filepath, energies=None):
    """最適化の全ステップを含む多フレーム.xyzを書き出す(Avogadro等の汎用ビューア向け)。"""
    blocks = []
    for i, coords in enumerate(coords_history):
        if energies and i < len(energies):
            comment = f"step {i}  E = {energies[i]:.8f} Hartree"
        else:
            comment = f"step {i}"
        blocks.append(_format_xyz_block(symbols, coords, comment))
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(blocks) + "\n")


def xyz_string(symbols, coords, comment=""):
    """ファイルに書き出さず、xyz形式の文字列だけを返す(py3Dmol等に直接渡す用)。"""
    return _format_xyz_block(symbols, coords, comment) + "\n"


def multiframe_xyz_string(symbols, coords_list, comments=None):
    """複数フレームをまとめたxyz文字列を返す(py3Dmolのアニメーション表示用)。"""
    blocks = []
    for i, coords in enumerate(coords_list):
        comment = comments[i] if comments and i < len(comments) else f"frame {i}"
        blocks.append(_format_xyz_block(symbols, coords, comment))
    return "\n".join(blocks) + "\n"
