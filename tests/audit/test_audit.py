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
    g = inv.set_index("rel_path")["neardup_group"]
    assert g["REAL/near.wav"] == g["REAL/file0_real.wav"]
    assert "samplerate" in rep["shortcut_flags"]["numeric_high"]
    assert (tmp_path / "out" / "for2sec_summary.md").read_text().startswith("# FoR-2sec")


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
