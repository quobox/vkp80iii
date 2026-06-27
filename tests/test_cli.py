"""Tests for the command-line interface (python -m vkp80iii), hardware-free."""

from __future__ import annotations

import pytest

from vkp80iii.__main__ import main


def test_hexdump(capsys):
    rc = main(["hexdump", "--paper-width-mm", "55", "--left-offset-dots", "24"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "self-test" in out
    assert "1b 40" in out  # ESC @ at the start of the dumped bytes


def test_selftest_dry_run(capsys):
    assert main(["selftest", "--dry-run"]) == 0
    assert "self-test ticket sent" in capsys.readouterr().out


def test_selftest_cut_dry_run():
    assert main(["selftest", "--dry-run", "--cut"]) == 0


def test_calibrate_dry_run(capsys):
    assert main(["calibrate", "--dry-run"]) == 0
    assert "ruler" in capsys.readouterr().out


def test_status_no_reply_returns_2(capsys):
    # DummyTransport replies with nothing -> StatusTimeout -> exit code 2
    assert main(["status", "--dry-run"]) == 2
    assert "no status reply" in capsys.readouterr().err


def test_info_dry_run_runs():
    # device_id/rom return empty (no reply) but don't raise -> exit 0
    assert main(["info", "--dry-run"]) == 0


def test_version_exits():
    with pytest.raises(SystemExit):
        main(["--version"])


def test_timeout_out_of_range_errors():
    # --timeout > 255 must be a clean argparse error, not a CommandError crash
    with pytest.raises(SystemExit):
        main(["selftest", "--dry-run", "--timeout", "300"])
