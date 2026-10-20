"""
common_backend.version
----------------------
リポジトリ全体のリリース番号(Gitタグ)。ここ1か所だけに書く。

画面(gui)のタイトル、UMA版の計算ログ・出力ファイルのコメント、READMEとの整合検査は、この値を直接importして使う
(pyscf_backend・uma_backend には別名を置かない)。
新しいタグを打つ前に更新するのは、このファイルと README.md 冒頭の「現在のバージョン」の2か所。
"""

__version__ = "0.2.2"
