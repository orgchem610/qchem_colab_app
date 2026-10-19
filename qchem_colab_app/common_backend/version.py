"""
common_backend.version
--------------
リポジトリ全体のリリース番号(Gitタグ)。ここ1か所だけに書く。

pyscf_backend.__version__・uma_backend.__version__ は、この値をそのまま使えるようにした別名なので、
新しいタグを打つ前に更新するのは、このファイルと README.md 冒頭の「現在のバージョン」の2か所。
(以前は、pyscf_backend と uma_backend の __init__.py にそれぞれ書いており、更新漏れが起きたことがある。)
"""

__version__ = "0.2.1"
