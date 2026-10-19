#!/bin/sh
# mainブランチにAGENTS.mdが入らないようにするための検査。
# pre-commit・pre-merge-commit から呼ばれる(.githooks/ の説明は、AGENTS.mdの
# 「AGENTS.mdのGit管理」を参照)。
branch=$(git symbolic-ref --short -q HEAD)
if [ "$branch" = "main" ] && git ls-files --error-unmatch AGENTS.md >/dev/null 2>&1; then
  echo "エラー: mainブランチで AGENTS.md が追跡されています。コミットを中止しました。" >&2
  echo "  次のコマンドを実行してから、もう一度コミットしてください:" >&2
  echo "    git rm --cached --ignore-unmatch AGENTS.md" >&2
  exit 1
fi
exit 0
