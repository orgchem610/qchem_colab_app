"""
tests/test_githooks.py
----------------------
.githooks/ のgitフック(mainブランチにAGENTS.mdを入れないための仕組み)の動作確認。
一時的なgitリポジトリを作り、「mainでAGENTS.mdを追跡したままコミットすると拒否される」
「developでは許可される」「main・タグへのpushにAGENTS.mdが含まれると中止される」を確かめる。
(リポジトリ自身のAGENTS.mdは参照しない。一時リポジトリの中に、同じ名前のファイルを作るだけ。)
gitが使えない環境では、動作の確認だけスキップされる。
"""

import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HOOKS_DIR = os.path.join(ROOT, ".githooks")
HOOK_FILES = ("check-agents.sh", "pre-commit", "pre-merge-commit", "pre-push")
ZERO = "0" * 40
HAS_GIT = shutil.which("git") is not None


class TestHookFiles(unittest.TestCase):
    def test_files_exist_and_are_executable(self):
        for name in HOOK_FILES:
            path = os.path.join(HOOKS_DIR, name)
            self.assertTrue(os.path.isfile(path), name)
            self.assertTrue(os.access(path, os.X_OK),
                            f"{name} に実行権限がありません(chmod +x .githooks/* を実行してください)")

    def test_files_start_with_a_shebang(self):
        for name in HOOK_FILES:
            with open(os.path.join(HOOKS_DIR, name), encoding="utf-8") as f:
                self.assertEqual(f.readline().strip(), "#!/bin/sh", name)


@unittest.skipUnless(HAS_GIT, "gitが使えないためスキップ")
class TestHookBehaviour(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="qchem_hooks_test_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = os.path.join(self.tmp, "repo")
        os.makedirs(self.repo)
        # 利用者のグローバルなgit設定の影響を受けないようにする
        self.env = dict(os.environ, HOME=self.tmp, XDG_CONFIG_HOME=self.tmp,
                        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
                        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
        self.git("init", "-q")
        self.git("symbolic-ref", "HEAD", "refs/heads/main")
        shutil.copytree(HOOKS_DIR, os.path.join(self.repo, ".githooks"))
        self.git("config", "core.hooksPath", ".githooks")
        self.write("app.py", "print('hello')\n")
        self.git("add", "app.py")
        self.git("commit", "-q", "-m", "init")
        self.base_sha = self.git("rev-parse", "HEAD").stdout.strip()

    def git(self, *args, check=True):
        result = subprocess.run(["git", *args], cwd=self.repo, env=self.env,
                                capture_output=True, text=True, encoding="utf-8")
        if check and result.returncode != 0:
            self.fail(f"git {' '.join(args)} が失敗しました: {result.stderr}")
        return result

    def write(self, name, text):
        with open(os.path.join(self.repo, name), "w", encoding="utf-8") as f:
            f.write(text)

    def commit_with_agents_md(self, message):
        self.write("AGENTS.md", "notes\n")
        self.git("add", "AGENTS.md")
        return self.git("commit", "-q", "-m", message, check=False)

    def run_pre_push(self, local_sha, remote_ref):
        line = f"refs/heads/x {local_sha} {remote_ref} {ZERO}\n"
        return subprocess.run(["sh", os.path.join(".githooks", "pre-push"), "origin", "url"],
                              cwd=self.repo, env=self.env, input=line,
                              capture_output=True, text=True, encoding="utf-8")

    # --- pre-commit ---------------------------------------------------------
    def test_commit_on_main_is_rejected_when_agents_md_is_tracked(self):
        result = self.commit_with_agents_md("bad")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("git rm --cached", result.stderr)

    def test_commit_on_main_without_agents_md_is_allowed(self):
        self.write("app.py", "print('changed')\n")
        self.git("add", "app.py")
        self.assertEqual(self.git("commit", "-q", "-m", "ok", check=False).returncode, 0)

    def test_commit_on_develop_with_agents_md_is_allowed(self):
        self.git("checkout", "-q", "-b", "develop")
        self.assertEqual(self.commit_with_agents_md("track").returncode, 0)

    # --- pre-merge-commit(developからmainへのマージ) -------------------------
    def _develop_with_agents_md(self):
        self.git("checkout", "-q", "-b", "develop")
        self.assertEqual(self.commit_with_agents_md("track").returncode, 0)
        self.git("checkout", "-q", "main")

    def test_merge_commit_is_rejected_until_agents_md_is_removed_from_the_index(self):
        self._develop_with_agents_md()
        self.git("merge", "--no-ff", "--no-commit", "develop")
        rejected = self.git("commit", "-q", "-m", "merge", check=False)
        self.assertNotEqual(rejected.returncode, 0)
        self.git("rm", "-q", "--cached", "--ignore-unmatch", "AGENTS.md")
        accepted = self.git("commit", "-q", "-m", "merge", check=False)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertEqual(self.git("ls-files", "AGENTS.md").stdout.strip(), "")
        self.assertTrue(os.path.exists(os.path.join(self.repo, "AGENTS.md")))   # 作業フォルダには残る

    def test_plain_merge_that_would_commit_automatically_is_rejected(self):
        self._develop_with_agents_md()
        result = self.git("merge", "--no-ff", "-m", "auto", "develop", check=False)
        self.assertNotEqual(self.git("log", "--format=%s", "-1").stdout.strip(), "auto", result.stderr)

    # --- pre-push -------------------------------------------------------------
    def test_push_of_main_is_stopped_when_the_commit_contains_agents_md(self):
        self.git("checkout", "-q", "-b", "develop")
        self.commit_with_agents_md("track")
        sha = self.git("rev-parse", "HEAD").stdout.strip()
        self.assertEqual(self.run_pre_push(sha, "refs/heads/main").returncode, 1)

    def test_push_of_develop_with_agents_md_is_allowed(self):
        self.git("checkout", "-q", "-b", "develop")
        self.commit_with_agents_md("track")
        sha = self.git("rev-parse", "HEAD").stdout.strip()
        self.assertEqual(self.run_pre_push(sha, "refs/heads/develop").returncode, 0)

    def test_push_of_main_without_agents_md_is_allowed(self):
        self.assertEqual(self.run_pre_push(self.base_sha, "refs/heads/main").returncode, 0)

    def test_push_of_a_tag_on_a_commit_with_agents_md_is_stopped(self):
        self.git("checkout", "-q", "-b", "develop")
        self.commit_with_agents_md("track")
        self.git("tag", "-a", "v9.9.9", "-m", "x")
        tag_sha = self.git("rev-parse", "v9.9.9").stdout.strip()        # 注釈付きタグ自体のID
        self.assertEqual(self.run_pre_push(tag_sha, "refs/tags/v9.9.9").returncode, 1)

    def test_deleting_a_remote_branch_is_not_blocked(self):
        self.assertEqual(self.run_pre_push(ZERO, "refs/heads/main").returncode, 0)


if __name__ == "__main__":
    unittest.main()
