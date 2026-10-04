"""Shared utilities for the Stage 1 dataset audit.

Nothing in this module decodes audio samples. Header-level metadata comes from
``soundfile.info``, which reads the file header only. That keeps these helpers
safe to use in the metadata-only DEEP-VOICE audit (decision D6).
"""
from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf

AUDIO_EXTS = {".wav", ".flac", ".mp3", ".ogg", ".m4a", ".aac", ".opus"}
LABEL_DIRS = {"real": "REAL", "fake": "FAKE"}
SPLIT_DIRS = {"training": "train", "train": "train", "validation": "val",
              "val": "val", "valid": "val", "testing": "test", "test": "test"}


class AuditError(RuntimeError):
    """Raised when an audit precondition fails. The audit must stop, not guess."""


def find_audio_files(root: Path) -> list[Path]:
    root = Path(root)
    if not root.is_dir():
        raise AuditError(f"Dataset root does not exist or is not a directory: {root}")
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_EXTS)
    if not files:
        raise AuditError(f"No audio files ({sorted(AUDIO_EXTS)}) found under {root}")
    return files


def infer_label(path: Path, root: Path) -> str:
    """Label = nearest ancestor directory named REAL or FAKE (case-insensitive).

    Fails loudly instead of guessing, because a wrong label mapping silently
    invalidates every downstream number.
    """
    rel_parts = path.relative_to(root).parts[:-1]
    hits = [LABEL_DIRS[p.lower()] for p in rel_parts if p.lower() in LABEL_DIRS]
    if len(hits) != 1:
        raise AuditError(f"Cannot infer a unique REAL/FAKE label for {path} (found {hits})")
    return hits[0]


def infer_split_dir(path: Path, root: Path) -> str:
    """Packaged split folder, if the packaging has one. 'none' otherwise."""
    rel_parts = path.relative_to(root).parts[:-1]
    hits = [SPLIT_DIRS[p.lower()] for p in rel_parts if p.lower() in SPLIT_DIRS]
    if len(hits) > 1:
        raise AuditError(f"Ambiguous split folders for {path}: {hits}")
    return hits[0] if hits else "none"


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def header_info(path: Path) -> dict:
    """Header-only metadata. Does NOT read audio samples."""
    try:
        info = sf.info(str(path))
        frames = int(info.frames) if info.frames and info.frames > 0 else None
        return {
            "header_ok": True, "header_error": "",
            "format": info.format, "subtype": info.subtype,
            "samplerate": int(info.samplerate), "channels": int(info.channels),
            "frames": frames,
            "duration_s": (frames / info.samplerate) if frames else np.nan,
        }
    except Exception as exc:  # noqa: BLE001 - every failure is recorded, not hidden
        return {"header_ok": False, "header_error": f"{type(exc).__name__}: {exc}",
                "format": None, "subtype": None, "samplerate": np.nan,
                "channels": np.nan, "frames": None, "duration_s": np.nan}


def filename_signature(stem: str) -> str:
    """Filename pattern with digit runs collapsed, e.g. 'file12_16k' -> 'file#_#k'."""
    return re.sub(r"\d+", "#", stem.lower())


def filename_tokens(stem: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", stem.lower()) if t and not t.isdigit()]


def environment_info() -> dict:
    def _git(*args):
        try:
            return subprocess.run(["git", *args], capture_output=True, text=True,
                                  timeout=5).stdout.strip() or None
        except Exception:  # noqa: BLE001
            return None
    import librosa  # local import: only the FoR audit needs it at runtime
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0], "platform": platform.platform(),
        "numpy": np.__version__, "pandas": pd.__version__,
        "soundfile": sf.__version__, "libsndfile": sf.__libsndfile_version__,
        "librosa": librosa.__version__,
        "git_commit": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain")),
    }


def auc_separability(values: pd.Series, labels: pd.Series, positive: str = "FAKE") -> float:
    """Univariate ROC-AUC of a single numeric feature vs the label (Mann-Whitney).

    Returns max(AUC, 1-AUC): 0.5 = no separation, 1.0 = the feature alone
    perfectly separates the classes (a shortcut).
    """
    mask = values.notna()
    v, y = values[mask].astype(float), (labels[mask] == positive)
    n_pos, n_neg = int(y.sum()), int((~y).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    ranks = v.rank(method="average")
    auc = (ranks[y].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
    return float(max(auc, 1 - auc))


def df_to_md(df: pd.DataFrame, floatfmt: str = "{:.4g}") -> str:
    """Minimal markdown table writer (no tabulate dependency)."""
    cols = [str(c) for c in df.columns]
    def fmt(x):
        if isinstance(x, (float, np.floating)):
            return str(int(x)) if np.isfinite(x) and float(x).is_integer() else floatfmt.format(x)
        return str(x)
    rows = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    rows += ["| " + " | ".join(fmt(x) for x in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(rows)


def write_json(obj, path: Path) -> None:
    Path(path).write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


@dataclass(frozen=True)
class Thresholds:
    """Audit flag thresholds. Recorded in the output so reviewers can see them."""
    shortcut_auc_high: float = 0.90
    shortcut_auc_moderate: float = 0.75
    category_purity: float = 0.99
    min_support_frac: float = 0.01
    silence_dbfs: float = -50.0
    clip_level: float = 0.999
    neardup_sims: tuple = (0.90, 0.95, 0.98)
    neardup_group_sim: float = 0.95

    def as_dict(self):
        return asdict(self)
