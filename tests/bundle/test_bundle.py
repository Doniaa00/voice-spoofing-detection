"""ModelBundle format and verifying loader tests (Stage 12 prep), on dummy files in tmp_path only.

No dataset access and no PyTorch: the checkpoint and profile are a few dummy bytes, the policy is a
hand-made RiskPolicy.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

import src.bundle.bundle as bundle_module
from src.bundle.bundle import (
    COMPONENTS,
    MANIFEST_NAME,
    SCHEMA_VERSION,
    BundleManifest,
    build_bundle,
    load_bundle,
)
from src.risk.calibration import PlattCalibration
from src.risk.policy import RiskPolicy

BUNDLE_DIR = Path(__file__).resolve().parents[2] / "src" / "bundle"

COMMIT = "0123456789abcdef0123456789abcdef01234567"
LEDGER = "c9fc2e230c0883028459d0b2b8de4f6ee537676cd5a4e259e9d0f545c60943cc"
CREATED_AT = "2026-10-17T12:00:00Z"


def _policy(version: str = "policy-v1") -> RiskPolicy:
    return RiskPolicy(
        version=version,
        calibration=PlattCalibration(a=1.0, b=0.0, n_spoof=10, n_bonafide=12),
        threshold=0.5,
        half_width=0.1,
        target_deferral=0.10,
        n_spoof_fit=10,
        n_bonafide_fit=12,
        deferral_on_fit=0.0909090909090909,
    )


def _sources(root: Path) -> tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    checkpoint = root / "cnn.pt"
    profile = root / "profile.yaml"
    checkpoint.write_bytes(b"dummy checkpoint bytes \x00\x01\x02")
    profile.write_bytes(b"name: profile-v1\nsample_rate: 16000\n")
    return checkpoint, profile


def _build(directory: Path, sources: Path, **overrides) -> Path:
    checkpoint, profile = _sources(sources)
    kwargs = dict(
        checkpoint=checkpoint,
        profile=profile,
        policy_json=_policy().to_json(),
        bundle_version="bundle-v1",
        model_version="cnn-v1",
        profile_version="profile-v1",
        code_commit=COMMIT,
        protocol_version="1.0",
        f2_ledger_sha256=LEDGER,
        created_at=CREATED_AT,
    )
    kwargs.update(overrides)
    return build_bundle(directory, **kwargs)


@pytest.fixture
def bundle_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "bundle"
    _build(directory, tmp_path / "src")
    return directory


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _edit_manifest(directory: Path, mutate) -> None:
    path = directory / MANIFEST_NAME
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data), encoding="utf-8")


# 1. Round trip.
def test_build_then_load_round_trip(tmp_path: Path):
    # The loaded bundle must report exactly what was built: each component's hash is the SHA-256 of
    # its source bytes (copied unchanged), the versions are the inputs (the policy version comes from
    # the policy JSON), the policy equals the input object, and manifest_sha256 is the SHA-256 of the
    # manifest file's bytes, which is the value the F4 decision records.
    directory = tmp_path / "bundle"
    manifest_path = _build(directory, tmp_path / "src")
    assert manifest_path == directory / MANIFEST_NAME

    loaded = load_bundle(directory)
    m = loaded.manifest
    assert m.schema_version == SCHEMA_VERSION
    assert (m.bundle_version, m.created_at, m.code_commit, m.protocol_version, m.f2_ledger_sha256) == (
        "bundle-v1", CREATED_AT, COMMIT, "1.0", LEDGER,
    )
    assert tuple(m.components) == COMPONENTS
    assert m.components["checkpoint"].sha256 == _sha(tmp_path / "src" / "cnn.pt")
    assert m.components["profile"].sha256 == _sha(tmp_path / "src" / "profile.yaml")
    assert m.components["policy"].sha256 == hashlib.sha256(_policy().to_json().encode("utf-8")).hexdigest()
    assert [m.components[c].version for c in COMPONENTS] == ["cnn-v1", "profile-v1", "policy-v1"]
    assert loaded.policy == _policy()
    assert loaded.checkpoint_path == directory / "cnn.pt"
    assert loaded.profile_path == directory / "profile.yaml"
    assert loaded.checkpoint_path.read_bytes() == (tmp_path / "src" / "cnn.pt").read_bytes()
    assert loaded.manifest_sha256 == _sha(manifest_path)
    # Strict JSON round trip of the manifest itself.
    assert BundleManifest.from_json(m.to_json()) == m


# 2. Tampering with a component file.
@pytest.mark.parametrize("component, file", [
    ("checkpoint", "cnn.pt"), ("profile", "profile.yaml"), ("policy", "policy.json"),
])
def test_tampered_component_raises(bundle_dir: Path, component: str, file: str):
    # Flipping one bit of one byte changes the SHA-256 (no collision is known for SHA-256), so the
    # loader must refuse and name the part that failed. The policy flip is checked by hash before the
    # policy is parsed, so a tampered but still valid policy is caught too.
    path = bundle_dir / file
    data = bytearray(path.read_bytes())
    data[0] ^= 0x01
    path.write_bytes(bytes(data))
    with pytest.raises(ValueError, match=rf"{component}: SHA-256 mismatch for {file}"):
        load_bundle(bundle_dir)


# 3. Edited manifest.
def test_edited_manifest_sha256_raises(bundle_dir: Path):
    # A changed recorded hash no longer matches the (untouched) file.
    _edit_manifest(bundle_dir, lambda d: d["components"]["checkpoint"].update(sha256="0" * 64))
    with pytest.raises(ValueError, match="checkpoint: SHA-256 mismatch"):
        load_bundle(bundle_dir)


def test_edited_manifest_policy_version_raises(bundle_dir: Path):
    # The policy file still says "policy-v1"; the manifest now claims "policy-v2".
    _edit_manifest(bundle_dir, lambda d: d["components"]["policy"].update(version="policy-v2"))
    with pytest.raises(ValueError, match="policy: version mismatch"):
        load_bundle(bundle_dir)


def test_edited_manifest_changes_manifest_sha256(bundle_dir: Path):
    # A version the loader cannot check against its file (the model version) still changes the
    # manifest bytes, so it no longer matches the manifest_sha256 recorded in the F4 decision.
    before = load_bundle(bundle_dir).manifest_sha256
    _edit_manifest(bundle_dir, lambda d: d["components"]["checkpoint"].update(version="cnn-v2"))
    assert load_bundle(bundle_dir).manifest_sha256 != before


@pytest.mark.parametrize("mutate", [
    lambda d: d.update(schema_version=2),                          # wrong schema version
    lambda d: d.pop("code_commit"),                                # missing key
    lambda d: d.update(extra=1),                                   # unknown key
    lambda d: d["components"].pop("profile"),                      # missing component
    lambda d: d["components"].update(extra=d["components"]["profile"]),  # unknown component
    lambda d: d["components"]["policy"].update(size=1),            # unknown component key
    lambda d: d.update(code_commit="ABC"),                         # not 40 lowercase hex
    lambda d: d.update(created_at="2026-10-17 12:00:00"),          # not ISO 8601 UTC
    lambda d: d.update(protocol_version="v1"),                     # not like "1.0"
])
def test_invalid_manifest_raises(bundle_dir: Path, mutate):
    _edit_manifest(bundle_dir, mutate)
    with pytest.raises(ValueError, match="manifest"):
        load_bundle(bundle_dir)


# 4. Path safety.
@pytest.mark.parametrize("bad_name", ["../x", "/abs/x", "C:\\abs\\x", "sub/x", "sub\\x", "..", "."])
def test_unsafe_component_path_raises_and_reads_nothing(tmp_path: Path, bundle_dir: Path, monkeypatch, bad_name):
    # A file named "x" exists both outside the bundle and in a sub-folder, so a loader that joined
    # the path would find something to read. The plain-name check runs while the manifest is parsed,
    # before any component file is opened, so the hash function is never called.
    (tmp_path / "x").write_bytes(b"outside")
    (bundle_dir / "sub").mkdir()
    (bundle_dir / "sub" / "x").write_bytes(b"nested")
    _edit_manifest(bundle_dir, lambda d: d["components"]["checkpoint"].update(file=bad_name))
    hashed = []
    monkeypatch.setattr(bundle_module, "sha256_file", lambda p: hashed.append(p) or "0" * 64)
    with pytest.raises(ValueError, match="plain file name"):
        load_bundle(bundle_dir)
    assert hashed == []


# 5. Folder contents.
def test_extra_file_raises(bundle_dir: Path):
    # Only the manifest and the three parts may be present: anything else is unexplained content.
    (bundle_dir / "notes.txt").write_text("extra", encoding="utf-8")
    with pytest.raises(ValueError, match=r"extra \['notes.txt'\]"):
        load_bundle(bundle_dir)


def test_missing_file_raises(bundle_dir: Path):
    (bundle_dir / "profile.yaml").unlink()
    with pytest.raises(ValueError, match=r"missing \['profile.yaml'\]"):
        load_bundle(bundle_dir)


def test_missing_manifest_raises(bundle_dir: Path):
    (bundle_dir / MANIFEST_NAME).unlink()
    with pytest.raises(ValueError, match="manifest"):
        load_bundle(bundle_dir)


# 6. Policy version mismatch / invalid policy.
def test_invalid_policy_json_at_build_raises(tmp_path: Path):
    # At build the policy version is read from the policy itself, so it cannot mismatch; an invalid
    # policy must stop the build before anything is written.
    directory = tmp_path / "bundle"
    with pytest.raises(ValueError, match="policy: invalid policy JSON"):
        _build(directory, tmp_path / "src", policy_json='{"schema_version": 1}')
    assert not directory.exists()


def test_policy_version_mismatch_at_load_raises(bundle_dir: Path):
    # Replace policy.json by a valid policy with another version and update its hash, so only the
    # version check can catch it.
    other = _policy("policy-v2").to_json().encode("utf-8")
    (bundle_dir / "policy.json").write_bytes(other)
    sha = hashlib.sha256(other).hexdigest()
    _edit_manifest(bundle_dir, lambda d: d["components"]["policy"].update(sha256=sha))
    with pytest.raises(ValueError, match=r"policy: version mismatch \(manifest 'policy-v1', file 'policy-v2'\)"):
        load_bundle(bundle_dir)


def test_invalid_policy_at_load_raises(bundle_dir: Path):
    # Hash updated, so the parse step is what must fail (NaN threshold is rejected by RiskPolicy).
    bad = _policy().to_json().replace('"threshold": 0.5', '"threshold": NaN').encode("utf-8")
    (bundle_dir / "policy.json").write_bytes(bad)
    sha = hashlib.sha256(bad).hexdigest()
    _edit_manifest(bundle_dir, lambda d: d["components"]["policy"].update(sha256=sha))
    with pytest.raises(ValueError, match="policy: invalid policy file"):
        load_bundle(bundle_dir)


def test_policy_is_parsed_from_the_hashed_bytes(bundle_dir: Path, monkeypatch):
    # policy.json must be read once: the bytes that are hashed are the bytes that are parsed. Right
    # after that read, the file is swapped for a valid policy-v2; a loader that read the file again
    # to parse it would return (or reject) policy-v2. Reading once, it returns the verified policy-v1.
    policy_path = bundle_dir / "policy.json"
    other = _policy("policy-v2").to_json().encode("utf-8")
    real_read_bytes = Path.read_bytes
    reads = []

    def read_bytes(self):
        data = real_read_bytes(self)
        if self == policy_path:
            reads.append(self)
            real_write_bytes(self, other)
        return data

    real_write_bytes = Path.write_bytes
    hashed = []
    real_sha256_file = bundle_module.sha256_file
    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    monkeypatch.setattr(bundle_module, "sha256_file", lambda p: hashed.append(p) or real_sha256_file(p))

    loaded = load_bundle(bundle_dir)
    assert loaded.policy == _policy("policy-v1")
    assert reads == [policy_path]
    assert policy_path not in hashed


# 7. Immutability.
def test_build_into_non_empty_directory_raises(tmp_path: Path, bundle_dir: Path):
    # Bundles are never overwritten: the existing folder keeps exactly its bytes.
    before = {p.name: p.read_bytes() for p in bundle_dir.iterdir()}
    with pytest.raises(ValueError, match="not empty"):
        _build(bundle_dir, tmp_path / "src2", bundle_version="bundle-v2")
    assert {p.name: p.read_bytes() for p in bundle_dir.iterdir()} == before


@pytest.mark.parametrize("pre_create", [False, True])
def test_failed_build_removes_what_it_wrote(tmp_path: Path, monkeypatch, pre_create: bool):
    # The second copy (the profile) fails after the checkpoint was written. No half-built bundle may
    # remain: a folder build_bundle created is removed, a pre-existing empty folder is empty again,
    # and the original error is re-raised.
    directory = tmp_path / "bundle"
    if pre_create:
        directory.mkdir()
    real_copyfile = bundle_module.shutil.copyfile
    calls = []

    def copyfile(src, dst):
        calls.append(dst)
        if len(calls) == 2:
            Path(dst).write_bytes(b"half")  # a partly written file must be removed too
            raise OSError("disk full")
        return real_copyfile(src, dst)

    monkeypatch.setattr(bundle_module.shutil, "copyfile", copyfile)
    with pytest.raises(OSError, match="disk full"):
        _build(directory, tmp_path / "src")
    assert len(calls) == 2
    if pre_create:
        assert directory.is_dir()
        assert list(directory.iterdir()) == []
    else:
        assert not directory.exists()


def test_build_into_empty_directory_is_allowed(tmp_path: Path):
    directory = tmp_path / "bundle"
    directory.mkdir()
    _build(directory, tmp_path / "src")
    assert load_bundle(directory).manifest.bundle_version == "bundle-v1"


# 8. Determinism.
def test_build_is_deterministic(tmp_path: Path):
    # Same inputs and created_at -> same manifest bytes (sorted keys, fixed layout), so the manifest
    # SHA-256 recorded in F4 can be reproduced.
    a = _build(tmp_path / "a", tmp_path / "src")
    b = _build(tmp_path / "b", tmp_path / "src")
    assert a.read_bytes() == b.read_bytes()


# 9. Layering.
def _imported_modules(path: Path) -> list[str]:
    """Absolute module names imported by a source file (relative imports resolved inside src.bundle)."""
    names = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # from .x / ..x: resolve against the src.bundle package
                base = ["src", "bundle"][: max(0, 2 - (node.level - 1))]
                names.append(".".join(base + ([node.module] if node.module else [])))
            else:
                names.append(node.module or "")
    return names


def test_bundle_does_not_import_research_code():
    # The API loads bundles but has no Evaluation or Tuning service (SDD Fig. 1).
    files = sorted(BUNDLE_DIR.glob("*.py"))
    assert files, f"no source files found in {BUNDLE_DIR}"
    offending = {
        f.name: name
        for f in files
        for name in _imported_modules(f)
        for research in ("evaluation", "tuning")
        if name == f"src.{research}" or name.startswith(f"src.{research}.") or name.startswith(research)
    }
    assert offending == {}
