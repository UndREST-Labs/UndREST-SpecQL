"""Tests for source-repository revision pinning."""

import refresh_database as refresh


def test_manage_source_repo_checks_out_pinned_commit(tmp_path, monkeypatch):
    repo = tmp_path / "source"
    (repo / ".git").mkdir(parents=True)
    calls = []
    pinned = "0123456789abcdef0123456789abcdef01234567"

    def fake_run(command, cwd=None, capture=False):
        calls.append((command, cwd))
        return True, pinned + "\n" if command == ["git", "rev-parse", "HEAD"] else ""

    monkeypatch.setattr(refresh, "run_command", fake_run)

    assert refresh.manage_source_repo(
        repo_url="https://github.com/example/source.git",
        specs_dir=str(repo),
        fresh=False,
        branch="main",
        spec_path="openapi",
        include_all=True,
        source_commit=pinned,
    )

    commands = [command for command, _cwd in calls]
    assert ["git", "fetch", "--depth", "1", "origin", "0123456789abcdef0123456789abcdef01234567"] in commands
    assert ["git", "checkout", "--detach", "0123456789abcdef0123456789abcdef01234567"] in commands
    assert not any(command[:3] == ["git", "reset", "--hard"] for command in commands)


def test_manage_source_repo_rejects_invalid_commit_pin(tmp_path):
    assert not refresh.manage_source_repo(
        repo_url="https://github.com/example/source.git",
        specs_dir=str(tmp_path / "source"),
        fresh=False,
        branch="main",
        spec_path="openapi",
        include_all=True,
        source_commit="not-a-full-sha",
    )


def test_manage_source_repo_rejects_mismatched_pinned_commit(tmp_path, monkeypatch):
    repo = tmp_path / "source"
    (repo / ".git").mkdir(parents=True)

    def fake_run(command, cwd=None, capture=False):
        if command == ["git", "rev-parse", "HEAD"]:
            return True, "ffffffffffffffffffffffffffffffffffffffff\n"
        return True, ""

    monkeypatch.setattr(refresh, "run_command", fake_run)

    assert not refresh.manage_source_repo(
        repo_url="https://github.com/example/source.git",
        specs_dir=str(repo),
        fresh=False,
        branch="main",
        spec_path="openapi",
        include_all=True,
        source_commit="0123456789abcdef0123456789abcdef01234567",
    )


def test_manage_source_repo_uses_branch_without_pin(tmp_path, monkeypatch):
    repo = tmp_path / "source"
    (repo / ".git").mkdir(parents=True)
    calls = []

    def fake_run(command, cwd=None, capture=False):
        calls.append((command, cwd))
        return True, ""

    monkeypatch.setattr(refresh, "run_command", fake_run)

    assert refresh.manage_source_repo(
        repo_url="https://github.com/example/source.git",
        specs_dir=str(repo),
        fresh=False,
        branch="main",
        spec_path="specification",
        include_all=True,
    )

    commands = [command for command, _cwd in calls]
    assert ["git", "fetch", "--depth", "1", "origin", "main"] in commands
    assert ["git", "reset", "--hard", "origin/main"] in commands
