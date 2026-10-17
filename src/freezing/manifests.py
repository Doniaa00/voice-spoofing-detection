"""Stage 5: freeze the F2 dataset manifests from audited metadata only.

The official run joins the approved Stage 4 FoR assignments to the Stage 1
inventories. It reads CSV metadata and computes hashes of those CSV files; it
never opens, decodes or otherwise inspects audio.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

import pandas as pd
import yaml


FROZEN_FOR_REVISION = "ff8c82c79e7bbefef811941bac9775c9328e9055"
FROZEN_DEEPVOICE_ARCHIVE_SHA256 = (
    "8cb258530daa2bb678121f3b276313a4d56fc638280bfd276a610dd8f732bdcf"
)
FROZEN_ASSIGNMENTS_SHA256 = (
    "853d947499e76c4cc9da5b69df384588f0023c21ed93f6a2dec1940f8988aa20"
)
FOR_COLUMNS = ("path", "label", "subgroup", "group", "split", "hash")
DEEPVOICE_COLUMNS = (
    "path", "label", "source_speaker", "target_speaker",
    "sample_rate", "channels", "duration_s", "hash",
)
HASH_RE = re.compile(r"[0-9a-f]{64}")


class FreezeError(ValueError):
    """Raised when an input cannot be used for the F2 freeze."""


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    """Return the SHA-256 of a metadata or generated manifest file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def code_version(repo_root: Path | None = None) -> dict[str, Any]:
    """Return HEAD and refuse an official run from a dirty worktree."""
    root = repo_root or Path(__file__).resolve().parents[2]
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=normal"],
            cwd=root, check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise FreezeError(f"Cannot determine Git code version: {exc}") from exc
    if status:
        raise FreezeError("Official Stage 5 freeze requires a clean Git worktree")
    return {"git_commit": commit, "git_dirty": False}


def load_config(path: Path) -> dict[str, Any]:
    """Read and validate the frozen Stage 5 configuration."""
    try:
        cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise FreezeError(f"Cannot read freeze config {path}: {exc}") from exc
    if not isinstance(cfg, dict):
        raise FreezeError("Freeze config must be a YAML mapping")
    required = {"freeze_id", "protocol_version", "for2sec", "deepvoice", "outputs"}
    missing = sorted(required - set(cfg))
    if missing:
        raise FreezeError(f"Freeze config is missing sections: {missing}")
    if cfg["freeze_id"] != "F2" or str(cfg["protocol_version"]) != "1.0":
        raise FreezeError("Stage 5 must create Protocol v1.0 freeze F2")
    if cfg["for2sec"].get("revision") != FROZEN_FOR_REVISION:
        raise FreezeError("FoR revision differs from the D21 pin")
    if cfg["for2sec"].get("assignments_sha256") != FROZEN_ASSIGNMENTS_SHA256:
        raise FreezeError("FoR assignments differ from the approved Stage 4 artifact")
    if cfg["deepvoice"].get("archive_sha256") != FROZEN_DEEPVOICE_ARCHIVE_SHA256:
        raise FreezeError("External archive hash differs from the D21 pin")
    for section, fields in {
        "for2sec": ("inventory_sha256", "assignments_sha256"),
        "deepvoice": ("inventory_sha256", "archive_sha256"),
    }.items():
        for field in fields:
            if not HASH_RE.fullmatch(str(cfg[section].get(field, ""))):
                raise FreezeError(f"{section}.{field} must be a lowercase SHA-256")
    names = list(cfg["outputs"].values())
    if len(names) != 3 or len(set(names)) != 3:
        raise FreezeError("Freeze output names must contain three unique files")
    for name in names:
        if Path(str(name)).name != str(name) or not str(name).endswith(".csv"):
            raise FreezeError(f"Freeze output must be a plain CSV filename: {name!r}")
    return cfg


def safe_relative_path(value: object) -> str:
    """Return a canonical POSIX relative path, rejecting unsafe spellings."""
    raw = str(value).strip()
    if not raw or raw.startswith(("/", "\\")) or PureWindowsPath(raw).drive:
        raise FreezeError(f"Manifest path must be relative: {raw!r}")
    canonical = raw.replace("\\", "/")
    path = PurePosixPath(canonical)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise FreezeError(f"Manifest path is unsafe: {raw!r}")
    return path.as_posix()


def _read_metadata_csv(path: Path, expected_sha256: str, name: str) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() != ".csv" or not path.is_file():
        raise FreezeError(f"{name} must be an existing CSV file")
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise FreezeError(
            f"{name} SHA-256 mismatch: expected {expected_sha256}, got {actual}"
        )
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    except (OSError, pd.errors.ParserError, UnicodeError) as exc:
        raise FreezeError(f"Cannot read {name}: {exc}") from exc


def _require_columns(frame: pd.DataFrame, required: set[str], name: str) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise FreezeError(f"{name} is missing columns: {missing}")


def _validate_hashes(values: pd.Series, name: str) -> pd.Series:
    normalized = values.astype(str).str.strip().str.lower()
    bad = normalized.loc[~normalized.map(lambda value: bool(HASH_RE.fullmatch(value)))]
    if not bad.empty:
        raise FreezeError(f"{name} contains invalid SHA-256 values")
    return normalized


def _validate_paths(values: pd.Series, name: str) -> pd.Series:
    paths = values.map(safe_relative_path)
    if paths.duplicated().any():
        raise FreezeError(f"{name} contains duplicate paths")
    return paths


def _counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    return {str(key): int(value) for key, value in frame[column].value_counts().items()}


def build_for2sec_manifest(
    inventory: pd.DataFrame, assignments: pd.DataFrame, cfg: dict[str, Any]
) -> tuple[pd.DataFrame, dict[str, bool]]:
    """Join audited FoR byte hashes to the approved Stage 4 assignments."""
    _require_columns(inventory, {"rel_path", "label", "sha256_bytes"}, "FoR inventory")
    _require_columns(
        assignments, {"path", "label", "subgroup", "group", "split"},
        "Stage 4 assignments",
    )
    expected_rows = int(cfg["expected_rows"])
    if len(inventory) != expected_rows or len(assignments) != expected_rows:
        raise FreezeError(
            f"FoR row count mismatch: inventory={len(inventory)}, "
            f"assignments={len(assignments)}, expected={expected_rows}"
        )

    inv = inventory[["rel_path", "label", "sha256_bytes"]].copy()
    inv["path"] = _validate_paths(inv.pop("rel_path"), "FoR inventory")
    inv["hash"] = _validate_hashes(inv.pop("sha256_bytes"), "FoR inventory")
    assignment = assignments[["path", "label", "subgroup", "group", "split"]].copy()
    assignment["path"] = _validate_paths(assignment["path"], "Stage 4 assignments")
    if set(inv["path"]) != set(assignment["path"]):
        raise FreezeError("FoR inventory and Stage 4 assignment path sets differ")

    merged = assignment.merge(
        inv, on="path", how="inner", validate="one_to_one", suffixes=("", "_inventory")
    )
    if not merged["label"].eq(merged["label_inventory"]).all():
        raise FreezeError("FoR labels differ between inventory and assignments")
    merged = merged.drop(columns="label_inventory")

    if _counts(merged, "label") != cfg["expected_labels"]:
        raise FreezeError("FoR label counts differ from the frozen expectation")
    if _counts(merged, "subgroup") != cfg["expected_subgroups"]:
        raise FreezeError("FoR subgroup counts differ from the frozen expectation")
    if _counts(merged, "split") != cfg["expected_splits"]:
        raise FreezeError("FoR split counts differ from the approved Stage 4 split")
    if not merged.groupby("group")["split"].nunique().le(1).all():
        raise FreezeError("A near-duplicate group crosses FoR splits")

    manifest = merged[list(FOR_COLUMNS)].sort_values("path", kind="stable").reset_index(drop=True)
    checks = {
        "row_count_matches": True,
        "paths_unique": True,
        "path_sets_match": True,
        "labels_match_inventory": True,
        "hashes_valid": True,
        "counts_match_stage4": True,
        "groups_do_not_cross_splits": True,
    }
    return manifest, checks


def build_deepvoice_manifest(
    inventory: pd.DataFrame, cfg: dict[str, Any]
) -> tuple[pd.DataFrame, dict[str, bool]]:
    """Create the D20 metadata-only external file manifest."""
    source_columns = {
        "rel_path", "label", "src_speaker", "tgt_speaker", "samplerate",
        "channels", "duration_s", "sha256_bytes", "header_ok",
    }
    _require_columns(inventory, source_columns, "External inventory")
    if len(inventory) != int(cfg["expected_rows"]):
        raise FreezeError("External inventory row count differs from the frozen expectation")

    work = inventory[list(source_columns)].copy()
    work["path"] = _validate_paths(work.pop("rel_path"), "External inventory")
    work["hash"] = _validate_hashes(work.pop("sha256_bytes"), "External inventory")
    header_ok = work.pop("header_ok").astype(str).str.strip().str.lower()
    if not header_ok.eq("true").all():
        raise FreezeError("External inventory contains a header failure")
    if _counts(work, "label") != cfg["expected_labels"]:
        raise FreezeError("External label counts differ from the frozen expectation")

    for column in ("samplerate", "channels", "duration_s"):
        numeric = pd.to_numeric(work[column], errors="coerce")
        if numeric.isna().any() or numeric.le(0).any():
            raise FreezeError(f"External inventory column {column!r} must be positive numeric")
    if work["src_speaker"].astype(str).str.strip().eq("").any():
        raise FreezeError("External inventory contains a missing source speaker")
    fake = work["label"].eq("FAKE")
    if work.loc[fake, "tgt_speaker"].astype(str).str.strip().eq("").any():
        raise FreezeError("External FAKE rows require a target speaker")

    manifest = work.rename(columns={
        "src_speaker": "source_speaker",
        "tgt_speaker": "target_speaker",
        "samplerate": "sample_rate",
    })
    manifest = manifest[list(DEEPVOICE_COLUMNS)].sort_values("path", kind="stable").reset_index(drop=True)
    checks = {
        "row_count_matches": True,
        "paths_unique": True,
        "labels_match_audit": True,
        "headers_valid": True,
        "metadata_numeric_positive": True,
        "speaker_metadata_valid": True,
        "hashes_valid": True,
    }
    return manifest, checks


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8")


def write_outputs(
    for_manifest: pd.DataFrame,
    deepvoice_manifest: pd.DataFrame,
    cfg: dict[str, Any],
    manifest_dir: Path,
    report_dir: Path,
    report: dict[str, Any],
) -> dict[str, Any]:
    """Write deterministic manifests, their hash ledger, and Stage 5 reports."""
    manifest_dir, report_dir = Path(manifest_dir), Path(report_dir)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    outputs = cfg["outputs"]
    frames = {
        outputs["for2sec"]: for_manifest,
        outputs["deepvoice"]: deepvoice_manifest,
    }
    manifest_records = []
    for filename, frame in frames.items():
        data = _csv_bytes(frame)
        target = manifest_dir / filename
        target.write_bytes(data)
        manifest_records.append({
            "manifest": filename,
            "rows": len(frame),
            "sha256": hashlib.sha256(data).hexdigest(),
        })

    ledger = pd.DataFrame(manifest_records, columns=["manifest", "rows", "sha256"])
    ledger_data = _csv_bytes(ledger)
    ledger_name = outputs["hashes"]
    (manifest_dir / ledger_name).write_bytes(ledger_data)
    report["manifests"] = {
        record["manifest"]: {"rows": record["rows"], "sha256": record["sha256"]}
        for record in manifest_records
    }
    report["hash_ledger"] = {
        "file": ledger_name,
        "rows": len(ledger),
        "sha256": hashlib.sha256(ledger_data).hexdigest(),
    }

    (report_dir / "freeze_report.json").write_bytes(
        (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )
    lines = [
        "# Stage 5 dataset freeze (F2)",
        "",
        f"Protocol: {report['protocol_version']}",
        f"Code commit: `{report['code_version']['git_commit']}`",
        f"Git dirty during run: `{str(report['code_version']['git_dirty']).lower()}`",
        "",
        "## Inputs",
        "",
        f"- FoR revision: `{report['sources']['for2sec_revision']}`",
        f"- FoR assignment SHA-256: `{report['sources']['assignments_sha256']}`",
        f"- External archive SHA-256: `{report['sources']['deepvoice_archive_sha256']}`",
        "- Audio decoded or inspected: **no**",
        "",
        "## Frozen manifests",
        "",
    ]
    for record in manifest_records:
        lines.append(
            f"- `{record['manifest']}`: {record['rows']} rows; SHA-256 `{record['sha256']}`"
        )
    lines += [
        f"- `{ledger_name}`: SHA-256 `{report['hash_ledger']['sha256']}`",
        "",
        "## Validation",
        "",
    ]
    for dataset, checks in report["checks"].items():
        lines.append(f"### {dataset}")
        lines.extend(f"- {name}: {value}" for name, value in checks.items())
        lines.append("")
    lines += [
        "All validation checks pass: **true**.",
        "",
        "F2 becomes immutable only after human review and merge. Stage 6 has not started.",
    ]
    (report_dir / "freeze_report.md").write_bytes(
        ("\n".join(lines) + "\n").encode("utf-8")
    )
    return report


def run(
    for_inventory_path: Path,
    assignments_path: Path,
    deepvoice_inventory_path: Path,
    config_path: Path,
    manifest_dir: Path,
    report_dir: Path,
) -> dict[str, Any]:
    """Perform the official metadata-only Stage 5 freeze."""
    version = code_version()  # Must happen before reading inputs or writing outputs.
    cfg = load_config(config_path)
    for_inventory = _read_metadata_csv(
        for_inventory_path, cfg["for2sec"]["inventory_sha256"], "FoR inventory"
    )
    assignments = _read_metadata_csv(
        assignments_path, cfg["for2sec"]["assignments_sha256"], "Stage 4 assignments"
    )
    deepvoice_inventory = _read_metadata_csv(
        deepvoice_inventory_path, cfg["deepvoice"]["inventory_sha256"], "External inventory"
    )
    for_manifest, for_checks = build_for2sec_manifest(
        for_inventory, assignments, cfg["for2sec"]
    )
    deepvoice_manifest, deepvoice_checks = build_deepvoice_manifest(
        deepvoice_inventory, cfg["deepvoice"]
    )
    report = {
        "freeze_id": cfg["freeze_id"],
        "protocol_version": str(cfg["protocol_version"]),
        "code_version": version,
        "sources": {
            "for2sec_revision": cfg["for2sec"]["revision"],
            "for2sec_inventory_sha256": cfg["for2sec"]["inventory_sha256"],
            "assignments_sha256": cfg["for2sec"]["assignments_sha256"],
            "deepvoice_archive_sha256": cfg["deepvoice"]["archive_sha256"],
            "deepvoice_inventory_sha256": cfg["deepvoice"]["inventory_sha256"],
        },
        "checks": {"for2sec": for_checks, "deepvoice": deepvoice_checks},
        "all_checks_pass": all((*for_checks.values(), *deepvoice_checks.values())),
        "audio_access": "none; metadata CSV inputs only",
        "stage6_started": False,
    }
    return write_outputs(
        for_manifest, deepvoice_manifest, cfg, manifest_dir, report_dir, report
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--for-inventory", type=Path, required=True)
    parser.add_argument("--assignments", type=Path, required=True)
    parser.add_argument("--deepvoice-inventory", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/freeze.yaml"))
    parser.add_argument("--manifest-dir", type=Path, default=Path("data/manifests"))
    parser.add_argument(
        "--report-dir", type=Path,
        default=Path("docs/audit_evidence/stage5_freeze"),
    )
    args = parser.parse_args()
    run(
        args.for_inventory, args.assignments, args.deepvoice_inventory,
        args.config, args.manifest_dir, args.report_dir,
    )


if __name__ == "__main__":
    main()
