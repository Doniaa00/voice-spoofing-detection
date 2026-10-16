"""Stage 4: deterministic leakage-aware split of the audited FoR-2sec inventory.

This module reads Stage 1 metadata only; it never opens audio. It writes a candidate
split-assignment CSV plus JSON and Markdown check reports. Dataset manifests and
their hashes belong to Stage 5 and are deliberately not produced here.

Usage:
    python -m src.splitting.for2sec \
        --inventory /path/to/for2sec_inventory.csv \
        --summary /path/to/for2sec_summary.json \
        --config configs/split.yaml \
        --out /path/to/stage4_split
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

import numpy as np
import pandas as pd
import yaml


SUBGROUPS = ("REAL", "FAKE_mp3", "FAKE_other")
LABELS = ("REAL", "FAKE")
FROZEN_REVISION = "ff8c82c79e7bbefef811941bac9775c9328e9055"
FROZEN_SEED = 2026
FROZEN_GROUP_COLUMN = "neardup_group_095"
FROZEN_COUNTS = {
    "files": 17721,
    "labels": {"REAL": 8800, "FAKE": 8921},
    "subgroups": {"REAL": 8800, "FAKE_mp3": 7592, "FAKE_other": 1329},
    "d14_selected_threshold": 0.95,
}


class SplitError(RuntimeError):
    """Raised when a frozen split rule or input precondition is violated."""


def load_config(path: Path) -> dict[str, Any]:
    """Load and structurally validate the versioned Stage 4 split config."""
    path = Path(path)
    if not path.is_file():
        raise SplitError(f"Split config does not exist: {path}")
    try:
        cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise SplitError(f"Cannot read split config {path}: {exc}") from exc
    if not isinstance(cfg, dict):
        raise SplitError("Split config must be a YAML mapping")

    required = {"protocol_version", "dataset", "revision", "seed", "columns",
                "splits", "acceptance", "expected"}
    missing = sorted(required - set(cfg))
    if missing:
        raise SplitError(f"Split config is missing keys: {missing}")
    if cfg["protocol_version"] != "1.0" or cfg["dataset"] != "FoR-2sec":
        raise SplitError("Stage 4 requires Protocol v1.0 and dataset FoR-2sec")
    if cfg["revision"] != FROZEN_REVISION:
        raise SplitError("Split config revision differs from the D21 FoR pin")
    if cfg["seed"] != FROZEN_SEED:
        raise SplitError("Protocol v1.0 requires split seed 2026")
    if cfg["columns"].get("group") != FROZEN_GROUP_COLUMN:
        raise SplitError("D14 requires group column neardup_group_095")
    if cfg["expected"] != FROZEN_COUNTS:
        raise SplitError("Split config expected counts differ from the signed Stage 1 audit")

    expected_splits = {"train", "val-A", "val-B", "test"}
    if set(cfg["splits"]) != expected_splits:
        raise SplitError(f"Split names must be exactly {sorted(expected_splits)}")
    ratios = {name: float(value) for name, value in cfg["splits"].items()}
    if any(value <= 0 for value in ratios.values()) or not np.isclose(sum(ratios.values()), 1.0):
        raise SplitError("Split ratios must be positive and sum to 1.0")
    if not np.isclose(ratios["train"], 0.70) or not np.isclose(ratios["test"], 0.15):
        raise SplitError("Protocol v1.0 requires train/test ratios of 0.70/0.15")
    if not np.isclose(ratios["val-A"], 0.075) or not np.isclose(ratios["val-B"], 0.075):
        raise SplitError("Protocol v1.0 requires validation split 50/50 into val-A/val-B")

    tolerance = cfg["acceptance"].get("proportion_tolerance_percentage_points")
    if not isinstance(tolerance, (int, float)) or tolerance != 1.0:
        raise SplitError("Protocol v1.0 requires a 1.0 percentage-point tolerance")
    cfg["splits"] = ratios
    return cfg


def code_version() -> dict[str, Any]:
    """Return the Git commit and dirty flag required for run traceability."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True,
            text=True, timeout=5).stdout.strip()
        dirty = bool(subprocess.run(
            ["git", "status", "--porcelain"], check=True, capture_output=True,
            text=True, timeout=5).stdout.strip())
    except (OSError, subprocess.SubprocessError) as exc:
        raise SplitError(f"Cannot determine code version from Git: {exc}") from exc
    if not commit:
        raise SplitError("Git returned an empty code version")
    return {"git_commit": commit, "git_dirty": dirty}


def derive_subgroups(inventory: pd.DataFrame, label_col: str, stem_col: str) -> pd.Series:
    """Apply D16's frozen REAL / FAKE_mp3 / FAKE_other filename rule."""
    if label_col not in inventory or stem_col not in inventory:
        raise SplitError(f"Inventory must contain {label_col!r} and {stem_col!r}")
    labels = inventory[label_col].astype(str)
    invalid = sorted(set(labels) - set(LABELS))
    if invalid:
        raise SplitError(f"Unsupported FoR labels: {invalid}")
    stems = inventory[stem_col]
    if stems.isna().any() or stems.astype(str).str.strip().eq("").any():
        raise SplitError(f"Inventory column {stem_col!r} contains an empty stem")
    has_mp3 = stems.astype(str).str.lower().str.contains("mp3", regex=False)
    values = np.where(labels.eq("REAL"), "REAL",
                      np.where(has_mp3, "FAKE_mp3", "FAKE_other"))
    return pd.Series(values, index=inventory.index, name="subgroup")


def validate_source(inventory: pd.DataFrame, summary: dict[str, Any],
                    cfg: dict[str, Any]) -> pd.DataFrame:
    """Validate that inputs are the complete pinned Stage 1 FoR audit outputs."""
    columns = cfg["columns"]
    required_columns = set(columns.values())
    missing = sorted(required_columns - set(inventory.columns))
    if missing:
        raise SplitError(f"FoR inventory is missing columns: {missing}")
    if inventory.empty:
        raise SplitError("FoR inventory is empty")

    if summary.get("dataset") != cfg["dataset"]:
        raise SplitError(f"Summary dataset mismatch: {summary.get('dataset')!r}")
    if summary.get("revision") != cfg["revision"]:
        raise SplitError("FoR revision does not match the D21 pin")
    selected = summary.get("near_duplicates", {}).get("d14_selected_threshold")
    if not isinstance(selected, (int, float)) or not np.isclose(
            selected, cfg["expected"]["d14_selected_threshold"]):
        raise SplitError("Stage 1 summary does not select D14 threshold 0.95")

    expected_files = int(cfg["expected"]["files"])
    summary_files = summary.get("counts", {}).get("files")
    if len(inventory) != expected_files or summary_files != expected_files:
        raise SplitError(
            f"Expected {expected_files} audited FoR rows; inventory={len(inventory)}, "
            f"summary={summary_files!r}")

    path_col = columns["path"]
    paths = inventory[path_col]
    if paths.isna().any() or paths.astype(str).str.strip().eq("").any():
        raise SplitError(f"Inventory column {path_col!r} contains an empty path")
    if paths.astype(str).duplicated().any():
        duplicates = paths.astype(str)[paths.astype(str).duplicated()].head(3).tolist()
        raise SplitError(f"FoR inventory contains duplicate relative paths: {duplicates}")
    bad_paths = []
    for value in paths.astype(str):
        normalized = value.replace("\\", "/")
        posix_path = PurePosixPath(normalized)
        windows_path = PureWindowsPath(value)
        if (posix_path.is_absolute() or windows_path.drive or windows_path.root
                or ".." in posix_path.parts):
            bad_paths.append(value)
    if bad_paths:
        raise SplitError(f"FoR inventory paths must be safe relative paths: {bad_paths[:3]}")

    decode = inventory[columns["decode_ok"]]
    if decode.dtype != bool:
        normalized = decode.astype(str).str.strip().str.lower()
        if not normalized.isin({"true", "false"}).all():
            raise SplitError(f"Inventory column {columns['decode_ok']!r} is not boolean")
        decode = normalized.eq("true")
    if not decode.all():
        raise SplitError("Pinned FoR audit reported zero decode failures, but input contains failures")
    if inventory[columns["group"]].isna().any():
        raise SplitError(f"Inventory column {columns['group']!r} contains missing groups")

    work = pd.DataFrame({
        "path": paths.astype(str).str.replace("\\", "/", regex=False),
        "label": inventory[columns["label"]].astype(str),
        "stem": inventory[columns["stem"]].astype(str),
        "group": inventory[columns["group"]].astype(str),
    })
    work["subgroup"] = derive_subgroups(inventory, columns["label"], columns["stem"])

    label_counts = work["label"].value_counts().to_dict()
    subgroup_counts = work["subgroup"].value_counts().to_dict()
    if label_counts != cfg["expected"]["labels"]:
        raise SplitError(f"FoR label counts differ from the signed audit: {label_counts}")
    if subgroup_counts != cfg["expected"]["subgroups"]:
        raise SplitError(f"FoR subgroup counts differ from the signed audit: {subgroup_counts}")
    summary_labels = summary.get("counts", {}).get("by_label")
    if summary_labels != cfg["expected"]["labels"]:
        raise SplitError(f"Summary label counts differ from the signed audit: {summary_labels}")
    return work


def allocate_targets(total: int, ratios: dict[str, float]) -> dict[str, int]:
    """Convert fractional split ratios to integer targets by largest remainder."""
    raw = {name: total * ratio for name, ratio in ratios.items()}
    targets = {name: int(np.floor(value)) for name, value in raw.items()}
    remainder = total - sum(targets.values())
    order = sorted(ratios, key=lambda name: (-(raw[name] - targets[name]), name))
    for name in order[:remainder]:
        targets[name] += 1
    return targets


def assign_groups(source: pd.DataFrame, ratios: dict[str, float], seed: int) -> pd.DataFrame:
    """Assign whole near-duplicate groups using deterministic deficit minimization."""
    splits = tuple(ratios)
    group_counts = source.groupby(["group", "subgroup"], sort=True).size().unstack(fill_value=0)
    group_counts = group_counts.reindex(columns=SUBGROUPS, fill_value=0).astype(int)
    subgroup_totals = source["subgroup"].value_counts().reindex(SUBGROUPS, fill_value=0)
    targets = pd.DataFrame({
        subgroup: allocate_targets(int(subgroup_totals[subgroup]), ratios)
        for subgroup in SUBGROUPS
    }).T.reindex(columns=splits)

    rng = np.random.default_rng(seed)
    group_ids = sorted(group_counts.index.astype(str))
    tie_rank = dict(zip(np.asarray(group_ids)[rng.permutation(len(group_ids))],
                        range(len(group_ids))))
    ordered = sorted(group_ids, key=lambda group: (-int(group_counts.loc[group].sum()),
                                                   tie_rank[group], group))
    assigned = pd.DataFrame(0, index=SUBGROUPS, columns=splits, dtype=int)
    split_totals = pd.Series(0, index=splits, dtype=int)
    overall_targets = pd.Series(allocate_targets(len(source), ratios)).reindex(splits)
    assignment: dict[str, str] = {}

    target_values = targets.to_numpy(dtype=float)
    target_den = np.maximum(target_values, 1.0)
    overall_den = np.maximum(overall_targets.to_numpy(dtype=float), 1.0)
    for group in ordered:
        vector = group_counts.loc[group].reindex(SUBGROUPS).to_numpy(dtype=int)
        candidates = []
        for split_index, split in enumerate(splits):
            trial = assigned.to_numpy(copy=True)
            trial[:, split_index] += vector
            subgroup_error = np.square((trial - target_values) / target_den).sum()
            overshoot = np.square(np.maximum(trial - target_values, 0) / target_den).sum()
            trial_totals = split_totals.to_numpy(copy=True)
            trial_totals[split_index] += int(vector.sum())
            size_error = np.square((trial_totals - overall_targets.to_numpy()) / overall_den).sum()
            candidates.append((subgroup_error + 10.0 * overshoot + 0.1 * size_error,
                               int(split_totals[split]), split_index, split))
        _, _, split_index, chosen = min(candidates)
        assigned.iloc[:, split_index] += vector
        split_totals[chosen] += int(vector.sum())
        assignment[group] = chosen

    result = source[["path", "label", "subgroup", "group"]].copy()
    result["split"] = result["group"].map(assignment)
    return result.sort_values("path", kind="stable").reset_index(drop=True)


def check_split(source: pd.DataFrame, assignments: pd.DataFrame,
                cfg: dict[str, Any]) -> dict[str, Any]:
    """Run every frozen Stage 4 acceptance check and return a serializable report."""
    splits = tuple(cfg["splits"])
    tolerance = float(cfg["acceptance"]["proportion_tolerance_percentage_points"])
    checks: dict[str, bool] = {
        "row_count_matches_source": len(assignments) == len(source),
        "paths_unique": not assignments["path"].duplicated().any(),
        "path_set_matches_source": set(assignments["path"]) == set(source["path"]),
        "split_values_valid": set(assignments["split"]) == set(splits),
        "groups_do_not_cross_splits": bool(
            assignments.groupby("group")["split"].nunique().le(1).all()),
    }

    split_sizes = {}
    for split in splits:
        count = int((assignments["split"] == split).sum())
        split_sizes[split] = {
            "count": count,
            "fraction": round(count / len(assignments), 8),
            "target_fraction": float(cfg["splits"][split]),
        }

    def proportion_report(column: str, categories: tuple[str, ...]) -> tuple[dict, float]:
        full = assignments[column].value_counts(normalize=True).reindex(categories, fill_value=0.0)
        table: dict[str, Any] = {"full": {k: round(float(v), 8) for k, v in full.items()}}
        max_deviation = 0.0
        for split in splits:
            part = assignments.loc[assignments["split"] == split, column]
            props = part.value_counts(normalize=True).reindex(categories, fill_value=0.0)
            deviations = (props - full).abs() * 100.0
            max_deviation = max(max_deviation, float(deviations.max()))
            table[split] = {
                category: {
                    "fraction": round(float(props[category]), 8),
                    "deviation_percentage_points": round(float(deviations[category]), 6),
                }
                for category in categories
            }
        return table, max_deviation

    subgroup_table, subgroup_max = proportion_report("subgroup", SUBGROUPS)
    class_table, class_max = proportion_report("label", LABELS)
    checks["subgroup_proportions_within_1pp"] = subgroup_max <= tolerance + 1e-12
    checks["class_proportions_within_1pp"] = class_max <= tolerance + 1e-12
    checks["all_pass"] = all(checks.values())

    return {
        "dataset": cfg["dataset"],
        "revision": cfg["revision"],
        "protocol_version": cfg["protocol_version"],
        "seed": cfg["seed"],
        "group_column": cfg["columns"]["group"],
        "ratios": cfg["splits"],
        "proportion_tolerance_percentage_points": tolerance,
        "checks": checks,
        "split_sizes": split_sizes,
        "subgroup_proportions": subgroup_table,
        "class_proportions": class_table,
        "max_subgroup_deviation_percentage_points": round(subgroup_max, 6),
        "max_class_deviation_percentage_points": round(class_max, 6),
    }


def write_outputs(assignments: pd.DataFrame, report: dict[str, Any], out: Path) -> None:
    """Write Stage 4 candidate assignments and check reports (never hashes/manifests)."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    assignments.to_csv(out / "for2sec_split_assignments.csv", index=False, lineterminator="\n")
    (out / "for2sec_split_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Stage 4 FoR leakage-aware split report",
        "",
        f"- Dataset revision: `{report['revision']}`",
        f"- Protocol: v{report['protocol_version']}",
        f"- Seed: {report['seed']}",
        f"- Code commit: `{report['code_version']['git_commit']}` "
        f"(dirty: {report['code_version']['git_dirty']})",
        f"- Group column: `{report['group_column']}`",
        f"- All automated checks pass: **{report['checks']['all_pass']}**",
        "",
        "## Split sizes",
        "",
        "| Split | Count | Fraction | Target |",
        "|---|---:|---:|---:|",
    ]
    for split, values in report["split_sizes"].items():
        lines.append(
            f"| {split} | {values['count']} | {values['fraction']:.4f} | "
            f"{values['target_fraction']:.4f} |")
    lines += ["", "## Checks", ""]
    lines.extend(f"- {name}: {value}" for name, value in report["checks"].items())
    lines += [
        "",
        f"Maximum subgroup deviation: "
        f"{report['max_subgroup_deviation_percentage_points']:.6f} percentage points.",
        f"Maximum class deviation: "
        f"{report['max_class_deviation_percentage_points']:.6f} percentage points.",
        "",
        "This is a Stage 4 assignment report, not the Stage 5 dataset freeze (F2).",
    ]
    (out / "for2sec_split_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(inventory_path: Path, summary_path: Path, config_path: Path,
        out: Path) -> dict[str, Any]:
    """Execute the FoR-only Stage 4 split and fail if any acceptance check fails."""
    for name, path in (("inventory", inventory_path), ("summary", summary_path)):
        if not Path(path).is_file():
            raise SplitError(f"FoR {name} input does not exist: {path}")
    cfg = load_config(config_path)
    version = code_version()
    if version["git_dirty"]:
        raise SplitError(
            "Stage 4 refuses to generate results from a dirty Git worktree; "
            "commit or otherwise clean the approved changes first")
    try:
        inventory = pd.read_csv(inventory_path)
    except Exception as exc:  # noqa: BLE001 - normalize input failure as a clear stage error
        raise SplitError(f"Cannot read FoR inventory {inventory_path}: {exc}") from exc
    try:
        summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SplitError(f"Cannot read FoR summary {summary_path}: {exc}") from exc
    source = validate_source(inventory, summary, cfg)
    assignments = assign_groups(source, cfg["splits"], cfg["seed"])
    report = check_split(source, assignments, cfg)
    report["code_version"] = version
    if not report["checks"]["all_pass"]:
        failed = [name for name, passed in report["checks"].items()
                  if name != "all_pass" and not passed]
        raise SplitError(f"Stage 4 acceptance checks failed: {failed}")
    write_outputs(assignments, report, out)
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True, type=Path,
                        help="Stage 1 FoR for2sec_inventory.csv")
    parser.add_argument("--summary", required=True, type=Path,
                        help="Stage 1 FoR for2sec_summary.json")
    parser.add_argument("--config", type=Path, default=Path("configs/split.yaml"))
    parser.add_argument("--out", required=True, type=Path,
                        help="Output directory (outside data/manifests until Stage 5)")
    args = parser.parse_args(argv)
    report = run(args.inventory, args.summary, args.config, args.out)
    print(f"Stage 4 FoR split passed: {report['split_sizes']}")


if __name__ == "__main__":
    main()
