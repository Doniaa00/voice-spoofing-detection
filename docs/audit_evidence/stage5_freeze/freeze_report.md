# Stage 5 dataset freeze (F2)

Protocol: 1.0
Code commit: `df1d6acab9df707b4702e038c45d5d22b38b8e66`
Git dirty during run: `false`

## Inputs

- FoR revision: `ff8c82c79e7bbefef811941bac9775c9328e9055`
- FoR assignment SHA-256: `853d947499e76c4cc9da5b69df384588f0023c21ed93f6a2dec1940f8988aa20`
- External archive SHA-256: `8cb258530daa2bb678121f3b276313a4d56fc638280bfd276a610dd8f732bdcf`
- Audio decoded or inspected: **no**

## Frozen manifests

- `for2sec_frozen_manifest.csv`: 17721 rows; SHA-256 `badfe948fb7b833357783dd18be00f6bb36253cf8699dc4c4beb4df2b07706f8`
- `deepvoice_frozen_manifest.csv`: 64 rows; SHA-256 `7c7a3e52ef254841f53bc08018bd3f9fe7ad83d6cd84531832513c616695355f`
- `manifest_hashes.csv`: SHA-256 `c9fc2e230c0883028459d0b2b8de4f6ee537676cd5a4e259e9d0f545c60943cc`

## Validation

### for2sec
- row_count_matches: True
- paths_unique: True
- path_sets_match: True
- labels_match_inventory: True
- hashes_valid: True
- counts_match_stage4: True
- groups_do_not_cross_splits: True

### deepvoice
- row_count_matches: True
- paths_unique: True
- labels_match_audit: True
- headers_valid: True
- metadata_numeric_positive: True
- speaker_metadata_valid: True
- hashes_valid: True

All validation checks pass: **true**.

F2 becomes immutable only after human review and merge. Stage 6 has not started.
