# Source release validation — 2026-11-16

## Provenance and policy

The imported unified source matches the code snapshot used by the completed `20261103_four_rules_alpha10` run (comparison excluding Git and Python caches). Conversion and cleaning algorithms are unchanged during this packaging pass. New material comprises documentation, an explicit alpha10 example, CI and a hash-checked local model importer.

The recorded full run completed 1721 repositories, 972324 episodes and 1077451809 frames (10207.572824 hours), with zero failed repositories and both execution/verification exit codes 0. These are existing run records checked during packaging, not a newly repeated full cleaning. Validation covers exact inventory, metadata schemas/counts and publication markers; it does not claim complete video decoding. All frames remain present; `quality.valid` is a per-frame annotation.

## Publication boundaries

- The repository has fresh Git history, without imported production history, logs, data, credentials or local configurations.
- Source scan found no credential patterns or absolute runtime paths. One historical relative dataset identifier contains nested `mnt/...` components; it is intentionally preserved and explained in THIRD_PARTY_NOTICES.md.
- FK models are ignored local resources. Public archive and Git exclude them. The manifest/importer checks 11 resource files, including the supplied model license. Their redistribution permissions have not been fully audited.
- Original Any4LeRobot MIT attribution is preserved. Dataset licenses are separate.
- Blur-screening experiments are not part of the alpha10 four-rule pipeline and are not silently included as a fifth filter.
- Dependencies were tested in an isolated test environment inheriting the existing Linux runtime; this is not a clean-system installation test.

## Current packaging tests

Results are appended after execution below. The historical VALIDATION.md retains the original dated records and their limitations.

- Full Linux regression suite with local authorized models: **258 passed, 8 subtests passed**, 340.60 seconds.
- Public ZIP extracted into a separate directory with no robot_models: **20 passed**, 38.91 seconds.
- Model importer: all11 files passed size/SHA256 verification; empty model source rejected.
- Python compile checks passed. One existing anyio plugin deprecation warning is unrelated to pipeline correctness.
- Scoped quality-only tests must use `python -m pytest -c pytest.ini -q quality/tests`; omitting `-c` selects the nested package configuration and can cause import errors. The documented full-root suite passes.

## Public PR cleanup validation

After simplifying batch planning, resume field comparison and FK initialization, the full Linux suite passed **264 tests and 8 subtests** (88.34 seconds), including six new resume/planning regression cases. Core modules were subsequently formatted with per-file AST equivalence checks; policy semantics were unchanged. Public CI runs the existing 20 model-independent tests; complete FK tests require the separately imported models. README table rows and details blocks were verified unchanged.
