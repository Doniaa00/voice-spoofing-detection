"""ModelBundle format and verifying loader (Protocol v1.0 §6 and §11; D2; AGENTS.md hard rule 2).

A ModelBundle is one folder: the CNN checkpoint, the preprocessing profile, the risk policy
(policy.json) and bundle_manifest.json, which records the SHA-256 and version of each part, the code
commit, the protocol version and the F2 hash ledger (D28). It is frozen in F4 (Stage 12) and is what
the API loads (SDD Model Registry, C->E interface).

- Verification before use (NFR-09; threat model §10, tampering): load_bundle checks the manifest,
  the folder contents, every SHA-256 and the policy version before it returns anything, so a
  replaced or altered part fails loudly instead of running.
- Path safety: component files are plain names inside the bundle folder; a manifest naming
  "../x", an absolute path or "sub/x" is rejected before any component file is opened.
- Immutability: build_bundle never writes into a non-empty folder, and load_bundle only reads.
- The manifest cannot hash itself, so load_bundle returns its SHA-256 (manifest_sha256) and the F4
  freeze decision records it; that external anchor also covers fields load_bundle cannot check
  (e.g. the model version).

Limitation: the profile version is recorded but not checked against the profile file; that check
needs the F3 profile format and is added in Stage 12.

Part of the shared core (SDD Fig. 1): the API loads bundles, so this module must not import
src.evaluation or src.tuning (research code).
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import MappingProxyType
from typing import Mapping

from src.risk.policy import RiskPolicy

MANIFEST_NAME = "bundle_manifest.json"
SCHEMA_VERSION = 1
COMPONENTS = ("checkpoint", "profile", "policy")
POLICY_FILE = "policy.json"

_CHUNK = 1 << 20  # 1 MiB: checkpoints can be large, so hashes are streamed
_HEX64 = re.compile(r"[0-9a-f]{64}")
_HEX40 = re.compile(r"[0-9a-f]{40}")
_PROTOCOL = re.compile(r"[0-9]+\.[0-9]+")
_UTC = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z")

_COMPONENT_KEYS = {"file", "sha256", "version"}
_MANIFEST_KEYS = {
    "schema_version", "bundle_version", "created_at", "code_commit", "protocol_version",
    "f2_ledger_sha256", "components",
}


def _require_nonempty_str(name: str, value) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string, got {value!r}")


def _require_match(name: str, pattern: re.Pattern, value, what: str) -> None:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(f"{name} must be {what}, got {value!r}")


def _require_plain_name(name: str, value) -> None:
    """A file name with no directory part: no separators, not '.', '..', absolute or a drive."""
    _require_nonempty_str(name, value)
    if (
        value in {".", ".."}
        or PurePosixPath(value).name != value
        or PureWindowsPath(value).name != value
        or PurePosixPath(value).is_absolute()
        or PureWindowsPath(value).is_absolute()
    ):
        raise ValueError(f"{name} must be a plain file name inside the bundle, got {value!r}")


def _check_keys(where: str, data: dict, expected: set[str]) -> None:
    missing = sorted(expected - data.keys())
    unknown = sorted(data.keys() - expected)
    if missing or unknown:
        raise ValueError(f"{where}: missing keys {missing}, unknown keys {unknown}")


def sha256_file(path: Path) -> str:
    """SHA-256 of a file's bytes, read in 1 MiB chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class Component:
    """One bundle part: plain file name, SHA-256 of its bytes, and its version."""

    file: str
    sha256: str
    version: str

    def __post_init__(self) -> None:
        _require_plain_name("file", self.file)
        if self.file == MANIFEST_NAME:
            raise ValueError(f"file must not be the manifest name {MANIFEST_NAME!r}")
        _require_match("sha256", _HEX64, self.sha256, "64 lowercase hex characters")
        _require_nonempty_str("version", self.version)


@dataclass(frozen=True)
class BundleManifest:
    """Contents of bundle_manifest.json. components maps exactly COMPONENTS to Component."""

    schema_version: int
    bundle_version: str
    created_at: str
    code_commit: str
    protocol_version: str
    f2_ledger_sha256: str
    components: Mapping[str, Component]

    def __post_init__(self) -> None:
        if isinstance(self.schema_version, bool) or self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {SCHEMA_VERSION}, got {self.schema_version!r}")
        _require_nonempty_str("bundle_version", self.bundle_version)
        _require_match("created_at", _UTC, self.created_at, "ISO 8601 UTC (YYYY-MM-DDTHH:MM:SSZ)")
        try:
            datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(f"created_at is not a valid date and time, got {self.created_at!r}") from None
        _require_match("code_commit", _HEX40, self.code_commit, "40 lowercase hex characters")
        _require_match("protocol_version", _PROTOCOL, self.protocol_version, "like '1.0'")
        _require_match("f2_ledger_sha256", _HEX64, self.f2_ledger_sha256, "64 lowercase hex characters")
        if not isinstance(self.components, Mapping) or set(self.components) != set(COMPONENTS):
            keys = sorted(self.components) if isinstance(self.components, Mapping) else self.components
            raise ValueError(f"components must have exactly the keys {list(COMPONENTS)}, got {keys!r}")
        for name in COMPONENTS:
            if not isinstance(self.components[name], Component):
                raise ValueError(f"components[{name!r}] must be a Component")
        files = [self.components[name].file for name in COMPONENTS]
        if len(set(files)) != len(files):
            raise ValueError(f"component files must be distinct, got {files}")
        # Read-only copy in a fixed order, so the frozen manifest cannot be changed through it.
        object.__setattr__(
            self, "components", MappingProxyType({name: self.components[name] for name in COMPONENTS})
        )

    def to_json(self) -> str:
        """Sorted keys, 2-space indent, trailing newline: same manifest -> same bytes."""
        payload = {
            "schema_version": self.schema_version,
            "bundle_version": self.bundle_version,
            "created_at": self.created_at,
            "code_commit": self.code_commit,
            "protocol_version": self.protocol_version,
            "f2_ledger_sha256": self.f2_ledger_sha256,
            "components": {
                name: {"file": c.file, "sha256": c.sha256, "version": c.version}
                for name, c in self.components.items()
            },
        }
        return json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"

    @classmethod
    def from_json(cls, text: str) -> BundleManifest:
        """Load a manifest written by to_json; ValueError on any schema or value problem."""
        data = json.loads(text)  # json.JSONDecodeError is a ValueError
        if not isinstance(data, dict):
            raise ValueError(f"manifest JSON must be an object, got {type(data).__name__}")
        _check_keys("manifest JSON", data, _MANIFEST_KEYS)
        components = data["components"]
        if not isinstance(components, dict):
            raise ValueError(f"components must be an object, got {type(components).__name__}")
        _check_keys("manifest components", components, set(COMPONENTS))
        parsed = {}
        for name in COMPONENTS:
            entry = components[name]
            if not isinstance(entry, dict):
                raise ValueError(f"components.{name} must be an object, got {type(entry).__name__}")
            _check_keys(f"manifest components.{name}", entry, _COMPONENT_KEYS)
            try:
                parsed[name] = Component(**entry)
            except ValueError as e:
                raise ValueError(f"components.{name}: {e}") from None
        return cls(**{**data, "components": parsed})


@dataclass(frozen=True)
class LoadedBundle:
    """A bundle that passed every check in load_bundle."""

    directory: Path
    manifest: BundleManifest
    checkpoint_path: Path
    profile_path: Path
    policy: RiskPolicy
    manifest_sha256: str


def build_bundle(
    directory,
    *,
    checkpoint,
    profile,
    policy_json: str,
    bundle_version: str,
    model_version: str,
    profile_version: str,
    code_commit: str,
    protocol_version: str,
    f2_ledger_sha256: str,
    created_at: str,
) -> Path:
    """Write a new bundle folder and return the manifest path.

    checkpoint and profile are copied under their own file names; policy_json is written as
    policy.json and must load as a RiskPolicy (its version is the policy version). Every input is
    checked before anything is written; the manifest is written last.
    """
    directory = Path(directory)
    if directory.exists() and (not directory.is_dir() or any(directory.iterdir())):
        raise ValueError(f"bundle directory {directory} exists and is not empty; bundles are never overwritten")
    if not isinstance(policy_json, str):
        raise ValueError(f"policy_json must be a string, got {type(policy_json).__name__}")
    try:
        policy = RiskPolicy.from_json(policy_json)
    except (ValueError, TypeError) as e:
        raise ValueError(f"policy: invalid policy JSON: {e}") from None
    policy_bytes = policy_json.encode("utf-8")

    sources = {"checkpoint": Path(checkpoint), "profile": Path(profile)}
    for name, src in sources.items():
        if not src.is_file():
            raise ValueError(f"{name}: source {src} is not a file")
    versions = {"checkpoint": model_version, "profile": profile_version, "policy": policy.version}
    components = {
        name: Component(file=src.name, sha256=sha256_file(src), version=versions[name])
        for name, src in sources.items()
    }
    components["policy"] = Component(
        file=POLICY_FILE, sha256=hashlib.sha256(policy_bytes).hexdigest(), version=policy.version
    )
    manifest = BundleManifest(
        schema_version=SCHEMA_VERSION,
        bundle_version=bundle_version,
        created_at=created_at,
        code_commit=code_commit,
        protocol_version=protocol_version,
        f2_ledger_sha256=f2_ledger_sha256,
        components=components,
    )

    directory.mkdir(parents=True, exist_ok=True)
    for name, src in sources.items():
        dest = directory / components[name].file
        shutil.copyfile(src, dest)
        if sha256_file(dest) != components[name].sha256:
            raise ValueError(f"{name}: copied file {dest} does not match its source (source changed?)")
    (directory / POLICY_FILE).write_bytes(policy_bytes)
    manifest_path = directory / MANIFEST_NAME
    manifest_path.write_bytes(manifest.to_json().encode("utf-8"))
    return manifest_path


def load_bundle(directory) -> LoadedBundle:
    """Verify a bundle folder and return it; read-only. ValueError naming the first failed check."""
    directory = Path(directory)
    if not directory.is_dir():
        raise ValueError(f"bundle directory {directory} does not exist or is not a directory")
    manifest_path = directory / MANIFEST_NAME
    if not manifest_path.is_file():
        raise ValueError(f"manifest {MANIFEST_NAME} is missing in {directory}")
    manifest_bytes = manifest_path.read_bytes()
    try:
        manifest = BundleManifest.from_json(manifest_bytes.decode("utf-8"))
    except (ValueError, TypeError) as e:  # UnicodeDecodeError is a ValueError
        raise ValueError(f"manifest {MANIFEST_NAME}: {e}") from None

    # Plain names were checked by Component, so every path below stays inside the directory.
    expected = {MANIFEST_NAME} | {c.file for c in manifest.components.values()}
    present = {p.name for p in directory.iterdir()}
    if present != expected:
        raise ValueError(
            f"bundle contents differ from the manifest: missing {sorted(expected - present)}, "
            f"extra {sorted(present - expected)}"
        )
    for name, component in manifest.components.items():
        path = directory / component.file
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"{name}: {component.file} is not a regular file")
        actual = sha256_file(path)
        if actual != component.sha256:
            raise ValueError(
                f"{name}: SHA-256 mismatch for {component.file} (manifest {component.sha256}, file {actual})"
            )

    policy_component = manifest.components["policy"]
    try:
        policy = RiskPolicy.from_json((directory / policy_component.file).read_bytes().decode("utf-8"))
    except (ValueError, TypeError) as e:
        raise ValueError(f"policy: invalid policy file {policy_component.file}: {e}") from None
    if policy.version != policy_component.version:
        raise ValueError(
            f"policy: version mismatch (manifest {policy_component.version!r}, file {policy.version!r})"
        )

    return LoadedBundle(
        directory=directory,
        manifest=manifest,
        checkpoint_path=directory / manifest.components["checkpoint"].file,
        profile_path=directory / manifest.components["profile"].file,
        policy=policy,
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
    )
