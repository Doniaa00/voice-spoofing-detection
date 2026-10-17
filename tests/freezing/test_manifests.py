"""Tests for the Stage 5 metadata-only dataset freeze."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest
import yaml

from src.freezing import manifests


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_csv(frame: pd.DataFrame, path: Path) -> str:
    frame.to_csv(path, index=False, lineterminator="\n")
    return _hash_file(path)


def _inputs(tmp_path: Path) -> tuple[Path, Path, Path, dict]:
    hashes = [f"{index:064x}" for index in range(1, 7)]
    inventory = pd.DataFrame({
        "rel_path": ["REAL/a.wav", "REAL/b.wav", "FAKE/c.wav", "FAKE/d.wav"],
        "label": ["REAL", "REAL", "FAKE", "FAKE"],
        "sha256_bytes": hashes[:4],
    })
    assignments = pd.DataFrame({
        "path": inventory["rel_path"],
        "label": inventory["label"],
        "subgroup": ["REAL", "REAL", "FAKE_mp3", "FAKE_other"],
        "group": ["g1", "g2", "g3", "g4"],
        "split": ["train", "val-A", "val-B", "test"],
    })
    deepvoice = pd.DataFrame({
        "rel_path": ["AUDIO/REAL/person-original.wav", "AUDIO/FAKE/a-to-b.wav"],
        "label": ["REAL", "FAKE"],
        "src_speaker": ["person", "a"],
        "tgt_speaker": ["", "b"],
        "samplerate": [48000, 44100],
        "channels": [2, 2],
        "duration_s": [79.5, 600.0],
        "sha256_bytes": hashes[4:],
        "header_ok": [True, True],
    })
    for_path = tmp_path / "for.csv"
    assignments_path = tmp_path / "assignments.csv"
    deepvoice_path = tmp_path / "deepvoice.csv"
    for_hash = _write_csv(inventory, for_path)
    assignments_hash = _write_csv(assignments, assignments_path)
    deepvoice_hash = _write_csv(deepvoice, deepvoice_path)
    cfg = {
        "freeze_id": "F2",
        "protocol_version": "1.0",
        "for2sec": {
            "revision": manifests.FROZEN_FOR_REVISION,
            "inventory_sha256": for_hash,
            "assignments_sha256": assignments_hash,
            "expected_rows": 4,
            "expected_labels": {"REAL": 2, "FAKE": 2},
            "expected_subgroups": {"REAL": 2, "FAKE_mp3": 1, "FAKE_other": 1},
            "expected_splits": {"train": 1, "val-A": 1, "val-B": 1, "test": 1},
        },
        "deepvoice": {
            "archive_sha256": manifests.FROZEN_DEEPVOICE_ARCHIVE_SHA256,
            "inventory_sha256": deepvoice_hash,
            "expected_rows": 2,
            "expected_labels": {"REAL": 1, "FAKE": 1},
        },
        "outputs": {
            "for2sec": "for2sec_frozen_manifest.csv",
            "deepvoice": "deepvoice_frozen_manifest.csv",
            "hashes": "manifest_hashes.csv",
        },
    }
    return for_path, assignments_path, deepvoice_path, cfg


def test_builds_frozen_contracts_and_hash_ledger(tmp_path, monkeypatch):
    for_path, assignments_path, deepvoice_path, cfg = _inputs(tmp_path)
    cfg["for2sec"]["assignments_sha256"] = manifests.FROZEN_ASSIGNMENTS_SHA256
    config_path = tmp_path / "freeze.yaml"
    config_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    # Preserve the frozen constant while making the synthetic file match the test config.
    monkeypatch.setattr(manifests, "FROZEN_ASSIGNMENTS_SHA256", _hash_file(assignments_path))
    cfg["for2sec"]["assignments_sha256"] = _hash_file(assignments_path)
    config_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    monkeypatch.setattr(
        manifests, "code_version", lambda: {"git_commit": "a" * 40, "git_dirty": False}
    )

    report = manifests.run(
        for_path, assignments_path, deepvoice_path, config_path,
        tmp_path / "manifests", tmp_path / "reports",
    )

    frozen_for = pd.read_csv(tmp_path / "manifests" / cfg["outputs"]["for2sec"])
    frozen_deepvoice = pd.read_csv(tmp_path / "manifests" / cfg["outputs"]["deepvoice"])
    ledger = pd.read_csv(tmp_path / "manifests" / cfg["outputs"]["hashes"])
    assert frozen_for.columns.tolist() == list(manifests.FOR_COLUMNS)
    assert frozen_deepvoice.columns.tolist() == list(manifests.DEEPVOICE_COLUMNS)
    assert ledger.columns.tolist() == ["manifest", "rows", "sha256"]
    assert set(ledger["rows"]) == {2, 4}
    for row in ledger.itertuples(index=False):
        assert row.sha256 == _hash_file(tmp_path / "manifests" / row.manifest)
    assert report["all_checks_pass"] is True
    assert report["audio_access"] == "none; metadata CSV inputs only"
    assert report["stage6_started"] is False
    for report_name in ("freeze_report.json", "freeze_report.md"):
        report_bytes = (tmp_path / "reports" / report_name).read_bytes()
        assert b"\r\n" not in report_bytes
        assert all(not line.endswith(b" ") for line in report_bytes.splitlines())


def test_run_checks_clean_worktree_before_reading_inputs(tmp_path, monkeypatch):
    def dirty():
        raise manifests.FreezeError("dirty")

    monkeypatch.setattr(manifests, "code_version", dirty)
    monkeypatch.setattr(
        manifests, "load_config",
        lambda _path: pytest.fail("config must not be read before the clean-tree check"),
    )
    with pytest.raises(manifests.FreezeError, match="dirty"):
        manifests.run(*(tmp_path / name for name in ("a", "b", "c", "d", "e", "f")))


@pytest.mark.parametrize(
    "bad_path",
    ["/absolute.wav", "../escape.wav", "dir/../escape.wav", r"C:\\audio\\x.wav", r"\\server\\share\\x.wav"],
)
def test_rejects_unsafe_manifest_paths(bad_path):
    with pytest.raises(manifests.FreezeError):
        manifests.safe_relative_path(bad_path)


def test_for2sec_rejects_cross_split_group(tmp_path):
    for_path, assignments_path, _deepvoice_path, cfg = _inputs(tmp_path)
    inventory = pd.read_csv(for_path, dtype=str, keep_default_na=False)
    assignments = pd.read_csv(assignments_path, dtype=str, keep_default_na=False)
    assignments.loc[0:1, "group"] = "shared"
    assignments.loc[0, "split"] = "train"
    assignments.loc[1, "split"] = "val-A"
    with pytest.raises(manifests.FreezeError, match="crosses"):
        manifests.build_for2sec_manifest(inventory, assignments, cfg["for2sec"])


def test_for2sec_rejects_label_disagreement(tmp_path):
    for_path, assignments_path, _deepvoice_path, cfg = _inputs(tmp_path)
    inventory = pd.read_csv(for_path, dtype=str, keep_default_na=False)
    assignments = pd.read_csv(assignments_path, dtype=str, keep_default_na=False)
    assignments.loc[0, "label"] = "FAKE"
    with pytest.raises(manifests.FreezeError, match="labels differ"):
        manifests.build_for2sec_manifest(inventory, assignments, cfg["for2sec"])


def test_deepvoice_rejects_header_failure(tmp_path):
    _for_path, _assignments_path, deepvoice_path, cfg = _inputs(tmp_path)
    inventory = pd.read_csv(deepvoice_path, dtype=str, keep_default_na=False)
    inventory.loc[0, "header_ok"] = "false"
    with pytest.raises(manifests.FreezeError, match="header failure"):
        manifests.build_deepvoice_manifest(inventory, cfg["deepvoice"])


def test_deepvoice_rejects_invalid_hash(tmp_path):
    _for_path, _assignments_path, deepvoice_path, cfg = _inputs(tmp_path)
    inventory = pd.read_csv(deepvoice_path, dtype=str, keep_default_na=False)
    inventory.loc[0, "sha256_bytes"] = "not-a-hash"
    with pytest.raises(manifests.FreezeError, match="invalid SHA-256"):
        manifests.build_deepvoice_manifest(inventory, cfg["deepvoice"])


def test_outputs_are_byte_deterministic(tmp_path):
    for_path, assignments_path, deepvoice_path, cfg = _inputs(tmp_path)
    for_inventory = pd.read_csv(for_path, dtype=str, keep_default_na=False)
    assignments = pd.read_csv(assignments_path, dtype=str, keep_default_na=False)
    deepvoice = pd.read_csv(deepvoice_path, dtype=str, keep_default_na=False)
    for_manifest, for_checks = manifests.build_for2sec_manifest(
        for_inventory, assignments, cfg["for2sec"]
    )
    deepvoice_manifest, deepvoice_checks = manifests.build_deepvoice_manifest(
        deepvoice, cfg["deepvoice"]
    )
    base_report = {
        "protocol_version": "1.0",
        "code_version": {"git_commit": "a" * 40, "git_dirty": False},
        "sources": {
            "for2sec_revision": manifests.FROZEN_FOR_REVISION,
            "assignments_sha256": cfg["for2sec"]["assignments_sha256"],
            "deepvoice_archive_sha256": manifests.FROZEN_DEEPVOICE_ARCHIVE_SHA256,
        },
        "checks": {"for2sec": for_checks, "deepvoice": deepvoice_checks},
    }
    manifests.write_outputs(
        for_manifest, deepvoice_manifest, cfg, tmp_path / "one", tmp_path / "report-one",
        dict(base_report),
    )
    manifests.write_outputs(
        for_manifest, deepvoice_manifest, cfg, tmp_path / "two", tmp_path / "report-two",
        dict(base_report),
    )
    for filename in cfg["outputs"].values():
        assert (tmp_path / "one" / filename).read_bytes() == (tmp_path / "two" / filename).read_bytes()
