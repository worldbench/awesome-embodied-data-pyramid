# LeRobot Release Pipeline

Convert six dataset families to **LeRobot v3**, check frame quality, and export training data with a `quality.valid` flag. Run conversion and cleaning together, or clean an existing supported repository on its own.

This directory contains the conversion engines, robot-specific adapters, four-rule quality checks, and resumable release workflow used by DataPyramid. Data paths and worker counts are configured in JSON.

[Quick start](docs/QUICKSTART.md) · [FK model setup](docs/ASSETS.md) · [Validation](docs/RELEASE_VALIDATION.md) · [Third-party notices](THIRD_PARTY_NOTICES.md)

## Supported datasets

The release manifest covers **1,721 repositories, 972,324 episodes, and 1,077,451,809 frames**:

| Dataset family | Repositories | Episodes | Hours |
|---|---:|---:|---:|
| AgiBot Beta | 202 | 153,689 | 2,539.82 |
| ABC-130k | 2 | 107,648 | 2,716.32 |
| AgiBotWorld2026 | 4 | 31,017 | 621.92 |
| Galaxea Lite / Pro | 2 | 19,105 | 462.33 |
| InternData A1 | 1,476 | 593,663 | 3,701.47 |
| RoboMIND | 35 | 67,202 | 165.70 |
| **Total** | **1,721** | **972,324** | **10,207.57** |

These counts describe the processed inventory, not current download availability. The full-release workflow targets the exact source versions and repository schemas in [the manifest](manifests/repositories.json). It does not produce these counts from arbitrary dataset versions. RoboMIND AgileX and RoboMIND simulation are outside this release.

## Installation

Run the commands below from `tools/lerobot_pipeline/`. Use Linux, Python 3.12, and FFmpeg 7, with `ffmpeg`, `ffprobe`, `bash`, and `flock` available. TorchCodec also needs the FFmpeg shared libraries; a standalone static executable is not sufficient.

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-runtime.txt
```

The requirements record versions from a working environment, rather than a cross-platform lockfile. See the [validation record](VALIDATION.md) for the tested scope.

**Import FK models before cleaning.** Model assets are distributed separately from the code and require their own usage rights. The importer verifies the expected paths, sizes, and SHA256 hashes:

```bash
python scripts/import_robot_models.py --source /path/to/authorized/robot_models
python scripts/import_robot_models.py --check
```

See [FK model setup](docs/ASSETS.md) for details. Without these assets, use planning and the tests that do not require models; an asset-free run does not reproduce the full cleaning pipeline.

## Clean an existing repository

For one supported LeRobot repository, use the quality exporter directly:

```bash
PYTHONPATH=quality/src python -m lerobot_quality.export \
  --repo /path/to/converted/repository \
  --output /path/to/new/cleaned/repository \
  --four-rules-config configs/four_rules.json
```

This selects the **alpha10 four-rule policy**. It retains every row and original column, adds `quality.valid`, and links to the original videos. The output directory must be new.

## Run the full release

### 1. Configure paths

```bash
cp configs/example.alpha10.json configs/local.json
```

Edit the four roots in `configs/local.json`: `raw_root`, `converted_root`, `cleaned_root`, and `work_root`. Keep them separate and non-overlapping. Relative paths resolve from the **config file's directory**. Adjust `conversion_workers` and `cleaning_workers` to match available CPU, memory, and disk capacity.

Keep the example's `four_rules` object to select alpha10. Omitting that object selects the legacy policy; [example.json](configs/example.json) is the legacy configuration.

Place the original releases under `raw_root` with this layout:

```text
raw/
├── AgiBot-World-Beta/
├── ABC-130k/
├── AgiBotWorld2026/
├── Galaxea-Open-World-Dataset/
├── InternData-A1/
└── RoboMIND-v1.2/
```

Preserve accompanying indexes and annotations, including RoboMIND's `static` files. Source selection and known exclusions are defined in [release.json](configs/release.json).

### 2. Check and run

```bash
python pipeline.py doctor --config configs/local.json
python pipeline.py plan --config configs/local.json
python pipeline.py run --config configs/local.json --execute
```

`doctor` checks prerequisites and `plan` previews the work. `run` performs conversion, manifest verification, cleaning, and output verification. Without `--execute`, `run`, `convert`, and `clean` only print the plan.

To run one phase or dataset family:

```bash
python pipeline.py convert --config configs/local.json --dataset beta --execute
python pipeline.py clean --config configs/local.json --dataset beta --execute --resume
```

Available family names are `beta`, `abc`, `agibot2026`, `galaxea`, `interndata`, and `robomind`; the default is `all`.

### 3. Resume interrupted work

```bash
python pipeline.py run --config configs/local.json --execute --resume
```

Reuse the same configuration and directories. Completed cleaning repositories are verified and reused; failed repositories are rerun. Source data is read-only, and unknown nonempty output directories are not overwritten. If paths, policies, or the manifest change, use new output and work directories.

## Quality checks

The alpha10 policy combines basic numerical, mask, index, and timestamp validation with four checks:

1. **Range outliers.** For each repository and channel, compute exact q01/q99 quantiles from finite, mask-valid samples. Retain values within `q01 − 10 × (q99 − q01)` and `q99 + 10 × (q99 − q01)`, including the boundaries.
2. **Abrupt motion.** Compute velocity and acceleration using actual timestamps. Flag magnitudes above `q99 + 10 × (q99 − q01)` for each channel. Differences do not cross episode boundaries, frame gaps, or invalid masks.
3. **Forward-kinematics consistency.** Compare observed end-effector poses with FK using a 1 cm position tolerance and a 2° rotation tolerance. Checks require valid joints, observed poses, and the configured model and coordinate mapping. Unavailable checks are recorded as skipped.
4. **State–action consistency.** Smooth joint positions over five frames, then search lags within ±15 frames for the best velocity-direction agreement. Flag an action frame when agreement is below 0.5 among at least two joints moving faster than 0.01 rad/s in both signals. Static, missing, masked, and boundary samples are skipped.

Parameters are in [four_rules.json](configs/four_rules.json). Range rules apply to supported joint, EE-position, and additional numeric channels, not gripper, dexterous-hand, or quaternion components. Quaternion motion uses the shortest rotation, treating `q` and `−q` as equivalent. Native velocity fields are not differentiated as positions, and incompatible state/action channels are not paired.

These are project-specific quality checks, not a complete reproduction of a paper's filtering algorithm. They do not remove episodes, trim stationary segments, or filter blurry videos. High FK failure rates in some Split Aloha and Beta repositories still require model/calibration review; they are not conclusive evidence of bad demonstrations.

## Outputs and training use

```text
cleaned/<repository>/
├── data/chunk-*/file-*.parquet   # Original columns plus quality.valid
├── meta/                       # LeRobot v3 metadata
├── quality/                    # Reports, rule coverage, and skip reasons
└── videos -> converted videos  # Original video files remain in place
```

**Apply `quality.valid` explicitly during training, together with the original action/EE masks.** Cleaning does not delete rows, change episode/frame indices or timestamps, or re-encode videos. The source videos must remain accessible through the links. Files under `quality/` are diagnostic reports, not training Parquet files.

Useful reports include:

- `quality/summary.json`: policy parameters and quality summary.
- `quality/frames.parquet`: combined frame results and FK details.
- `quality/signal/frames.parquet`: signal-rule flags and coverage.
- `quality/signal/bounds.json`: per-channel quantiles and thresholds.
- `quality/signal/state_action_episodes.json`: selected lags and skip reasons.

Rule hits can overlap; do not sum them to estimate the final invalid-frame rate. Exact quantiles use temporary disk files, and complete episodes are processed in memory. Set cleaning concurrency with these resource costs in mind.

## Verification and tests

Verify existing outputs without modifying them:

```bash
python pipeline.py verify --config configs/local.json --kind converted
python pipeline.py verify --config configs/local.json --kind cleaned
```

Verification checks manifest paths, schemas, episode/frame counts, FPS, completion records, and video links. It does not decode every video frame or establish video byte-for-byte equivalence. For read-only checks of a directory containing other datasets, add `--allow-extra`.

Install test dependencies and run the tests that do not require external model assets:

```bash
python -m pip install -r requirements-test.txt
python -m pytest -q tests/test_pipeline.py quality/tests/test_schema.py quality/tests/test_signal_quality.py
```

After importing FK models, run the full suite:

```bash
python scripts/import_robot_models.py --check
python -m pytest -q
```

See [release validation](docs/RELEASE_VALIDATION.md) for results and limits. Code licensing and third-party attribution are documented in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md); dataset and robot-model licenses remain separate.
