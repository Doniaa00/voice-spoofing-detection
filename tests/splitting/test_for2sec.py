"""Stage 4 split tests use metadata-only synthetic fixtures; no dataset audio is read."""
from __future__ import annotations

import json

import pandas as pd
import pytest
import yaml

from src.splitting import for2sec


def _config(counts: dict[str, int],
            revision: str = for2sec.FROZEN_REVISION) -> dict:
    return {
        "protocol_version": "1.0",
        "dataset": "FoR-2sec",
        "revision": revision,
        "seed": 2026,
        "columns": {
            "path": "rel_path",
            "label": "label",
            "stem": "stem",
            "decode_ok": "decode_ok",
            "group": "neardup_group_095",
        },
        "splits": {"train": 0.70, "val-A": 0.075, "val-B": 0.075, "test": 0.15},
        "acceptance": {"proportion_tolerance_percentage_points": 1.0},
        "expected": {
            "files": sum(counts.values()),
            "labels": {"REAL": counts["REAL"],
                       "FAKE": counts["FAKE_mp3"] + counts["FAKE_other"]},
            "subgroups": counts,
            "d14_selected_threshold": 0.95,
        },
    }


def _inventory(counts: dict[str, int]) -> pd.DataFrame:
    rows = []
    index = 0
    for subgroup, count in counts.items():
        label = "REAL" if subgroup == "REAL" else "FAKE"
        for j in range(count):
            stem = f"file{index}_real" if label == "REAL" else f"file{index}_fake"
            if subgroup == "FAKE_mp3":
                stem += "_mp3"
            rows.append({
                "rel_path": f"{label}/{stem}.wav",
                "label": label,
                "stem": stem,
                "decode_ok": True,
                "neardup_group_095": index,
            })
            index += 1
    # Two same-subgroup two-file components exercise atomic group assignment.
    rows[1]["neardup_group_095"] = rows[0]["neardup_group_095"]
    fake_start = counts["REAL"]
    rows[fake_start + 1]["neardup_group_095"] = rows[fake_start]["neardup_group_095"]
    return pd.DataFrame(rows)


def _summary(cfg: dict) -> dict:
    return {
        "dataset": "FoR-2sec",
        "revision": cfg["revision"],
        "counts": {"files": cfg["expected"]["files"],
                   "by_label": cfg["expected"]["labels"]},
        "near_duplicates": {"d14_selected_threshold": 0.95},
    }


def test_load_config_accepts_frozen_values_and_rejects_ratio_change(tmp_path):
    cfg = _config(for2sec.FROZEN_COUNTS["subgroups"])
    path = tmp_path / "split.yaml"
    path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    assert for2sec.load_config(path)["seed"] == 2026
    cfg["splits"]["train"] = 0.69
    cfg["splits"]["test"] = 0.16
    path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    with pytest.raises(for2sec.SplitError, match="train/test ratios"):
        for2sec.load_config(path)


def test_load_config_normalizes_quoted_numeric_ratios(tmp_path):
    cfg = _config(for2sec.FROZEN_COUNTS["subgroups"])
    cfg["splits"] = {name: str(value) for name, value in cfg["splits"].items()}
    path = tmp_path / "split.yaml"
    path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    loaded = for2sec.load_config(path)
    assert loaded["splits"] == {"train": 0.70, "val-A": 0.075,
                                "val-B": 0.075, "test": 0.15}
    assert all(isinstance(value, float) for value in loaded["splits"].values())


def test_load_config_rejects_frozen_seed_revision_group_or_counts_change(tmp_path):
    baseline = _config(for2sec.FROZEN_COUNTS["subgroups"])
    path = tmp_path / "split.yaml"
    changes = [
        ("seed", 7, "seed 2026"),
        ("revision", "other", "D21 FoR pin"),
    ]
    for key, value, message in changes:
        cfg = _config(for2sec.FROZEN_COUNTS["subgroups"])
        cfg[key] = value
        path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
        with pytest.raises(for2sec.SplitError, match=message):
            for2sec.load_config(path)
    baseline["columns"]["group"] = "neardup_group_098"
    path.write_text(yaml.safe_dump(baseline, sort_keys=False), encoding="utf-8")
    with pytest.raises(for2sec.SplitError, match="neardup_group_095"):
        for2sec.load_config(path)
    baseline = _config(for2sec.FROZEN_COUNTS["subgroups"])
    baseline["expected"]["files"] -= 1
    path.write_text(yaml.safe_dump(baseline, sort_keys=False), encoding="utf-8")
    with pytest.raises(for2sec.SplitError, match="signed Stage 1 audit"):
        for2sec.load_config(path)


def test_code_version_reports_commit_and_dirty_state(monkeypatch):
    class Result:
        def __init__(self, stdout):
            self.stdout = stdout

    outputs = iter([Result("abc123\n"), Result(" M file.py\n")])
    monkeypatch.setattr(for2sec.subprocess, "run", lambda *args, **kwargs: next(outputs))
    assert for2sec.code_version() == {"git_commit": "abc123", "git_dirty": True}


def test_derive_subgroups_uses_the_frozen_mp3_stem_rule():
    inv = pd.DataFrame({
        "label": ["REAL", "FAKE", "FAKE"],
        "stem": ["file1_real", "file2.MP3.wav_norm", "file3_fake"],
    })
    assert for2sec.derive_subgroups(inv, "label", "stem").tolist() == \
        ["REAL", "FAKE_mp3", "FAKE_other"]
    inv.loc[0, "label"] = "UNKNOWN"
    with pytest.raises(for2sec.SplitError, match="Unsupported FoR labels"):
        for2sec.derive_subgroups(inv, "label", "stem")


def test_validate_source_rejects_wrong_revision_and_unsafe_paths():
    counts = {"REAL": 80, "FAKE_mp3": 70, "FAKE_other": 50}
    cfg = _config(counts)
    inv = _inventory(counts)
    summary = _summary(cfg)
    assert len(for2sec.validate_source(inv, summary, cfg)) == 200
    summary["revision"] = "wrong"
    with pytest.raises(for2sec.SplitError, match="D21 pin"):
        for2sec.validate_source(inv, summary, cfg)
    summary = _summary(cfg)
    inv.loc[0, "rel_path"] = "../outside.wav"
    with pytest.raises(for2sec.SplitError, match="safe relative paths"):
        for2sec.validate_source(inv, summary, cfg)


@pytest.mark.parametrize("bad_path", [
    r"C:\secret.wav",
    "C:/secret.wav",
    r"\\server\share\secret.wav",
    "//server/share/secret.wav",
    "/secret.wav",
    "REAL/../secret.wav",
])
def test_validate_source_rejects_absolute_or_traversing_paths(bad_path):
    counts = {"REAL": 80, "FAKE_mp3": 70, "FAKE_other": 50}
    cfg = _config(counts)
    inv = _inventory(counts)
    inv.loc[0, "rel_path"] = bad_path
    with pytest.raises(for2sec.SplitError, match="safe relative paths"):
        for2sec.validate_source(inv, _summary(cfg), cfg)


def test_allocate_targets_uses_largest_remainder():
    ratios = {"train": 0.70, "val-A": 0.075, "val-B": 0.075, "test": 0.15}
    targets = for2sec.allocate_targets(11, ratios)
    assert sum(targets.values()) == 11
    assert targets == {"train": 8, "val-A": 1, "val-B": 1, "test": 1}


def test_assign_groups_is_deterministic_group_safe_and_balanced():
    counts = {"REAL": 800, "FAKE_mp3": 700, "FAKE_other": 500}
    cfg = _config(counts)
    source = for2sec.validate_source(_inventory(counts), _summary(cfg), cfg)
    first = for2sec.assign_groups(source, cfg["splits"], cfg["seed"])
    second = for2sec.assign_groups(source.sample(frac=1, random_state=7),
                                   cfg["splits"], cfg["seed"])
    pd.testing.assert_frame_equal(first, second)
    report = for2sec.check_split(source, first, cfg)
    assert report["checks"]["all_pass"]
    assert first.groupby("group")["split"].nunique().max() == 1


def test_check_split_detects_cross_split_group():
    counts = {"REAL": 800, "FAKE_mp3": 700, "FAKE_other": 500}
    cfg = _config(counts)
    source = for2sec.validate_source(_inventory(counts), _summary(cfg), cfg)
    assignments = for2sec.assign_groups(source, cfg["splits"], cfg["seed"])
    group = assignments["group"].value_counts().loc[lambda counts_: counts_ > 1].index[0]
    members = assignments.index[assignments["group"] == group].tolist()
    assert len(members) == 2
    assignments.loc[members[0], "split"] = "train"
    assignments.loc[members[1], "split"] = "test"
    report = for2sec.check_split(source, assignments, cfg)
    assert not report["checks"]["groups_do_not_cross_splits"]
    assert not report["checks"]["all_pass"]


def test_run_writes_candidate_assignments_and_reports_only(tmp_path, monkeypatch):
    counts = {"REAL": 800, "FAKE_mp3": 700, "FAKE_other": 500}
    cfg = _config(counts)
    inventory_path = tmp_path / "for2sec_inventory.csv"
    summary_path = tmp_path / "for2sec_summary.json"
    config_path = tmp_path / "split.yaml"
    out = tmp_path / "out"
    _inventory(counts).to_csv(inventory_path, index=False)
    summary_path.write_text(json.dumps(_summary(cfg)), encoding="utf-8")
    config_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr(for2sec, "load_config", lambda _: cfg)
    monkeypatch.setattr(for2sec, "code_version", lambda: {
        "git_commit": "clean-commit", "git_dirty": False})

    report = for2sec.run(inventory_path, summary_path, config_path, out)
    assert report["checks"]["all_pass"]
    assert sorted(path.name for path in out.iterdir()) == [
        "for2sec_split_assignments.csv",
        "for2sec_split_report.json",
        "for2sec_split_report.md",
    ]
    assignment_columns = pd.read_csv(out / "for2sec_split_assignments.csv").columns.tolist()
    assert assignment_columns == ["path", "label", "subgroup", "group", "split"]
    assert "sha256" not in assignment_columns
    assert "not the Stage 5 dataset freeze" in \
        (out / "for2sec_split_report.md").read_text(encoding="utf-8")


def test_run_refuses_dirty_worktree_without_writing_outputs(tmp_path, monkeypatch):
    counts = {"REAL": 80, "FAKE_mp3": 70, "FAKE_other": 50}
    cfg = _config(counts)
    inventory_path = tmp_path / "inventory.csv"
    summary_path = tmp_path / "summary.json"
    config_path = tmp_path / "split.yaml"
    out = tmp_path / "out"
    _inventory(counts).to_csv(inventory_path, index=False)
    summary_path.write_text(json.dumps(_summary(cfg)), encoding="utf-8")
    config_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr(for2sec, "load_config", lambda _: cfg)
    monkeypatch.setattr(for2sec, "code_version", lambda: {
        "git_commit": "dirty-commit", "git_dirty": True})

    with pytest.raises(for2sec.SplitError, match="dirty Git worktree"):
        for2sec.run(inventory_path, summary_path, config_path, out)
    assert not out.exists()


def test_main_runs_the_cli_contract(tmp_path, capsys, monkeypatch):
    counts = {"REAL": 800, "FAKE_mp3": 700, "FAKE_other": 500}
    cfg = _config(counts)
    inventory_path = tmp_path / "inventory.csv"
    summary_path = tmp_path / "summary.json"
    config_path = tmp_path / "split.yaml"
    out = tmp_path / "out"
    _inventory(counts).to_csv(inventory_path, index=False)
    summary_path.write_text(json.dumps(_summary(cfg)), encoding="utf-8")
    config_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr(for2sec, "load_config", lambda _: cfg)
    monkeypatch.setattr(for2sec, "code_version", lambda: {
        "git_commit": "clean-commit", "git_dirty": False})
    for2sec.main(["--inventory", str(inventory_path), "--summary", str(summary_path),
                  "--config", str(config_path), "--out", str(out)])
    assert "Stage 4 FoR split passed" in capsys.readouterr().out
