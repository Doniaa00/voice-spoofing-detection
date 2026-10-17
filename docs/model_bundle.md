# Model bundle

The ModelBundle is the one frozen artifact the deployed system and the external run use: the CNN
checkpoint, the preprocessing profile and the risk policy, fitted on FoR only and frozen together in
F4 before the external run (D2, AGENTS.md hard rule 2, Protocol v1.0 §6 and §12). It is the
**C→D** hand-over (the bundle Stage 13 scores with) and the **C→E** hand-over (the bundle the API
loads, its hash verified, refusal to start otherwise; Protocol v1.0 §11, D26). It lives in
`src/bundle/`, the Model Registry of the shared core (SDD Fig. 1).

This step defines the format and the verifying loader. It is tested on dummy files only; no dataset
is read and no PyTorch is needed.

## Format

One folder holding exactly four files:

| File | Content |
|---|---|
| checkpoint (its own name, e.g. `cnn.pt`) | CNN weights, copied unchanged |
| profile (its own name) | Preprocessing profile (F3), copied unchanged |
| `policy.json` | `RiskPolicy.to_json()` ([risk_policy.md](risk_policy.md), Step R2) |
| `bundle_manifest.json` | The manifest below |

`src/bundle/bundle.py` (core) holds:
- `MANIFEST_NAME = "bundle_manifest.json"`, `SCHEMA_VERSION = 1`,
  `COMPONENTS = ("checkpoint", "profile", "policy")`.
- `Component(file, sha256, version)`, a frozen dataclass: plain file name, 64 lowercase hex, non-empty
  version.
- `BundleManifest(schema_version, bundle_version, created_at, code_commit, protocol_version,
  f2_ledger_sha256, components)`, a frozen dataclass. `created_at` is ISO 8601 UTC
  (`YYYY-MM-DDTHH:MM:SSZ`, optional fraction), `code_commit` 40 lowercase hex, `protocol_version`
  like `1.0`, `f2_ledger_sha256` the F2 hash ledger (D28), `components` exactly the three names
  with distinct files. `to_json` / `from_json` are strict: sorted keys, and unknown or missing keys
  at any level raise `ValueError`.
- `build_bundle(directory, *, checkpoint, profile, policy_json, bundle_version, model_version,
  profile_version, code_commit, protocol_version, f2_ledger_sha256, created_at) -> Path`
  (the manifest path).
- `LoadedBundle(directory, manifest, checkpoint_path, profile_path, policy, manifest_sha256)` and
  `load_bundle(directory) -> LoadedBundle`.

## Method

Build:
1. Refuse if the folder exists and is not empty.
2. Parse `policy_json` with `RiskPolicy.from_json`; the policy version is the policy's own `version`.
3. Hash the checkpoint and profile sources (streamed, 1 MiB chunks) and build the manifest object, so
   every field is checked before anything is written.
4. Copy the checkpoint and profile, re-hash the copies, write `policy.json`, write the manifest last.
5. If any write step fails, remove every file this call wrote (and the folder, if this call created
   it), then re-raise the original error: no half-built bundle is left behind.

Load (read-only; nothing is returned until every check passes; any failure is a `ValueError` naming
the check and the component):
1. The manifest is read once and parses strictly (including plain-name checks on every component
   file); `manifest_sha256` is computed from those same bytes.
2. The folder holds exactly the manifest and the three component files; extra or missing → error.
3. Each component is a regular file (no symlink) and its SHA-256 matches the manifest.
   `policy.json` is read once: the bytes that are hashed are the bytes that are parsed.
4. Those policy bytes load as a `RiskPolicy` and its version equals `components["policy"].version`.
5. `manifest_sha256` = SHA-256 of the manifest's bytes.

## Why (team reasoning)
- **(a) Verify before use.** NFR-09 and threat model §10 (tampering: model, profile or thresholds
  replaced) require a refusal at load, and §10 recommends checking the checkpoint hash. Hashing every
  part, and checking the policy version against the file, means a replaced or altered part stops the
  API or the external run instead of producing numbers from an unknown model.
- **(b) Path safety.** The manifest is data. If it could name `../x`, an absolute path or `sub/x`,
  an edited manifest could make the loader hash or load a file outside the bundle. Plain names are
  checked while the manifest is parsed, before any component file is opened.
- **(c) Immutability.** A frozen bundle is never changed (Protocol v1.0 §12): `build_bundle` never
  writes into a non-empty folder and `load_bundle` only reads. A new bundle is a new folder and a new
  version.
- **(d) Provenance.** Every run is dataset version + config + code version → results (AGENTS.md).
  The manifest records the code commit, the protocol version and the F2 ledger hash (D28), so a
  bundle names the data, protocol and code it was built from.
- **(e) External anchor for the manifest hash.** A file cannot contain its own SHA-256. The loader
  returns `manifest_sha256` and the F4 freeze decision records it, so an edited manifest, including
  fields the loader cannot check against a file (such as the model version), is detected by comparing
  with the decision. Same inputs and `created_at` give byte-identical manifests, so the hash can be
  reproduced.

- **(f) Single read.** A file read once to hash and again to parse could be swapped in between;
  reading `policy.json` and the manifest once closes that gap for the parts the loader parses.

**Limitations:**
- The profile version is recorded but not checked against the profile file; that check needs the F3
  profile format and is added in Stage 12.
- **Check-then-use.** `load_bundle` verifies the checkpoint and profile by path and returns those
  paths; a file replaced after the check is not detected here. Stage 12 and the API (Stage 17) must
  load the checkpoint from the verified bytes or re-verify its hash at load time.
- **Unsafe deserialization.** A PyTorch checkpoint saved with pickle can execute code when loaded.
  Stage 8 saves checkpoints in a non-executable form (safetensors, or `torch.save` of a `state_dict`
  loaded with `torch.load(..., weights_only=True)`), and Stage 12/17 load them that way.

## Tests (`tests/bundle/test_bundle.py`)
Each case has its reasoning as a comment.

| Point | Test |
|---|---|
| Round trip | `test_build_then_load_round_trip` (hashes, versions, policy equal the inputs; `manifest_sha256` = SHA-256 of the file) |
| (a) tampering | `test_tampered_component_raises` (one bit flipped in checkpoint, profile or policy → error naming it) |
| (a), (e) edited manifest | `test_edited_manifest_sha256_raises`, `test_edited_manifest_policy_version_raises`, `test_edited_manifest_changes_manifest_sha256` |
| Strict manifest | `test_invalid_manifest_raises` (schema version, missing / unknown keys and components, commit, date, protocol format) |
| (b) path safety | `test_unsafe_component_path_raises_and_reads_nothing` (`../x`, absolute POSIX and Windows paths, `sub/x`, `sub\x`, `..`, `.`; the hash function is never called) |
| (a) folder contents | `test_extra_file_raises`, `test_missing_file_raises`, `test_missing_manifest_raises` |
| (a) policy | `test_invalid_policy_json_at_build_raises`, `test_policy_version_mismatch_at_load_raises`, `test_invalid_policy_at_load_raises` |
| (f) single read | `test_policy_is_parsed_from_the_hashed_bytes` (policy.json swapped right after its one read; the verified policy is returned, the file is read once) |
| (c) immutability | `test_build_into_non_empty_directory_raises` (folder bytes unchanged), `test_build_into_empty_directory_is_allowed`, `test_failed_build_removes_what_it_wrote` (second copy fails → error re-raised; created folder gone, pre-existing folder empty) |
| (e) determinism | `test_build_is_deterministic` |
| Layering | `test_bundle_does_not_import_research_code` (no import of `src.evaluation` or `src.tuning`) |
