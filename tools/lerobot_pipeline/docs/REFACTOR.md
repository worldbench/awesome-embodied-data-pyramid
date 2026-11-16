# Public-source cleanup

The six-family converters and four-rule numerical policy are unchanged. Batch planning now tracks only unique input paths: destination paths are already required to equal output_root / source.relative_to(input_root), so a second destination set was redundant. Resume expectations are expressed as named dictionaries rather than a long disjunction. Executable FK initialization follows the existing early-return branch directly instead of nesting under a redundant optional-path guard.

Overwrite prevention, manifest identity, locks, required model mappings, mask semantics, source/index alignment and completion checks remain. These conditions prevent data loss or invalid resume; they are not fallback behavior for unsupported inputs. Raw Python/JSON errors remain visible rather than being hidden by generic catch-and-continue logic.

This source is submitted as tools/lerobot_pipeline in the survey repository. Its MIT license applies within this directory; the parent survey repository retains its existing Apache-2.0 license. No production datasets or unverified model assets are included.

Core orchestration and quality modules use expanded statements and consistent formatting; formatting changes were checked for identical Python ASTs. Six regression cases explicitly cover successful resume, changed policy/source/status/frame counts, duplicate inputs and mismatched destinations.
