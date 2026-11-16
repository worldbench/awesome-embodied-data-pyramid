# Quick start

Linux and Python 3.12 are the validated target. Work from this repository checkout. All paths are supplied through configuration.

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements-runtime.txt -r requirements-test.txt
python scripts/import_robot_models.py --source /path/to/authorized/robot_models
cp configs/example.alpha10.json configs/local.json
# Edit the four separate roots in configs/local.json.
python pipeline.py plan --config configs/local.json
python pipeline.py clean --config configs/local.json --execute
# On interruption, retain the same config and add --resume.
```

The uniform entry point reproduces the exact 1721-repository release, not an arbitrary input directory. For a single supported LeRobot repository:

```bash
PYTHONPATH=quality/src python -m lerobot_quality.export \
  --repo /path/to/converted/repository --output /path/to/new/cleaned/repository \
  --four-rules-config configs/four_rules.json
```

The output `data/chunk-*/file-*.parquet` retains all original rows and columns and adds `quality.valid`. Reports are under `quality/`; they are not the training data. Consumers must apply the validity mask explicitly. Video links require the original converted videos to remain accessible. Dataset metadata remains under `meta/`.

## Tests

```bash
# Public source, no external model assets:
python -m pytest -q tests/test_pipeline.py quality/tests/test_schema.py quality/tests/test_signal_quality.py
# Complete regression suite after importing assets:
python scripts/import_robot_models.py --check
python -m pytest -q
```

The runtime requirements record observed working versions; installing the entire conversion stack on a new system has not been revalidated during this packaging pass. See VALIDATION.md and docs/RELEASE_VALIDATION.md for exact tested scope.

For a quality-only run from the repository root, explicitly select the root configuration: `python -m pytest -c pytest.ini -q quality/tests`.
