# Contributing

Thanks for your interest in improving `vkp80iii`. It's a small, focused library;
contributions of any size are welcome.

## Development setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/quobox/vkp80iii
cd vkp80iii
uv sync          # library + dev tools + optional backends, pinned via uv.lock
prek install     # install the pre-commit hooks (https://github.com/j178/prek)
```

## Before opening a pull request

Run the checks (the pre-commit hooks run these on every commit):

```bash
uv run ruff format .           # format
uv run ruff check .            # lint
uv run pyrefly check           # type-check
uv run pytest --cov=vkp80iii   # tests + coverage (must stay >= 90%)
```

All four must pass. They use the project's pinned tool versions through `uv`, so
there is no extra setup beyond `uv sync` — and no version drift.

## Editor setup (VS Code)

Open the project and accept the recommended extensions (`.vscode/extensions.json`):
Python, **Ruff**, **Pyrefly**, EditorConfig and Even Better TOML. The committed
`.vscode/settings.json` points them at the **uv-managed `.venv`**, so Ruff, pytest
and the type-checker are the project-pinned versions — the same ones the
pre-commit hooks and CI use (no version drift). Format, lint-fix and import-sort
run on save.

## Guidelines

- **Branch off `master`** and open your pull request against `master`.
- Keep code **formatted** (ruff), **typed** (pyrefly clean) and **tested**.
  New features need tests; bug fixes should add a regression test. Most of the
  suite is hardware-free (byte-level checks + `DummyTransport`), so you can
  contribute without owning a printer.
- Match the surrounding style. Public functions get a short docstring; for
  command builders, note the byte sequence / valid ranges from the manual.
- Add an entry under `## [Unreleased]` in [`CHANGELOG.md`](CHANGELOG.md).

## Hardware notes

`UsbLpTransport` talks to `/dev/usb/lp0` and needs write access (the `lp` group
or a udev rule — see the README). The command encoder and most of the logic can
be developed and tested entirely without hardware.

Opt-in **integration tests** (`tests/integration/`, marked `hardware`) run
against a real printer. They are deselected by default and skip when no printer
is reachable, so they never affect CI or a normal `pytest` run:

```bash
uv run pytest -m hardware                  # status/query reads only (no paper)
VKP80III_PRINT=1 uv run pytest -m hardware  # also the paper-consuming smoke tests
```

## Licensing of contributions

By submitting a contribution you agree that it is licensed under the project's
[MIT License](LICENSE) (inbound = outbound).
