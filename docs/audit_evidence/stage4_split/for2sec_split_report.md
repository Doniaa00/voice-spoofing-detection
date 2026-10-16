# Stage 4 FoR leakage-aware split report

- Dataset revision: `ff8c82c79e7bbefef811941bac9775c9328e9055`
- Protocol: v1.0
- Seed: 2026
- Code commit: `10a5e6809bb55484908cbcce547a75c14d33a908` (dirty: False)
- Group column: `neardup_group_095`
- All automated checks pass: **True**

## Split sizes

| Split | Count | Fraction | Target |
|---|---:|---:|---:|
| train | 12404 | 0.7000 | 0.7000 |
| val-A | 1330 | 0.0751 | 0.0750 |
| val-B | 1329 | 0.0750 | 0.0750 |
| test | 2658 | 0.1500 | 0.1500 |

## Checks

- row_count_matches_source: True
- paths_unique: True
- path_set_matches_source: True
- split_values_valid: True
- groups_do_not_cross_splits: True
- subgroup_proportions_within_1pp: True
- class_proportions_within_1pp: True
- all_pass: True

Maximum subgroup deviation: 0.034537 percentage points.
Maximum class deviation: 0.034537 percentage points.

## Candidate evidence and determinism

- Candidate file: `for2sec_split_assignments.csv` (kept out of Git)
- Row count: 17721
- SHA-256 before rerun: `853d947499e76c4cc9da5b69df384588f0023c21ed93f6a2dec1940f8988aa20`
- SHA-256 after rerun: `853d947499e76c4cc9da5b69df384588f0023c21ed93f6a2dec1940f8988aa20`
- Determinism comparison: **identical SHA-256 and row count**
- Drive destination: `MyDrive/voice-spoofing-detection/processed/metadata/stage4/for2sec_split_assignments.csv`
- Drive upload confirmed: **True** (2026-10-16)

## Per-split × class × subgroup counts

| Split | Class | Subgroup | Count |
|---|---|---|---:|
| train | REAL | REAL | 6160 |
| train | FAKE | FAKE_mp3 | 5314 |
| train | FAKE | FAKE_other | 930 |
| val-A | REAL | REAL | 660 |
| val-A | FAKE | FAKE_mp3 | 570 |
| val-A | FAKE | FAKE_other | 100 |
| val-B | REAL | REAL | 660 |
| val-B | FAKE | FAKE_mp3 | 569 |
| val-B | FAKE | FAKE_other | 100 |
| test | REAL | REAL | 1320 |
| test | FAKE | FAKE_mp3 | 1139 |
| test | FAKE | FAKE_other | 199 |

## Real test output

Python 3.13.14 used the existing pinned `.venv` site-packages. The `.venv` launcher itself was
blocked by Windows Application Control, so pytest was invoked through the Python 3.13 launcher.

Focused: `tests/splitting/test_for2sec.py -q`

```text
..................                                                       [100%]
18 passed in 11.14s
```

Complete: `pytest -q`

```text
.................................                                        [100%]
33 passed in 19.83s
```

The group-leakage failure is exercised by
`tests/splitting/test_for2sec.py::test_check_split_detects_cross_split_group`. It assigns two
members of one group to different splits and asserts that `groups_do_not_cross_splits` and
`all_pass` are both false.

This is a Stage 4 assignment report, not the Stage 5 dataset freeze (F2).
