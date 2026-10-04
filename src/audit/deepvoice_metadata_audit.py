"""Stage 1 — METADATA-ONLY audit of DEEP-VOICE (approved decision D6).

Allowed: file counts, class counts, formats, header sample rates / durations,
byte hashes, directory structure, filename-encoded speaker info, CSV schema and
label counts, provenance.
Forbidden: decoding samples, listening, spectrograms, feature statistics,
model scoring, threshold experiments.

The forbidden set is enforced in code: while this module runs, audio-decoding
entry points are replaced with a function that raises. A violation fails the
run; it cannot happen silently.

Usage:
    python -m src.audit.deepvoice_metadata_audit --root /content/data/deep_voice \
        --out /content/audit_out/deepvoice --revision "<kaggle version number>"
"""
from __future__ import annotations

import argparse
import contextlib
import re
from pathlib import Path

import pandas as pd
import soundfile as sf

from .common import (AuditError, df_to_md, find_audio_files, header_info, infer_label,
                     sha256_file, write_json)

ATTESTATION = ("BLIND AUDIT ATTESTATION: this run read file headers, byte hashes, "
               "filenames and CSV schema/label counts only. No audio samples were "
               "decoded, no features computed, no model run.")


class BlindAuditViolation(RuntimeError):
    pass


@contextlib.contextmanager
def decoding_forbidden():
    """Disable sample-decoding APIs for the duration of the audit."""
    def _refuse(*_a, **_k):
        raise BlindAuditViolation("Audio decoding is forbidden in the DEEP-VOICE audit (D6)")
    patched = [(sf, "read"), (sf, "blocks"), (sf.SoundFile, "read")]
    try:
        import librosa
        patched += [(librosa, "load"), (librosa, "stream")]
    except ImportError:
        pass
    try:
        import torchaudio
        patched += [(torchaudio, "load")]
    except ImportError:
        pass
    saved = [(obj, name, getattr(obj, name)) for obj, name in patched]
    try:
        for obj, name, _ in saved:
            setattr(obj, name, _refuse)
        yield
    finally:
        for obj, name, orig in saved:
            setattr(obj, name, orig)


def parse_speakers(stem: str) -> dict:
    """Filenames encode source and target speakers, e.g. 'Obama-to-Biden' (publisher doc).

    Parsed generically; anything that does not match is recorded as-is for review.
    """
    m = re.match(r"^(?P<src>.+?)[-_ ]to[-_ ](?P<tgt>.+)$", stem, flags=re.IGNORECASE)
    if m:
        return {"src_speaker": m["src"].strip().lower(),
                "tgt_speaker": m["tgt"].strip().lower(), "name_pattern": "src-to-tgt"}
    base = re.sub(r"[-_ ]?(original|real)$", "", stem, flags=re.IGNORECASE)
    return {"src_speaker": base.strip().lower(), "tgt_speaker": None,
            "name_pattern": "single"}


def csv_schema(csv_path: Path) -> dict:
    """Schema + label counts only. Feature columns are never summarized."""
    header = pd.read_csv(csv_path, nrows=0)
    cols = list(header.columns)
    label_col = next((c for c in cols if c.strip().lower() in {"label", "class", "target"}), None)
    n_rows = sum(1 for _ in open(csv_path, "rb")) - 1
    out = {"file": csv_path.name, "sha256": sha256_file(csv_path), "n_rows": n_rows,
           "n_columns": len(cols), "columns": cols, "label_column": label_col}
    if label_col:
        out["label_counts"] = pd.read_csv(csv_path, usecols=[label_col])[label_col] \
            .value_counts().to_dict()
    out["usage_rule"] = ("Supplementary features from a different pipeline (1-s windows, "
                         "class-balanced by random sampling per publisher). NOT used for "
                         "any evaluation in this project.")
    return out


def run(root: Path, out: Path, revision: str) -> dict:
    root, out = Path(root), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    with decoding_forbidden():
        rows = []
        for p in find_audio_files(root):
            r = {"rel_path": p.relative_to(root).as_posix(), "label": infer_label(p, root),
                 "ext": p.suffix.lower(), "size_bytes": p.stat().st_size,
                 "sha256_bytes": sha256_file(p)}
            r.update(header_info(p))
            r.update(parse_speakers(p.stem))
            rows.append(r)
        inv = pd.DataFrame(rows)
        csvs = [csv_schema(c) for c in sorted(root.rglob("*.csv"))]
        other = sorted({p.suffix.lower() or "<none>" for p in root.rglob("*")
                        if p.is_file() and p.suffix.lower() not in {".csv", *inv.ext.unique()}})

    dur = inv.groupby("label")["duration_s"].agg(["count", "min", "median", "max", "sum"])
    report = {
        "dataset": "DEEP-VOICE", "root": str(root), "revision": revision,
        "attestation": ATTESTATION,
        "files": len(inv), "by_label": inv["label"].value_counts().to_dict(),
        "header_failures": int((~inv["header_ok"]).sum()),
        "ext": inv["ext"].value_counts().to_dict(),
        "samplerates_by_label": {str(k): int(v) for k, v in
                                 inv.groupby(["label", "samplerate"]).size().items()},
        "channels_by_label": {str(k): int(v) for k, v in
                              inv.groupby(["label", "channels"]).size().items()},
        "total_seconds_by_label": dur["sum"].round(3).to_dict(),
        "total_hours_by_label": (dur["sum"] / 3600).round(3).to_dict(),
        "n_2s_windows_by_label_if_nonoverlapping": (inv.groupby("label")["duration_s"]
            .apply(lambda d: int((d // 2).sum())).to_dict()),
        "source_speakers": sorted(inv["src_speaker"].dropna().unique().tolist()),
        "target_speakers": sorted(inv["tgt_speaker"].dropna().unique().tolist()),
        "unparsed_name_patterns": int((inv["name_pattern"] == "single").sum()),
        "exact_duplicate_files": int(inv["sha256_bytes"].duplicated(keep=False).sum()),
        "csv_files": csvs, "other_file_types": other,
    }
    inv.to_csv(out / "deepvoice_inventory.csv", index=False)
    write_json(report, out / "deepvoice_summary.json")
    md = ["# DEEP-VOICE — metadata-only audit", f"> {ATTESTATION}",
          f"\nRevision: `{revision}` · files: {len(inv)} · by label: {report['by_label']}",
          "\n## Duration by label (header-derived, seconds)", df_to_md(dur.reset_index()),
          "\n## Files", df_to_md(inv[["rel_path", "label", "samplerate", "channels",
                                      "duration_s", "src_speaker", "tgt_speaker"]]),
          f"\nWindows (2 s, non-overlapping) if D5 is adopted: "
          f"{report['n_2s_windows_by_label_if_nonoverlapping']}",
          "\n## CSV files (schema only)"]
    md += [f"- `{c['file']}`: {c['n_rows']} rows × {c['n_columns']} cols; label counts "
           f"{c.get('label_counts')} — {c['usage_rule']}" for c in csvs] or ["_none_"]
    (out / "deepvoice_summary.md").write_text("\n".join(md), encoding="utf-8")
    print(f"DEEP-VOICE metadata audit done: {len(inv)} files -> {out}")
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--revision", required=True, help="Kaggle dataset version number")
    a = ap.parse_args()
    if not a.revision.strip():
        raise AuditError("--revision must not be empty")
    run(a.root, a.out, a.revision)


if __name__ == "__main__":
    main()
