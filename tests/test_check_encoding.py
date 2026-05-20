from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_encoding.py"
MODULE_SPEC = importlib.util.spec_from_file_location("check_encoding", MODULE_PATH)
assert MODULE_SPEC is not None
assert MODULE_SPEC.loader is not None
check_encoding = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(check_encoding)


def test_check_file_detects_utf8_bom(tmp_path: Path) -> None:
    path = tmp_path / "bom.md"
    path.write_bytes(check_encoding.UTF8_BOM + b"text")

    assert check_encoding.check_file(path) == ["starts with UTF-8 BOM"]


def test_check_file_detects_invalid_utf8(tmp_path: Path) -> None:
    path = tmp_path / "invalid.md"
    path.write_bytes(b"\xff\xfe\x00")

    problems = check_encoding.check_file(path)

    assert len(problems) == 1
    assert problems[0].startswith("not valid UTF-8:")


def test_check_file_detects_mojibake_marker(tmp_path: Path) -> None:
    path = tmp_path / "broken.md"
    marker = check_encoding.MOJIBAKE_MARKERS[0]
    path.write_text(f"{marker} broken", encoding="utf-8")

    assert check_encoding.check_file(path) == [f"mojibake marker found: {marker!r}"]


def test_check_file_accepts_valid_utf8(tmp_path: Path) -> None:
    path = tmp_path / "ok.md"
    path.write_text("status: in-progress\n", encoding="utf-8")

    assert check_encoding.check_file(path) == []


def test_collect_paths_uses_git_ls_files(monkeypatch) -> None:
    def fake_check_output(command: list[str], text: bool) -> str:
        assert command == ["git", "ls-files"]
        assert text is True
        return "a.py\nb.md\n"

    monkeypatch.setattr(check_encoding.subprocess, "check_output", fake_check_output)

    assert check_encoding.collect_paths([]) == [Path("a.py"), Path("b.md")]


def test_main_returns_failure_when_problem_found(monkeypatch, tmp_path: Path, capsys) -> None:
    path = tmp_path / "bad.md"
    path.write_bytes(check_encoding.UTF8_BOM + b"bad")

    monkeypatch.setattr(check_encoding.sys, "argv", ["check_encoding.py", str(path)])

    assert check_encoding.main() == 1
    assert "FAIL" in capsys.readouterr().out


def test_main_returns_success_for_clean_file(monkeypatch, tmp_path: Path, capsys) -> None:
    path = tmp_path / "ok.md"
    path.write_text("all good\n", encoding="utf-8")

    monkeypatch.setattr(check_encoding.sys, "argv", ["check_encoding.py", str(path)])

    assert check_encoding.main() == 0
    assert "OK 1 text files checked." in capsys.readouterr().out
