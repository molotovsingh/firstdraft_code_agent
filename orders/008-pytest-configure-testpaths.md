# Order 008 — Configure pytest to only collect tests under `tests/`

Owner: Claude
Scope: Prevent accidental collection of helper scripts in `scripts/` that contain `test_*` functions.

Changes
- Add `pytest.ini` in repo root:
```
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
```

Acceptance Criteria
- `pytest -q` does not attempt to collect `scripts/quick_block0_test.py`.
- No changes to test code under `tests/`.

Validation
- Run `pytest -q` locally; ensure the previous error about missing fixture `file_path` from the script no longer occurs.
