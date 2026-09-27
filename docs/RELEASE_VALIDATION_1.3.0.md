# Phase 2 Release Validation — 1.3.0

## Scope

This release fixes the field failure `LRC_GENERATION_FAILED: timestamps are not globally chronological` and the related blank-marker output-stage rejection.

## Automated validation

- Python compilation: required
- Unit tests: required
- Same-chunk chronology repair: covered
- Repeated merge purity: covered
- Blank-marker finalization: covered
- LRC acceptance of end-span crossing with valid onset: covered

## Field recovery

Use `python main.py --failed --debug` after installing/replacing the project. Existing successful outputs should remain untouched.
