"""Tests for the Stage 1 audit tools, on small synthetic fixtures (no real data)."""
import json
import numpy as np
import pandas as pd
import pytest
import soundfile as sf

from src.audit import for2sec_audit as fa
from src.audit import deepvoice_metadata_audit as dv
from src.audit.common import AuditError, auc_separability

RNG = np.random.default_rng(0)


def _speech_like(sr, sec=2.0, f0=None):
    t = np.arange(int(sr * sec)) / sr
    f0 = f0 or RNG.uniform(90, 250)
    env = 0.5 * (1 + np.sin(2 * np.pi * RNG.uniform(2, 6) * t))
    x = sum(np.sin(2 * np.pi * f0 * k * t) / k for k in range(1, 8)) * env
    x += 0.01 * RNG.standard_normal(len(t))
    return (0.3 * x / np.max(np.abs(x))).astype(np.float32)


@pytest.fixture
def for_root(tmp_path):
    root = tmp_path / "for2sec"
    for lab, sr in (("REAL", 16000), ("FAKE", 22050)):  # deliberate sample-rate shortcut
        d = root / lab
        d.mkdir(parents=True)
        for i in range(12):
            sf.write(d / f"file{i}_{lab.lower()}.wav", _speech_like(sr), sr, subtype="PCM_16")
    base = sf.read(root / "REAL" / "file0_real.wav", dtype="float32")[0]
    sf.write(root / "REAL" / "copy_bytes.wav", base, 16000, subtype="PCM_16")      # byte dup
    sf.write(root / "FAKE" / "copy_pcm24.wav", base, 16000, subtype="PCM_24")      # PCM dup, other label
    sf.write(root / "REAL" / "near.wav", base + 1e-3 * RNG.standard_normal(len(base)).astype(np.float32),
             16000, subtype="PCM_16")                                              # near dup
    (root / "REAL" / "corrupt.wav").write_bytes(b"RIFF\x00\x00garbage")           # corrupt
    return root


def test_for_audit_end_to_end(for_root, tmp_path):
    rep = fa.run(for_root, tmp_path / "out", revision="test-rev")
    inv = pd.read_csv(tmp_path / "out" / "for2sec_inventory.csv")
    assert rep["counts"]["files"] == 28
    assert rep["counts"]["decode_failures"] == 1
    assert rep["exact_duplicates_bytes"]["groups"] == 1
    # PCM16 and PCM24 copies of the same signal decode to the same PCM hash, across labels
    assert rep["exact_duplicates_pcm"]["files_in_groups"] >= 3
    assert rep["exact_duplicates_pcm"]["cross_label_groups"] == 1
    near = inv.loc[inv.rel_path.str.endswith("near.wav"), "fp_max_sim"].item()
    assert near > 0.98
    g = inv.set_index("rel_path")["neardup_group_095"]
    assert g["REAL/near.wav"] == g["REAL/file0_real.wav"]
    assert "neardup_group" not in inv
    for col in ("neardup_group_090", "neardup_group_095", "neardup_group_098"):
        assert col in inv
    by_th = rep["near_duplicates"]["by_threshold"]
    assert set(by_th) == {"0.9", "0.95", "0.98"}
    for st in by_th.values():
        assert {"n_groups", "multi_file_groups", "largest_group", "largest_group_pct",
                "d14_pass"} <= set(st)
        assert st["n_groups"] <= 27  # 28 files minus the corrupt one
    # Tiny fixture: the duplicate cluster around file0_real (>= 2 of 27 clips, > 5%) fails D14
    assert rep["near_duplicates"]["d14_selected_threshold"] == "pcm_hash_only"
    assert "D14 selected threshold: pcm_hash_only" in \
        (tmp_path / "out" / "for2sec_summary.md").read_text(encoding="utf-8")
    sanity = rep["near_duplicates"]["pcm_dup_sanity"]
    assert sanity["pairs"] >= 3 and sanity["min_sim"] > 0.999  # identical PCM -> identical fp
    assert "samplerate" in rep["shortcut_flags"]["numeric_high"]
    assert (tmp_path / "out" / "for2sec_summary.md").read_text().startswith("# FoR-2sec")


def _unit(deg, dim=8):
    v = np.zeros(dim, np.float32)
    v[0], v[1] = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    return v


def test_neardup_grouping_chains_transitively():
    # A~B and B~C at cos(16°)≈0.961, but A vs C is cos(32°)≈0.848; D is orthogonal.
    F = np.stack([_unit(0), _unit(16), _unit(32), np.eye(8, dtype=np.float32)[2]])
    valid = np.ones(4, bool)
    pairs, _, groups, _ = fa.near_duplicates(F, valid, fa.Thresholds())
    sims = {(i, j): s for i, j, s in pairs.itertuples(index=False)}
    assert (0, 2) not in sims or sims[(0, 2)] < 0.95  # A is not ~ C directly
    g95 = groups[0.95]
    assert g95[0] == g95[1] == g95[2] != g95[3]       # ...yet one group via B
    assert len(set(groups[0.98])) == 4                 # nothing groups at 0.98
    st = fa.neardup_group_stats(g95, np.ones(4, bool), fa.Thresholds())
    assert st == {"n_groups": 2, "multi_file_groups": 1, "largest_group": 3,
                  "largest_group_pct": 75.0, "d14_pass": False}


def test_neardup_group_stats_excludes_corrupt():
    groups = np.array([0, 0, 2, 3])                   # file 3 is corrupt (its own singleton)
    decodable = np.array([True, True, True, False])
    st = fa.neardup_group_stats(groups, decodable, fa.Thresholds())
    assert st["n_groups"] == 2 and st["largest_group"] == 2
    assert abs(st["largest_group_pct"] - 100 * 2 / 3) < 1e-3


def test_d14_select_threshold():
    th = fa.Thresholds()
    def bt(p95, p98):
        return {"0.9": {"d14_pass": False}, "0.95": {"d14_pass": p95},
                "0.98": {"d14_pass": p98}}
    assert fa.d14_select_threshold(bt(True, True), th) == 0.95
    assert fa.d14_select_threshold(bt(False, True), th) == 0.98
    assert fa.d14_select_threshold(bt(False, False), th) == "pcm_hash_only"
    # boundary: exactly 5% passes ("<= 5%")
    st = fa.neardup_group_stats(np.r_[np.zeros(5, int), np.arange(1, 96)],
                                np.ones(100, bool), th)
    assert st["largest_group_pct"] == 5.0 and st["d14_pass"] is True


def test_neardup_col():
    assert [fa.neardup_col(s) for s in (0.90, 0.95, 0.98)] == \
        ["neardup_group_090", "neardup_group_095", "neardup_group_098"]


def test_pcm_dup_min_sim():
    F = np.stack([_unit(0), _unit(10), _unit(90), _unit(0), _unit(45)])
    valid = np.array([True, True, True, True, False])
    h = pd.Series(["x", "x", "y", None, "y"])
    r = fa.pcm_dup_min_sim(F, valid, h)
    assert r["pairs"] == 2 and r["pairs_without_fingerprint"] == 1
    assert abs(r["min_sim"] - np.cos(np.radians(10))) < 1e-6
    assert fa.pcm_dup_min_sim(F, valid, pd.Series([None] * 5))["min_sim"] is None


def test_label_inference_fails_loudly(tmp_path):
    d = tmp_path / "ds" / "unknown"
    d.mkdir(parents=True)
    sf.write(d / "a.wav", _speech_like(16000), 16000)
    with pytest.raises(AuditError):
        fa.run(tmp_path / "ds", tmp_path / "o", revision="r")


def test_auc_separability():
    y = pd.Series(["REAL"] * 50 + ["FAKE"] * 50)
    assert auc_separability(pd.Series(np.r_[np.zeros(50), np.ones(50)]), y) == 1.0
    assert abs(auc_separability(pd.Series(RNG.standard_normal(100)), y) - 0.5) < 0.2


@pytest.fixture
def dv_root(tmp_path):
    root = tmp_path / "KAGGLE" / "AUDIO"
    (root / "REAL").mkdir(parents=True)
    (root / "FAKE").mkdir(parents=True)
    sf.write(root / "REAL" / "obama-original.wav", _speech_like(44100, 5), 44100)
    sf.write(root / "FAKE" / "Obama-to-Biden.wav", _speech_like(44100, 5), 44100)
    pd.DataFrame({"f1": [0.1, 0.2, 0.3], "LABEL": ["REAL", "FAKE", "FAKE"]}) \
        .to_csv(tmp_path / "KAGGLE" / "DATASET-balanced.csv", index=False)
    return tmp_path / "KAGGLE"


def test_deepvoice_metadata_only(dv_root, tmp_path):
    rep = dv.run(dv_root, tmp_path / "dv", revision="v1")
    assert rep["by_label"] == {"REAL": 1, "FAKE": 1}
    assert rep["source_speakers"] == ["obama"] and rep["target_speakers"] == ["biden"]
    assert rep["csv_files"][0]["label_counts"] == {"FAKE": 2, "REAL": 1}
    assert abs(rep["total_seconds_by_label"]["REAL"] - 5.0) < 1e-3
    # feature columns must never be summarized
    assert "f1" not in json.dumps(rep["csv_files"][0].get("label_counts"))


def test_decoding_is_blocked_during_blind_audit(dv_root):
    wav = next(dv_root.rglob("*.wav"))
    with dv.decoding_forbidden():
        with pytest.raises(dv.BlindAuditViolation):
            sf.read(str(wav))
        with pytest.raises(dv.BlindAuditViolation):
            import librosa
            librosa.load(str(wav))
    sf.read(str(wav))  # restored afterwards
