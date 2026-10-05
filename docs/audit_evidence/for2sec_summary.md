# FoR-2sec audit — machine summary
Revision: `ff8c82c79e7bbefef811941bac9775c9328e9055` · files: 17721 · generated 2026-10-04T11:46:02.460742+00:00

## 1. Inventory
| split_dir/label | files |
|---|---|
| none/FAKE | 8921 |
| none/REAL | 8800 |

Header failures: 0 · decode failures: 0 · extensions: {'.wav': 17721}

## 2. Format by label
| samplerate | channels | subtype | FAKE | REAL |
|---|---|---|---|---|
| 16000 | 1 | PCM_16 | 8921 | 8800 |

## 3. Duration by label (s)
| label | count | min | 1% | 50% | 99% | max | mean |
|---|---|---|---|---|---|---|---|
| FAKE | 8921 | 2 | 2 | 2 | 2 | 2 | 2 |
| REAL | 8800 | 2 | 2 | 2 | 2 | 2 | 2 |

Clips outside 2.0 s ± 50 ms: 0

## 4. Shortcut screen — numeric (univariate separability AUC)
| feature | separability_auc | median_REAL | median_FAKE | flag |
|---|---|---|---|---|
| rms_dbfs | 0.6976 | -16.68 | -15.05 |  |
| bw99_hz | 0.6561 | 5074 | 3264 |  |
| dc_offset | 0.6352 | -1.163e-06 | 3.734e-05 |  |
| clip_frac | 0.6175 | 3.125e-05 | 3.125e-05 |  |
| silence_frac | 0.6124 | 0.01 | 0.03 |  |
| peak_dbfs | 0.6028 | -0.0002651 | -0.0002651 |  |
| trail_silence_ms | 0.5037 | 0 | 0 |  |
| duration_s | 0.5 | 2 | 2 |  |
| channels | 0.5 | 1 | 1 |  |
| samplerate | 0.5 | 16000 | 16000 |  |
| size_bytes | 0.5 | 64044 | 64044 |  |
| lead_silence_ms | 0.5 | 0 | 0 |  |

## 5. Shortcut screen — categorical values ≥ purity threshold
| feature | value | n | majority_label | purity |
|---|---|---|---|---|
| filename_signature | file#.mp#.wav_#k.wav_norm.wav_mono.wav_silence.wav_#sec | 7592 | FAKE | 1 |

## 6. Filename tokens (top 30 by frequency)
| token | n | frac_FAKE | label_pure |
|---|---|---|---|
| 2sec | 17721 | 0.5034 | False |
| 16k | 17721 | 0.5034 | False |
| wav | 17721 | 0.5034 | False |
| silence | 17721 | 0.5034 | False |
| norm | 17721 | 0.5034 | False |
| mono | 17721 | 0.5034 | False |
| mp3 | 7592 | 1 | True |
| file788 | 3 | 0.6667 | False |
| file963 | 3 | 0.6667 | False |
| file1102 | 3 | 0.6667 | False |
| file2198 | 3 | 0.6667 | False |
| file1631 | 3 | 0.6667 | False |
| file1684 | 3 | 0.6667 | False |
| file563 | 3 | 0.6667 | False |
| file1452 | 3 | 0.6667 | False |
| file2219 | 3 | 0.6667 | False |
| file257 | 3 | 0.6667 | False |
| file583 | 3 | 0.6667 | False |
| file1305 | 3 | 0.6667 | False |
| file478 | 3 | 0.6667 | False |
| file1204 | 3 | 0.6667 | False |
| file727 | 3 | 0.6667 | False |
| file1422 | 3 | 0.6667 | False |
| file1901 | 3 | 0.6667 | False |
| file113 | 3 | 0.6667 | False |
| file2185 | 3 | 0.6667 | False |
| file88 | 3 | 0.6667 | False |
| file410 | 3 | 0.6667 | False |
| file1133 | 3 | 0.6667 | False |
| file932 | 3 | 0.6667 | False |

## 7. Exact duplicates
| key | groups | files_in_groups | cross_label_groups | cross_split_groups |
|---|---|---|---|---|
| bytes | 0 | 0 | 0 | 0 |
| decoded PCM | 0 | 0 | 0 | 0 |

## 8. Near-duplicates (log-mel fingerprint cosine)
| threshold | pairs | cross_label_pairs | cross_split_pairs | n_groups | multi_file_groups | largest_group | largest_group_pct | d14_pass | d14_sanity_pass | d14_eligible |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.9 | 181 | 0 | 0 | 17579 | 112 | 13 | 0.0734 | True | True | True |
| 0.95 | 98 | 0 | 0 | 17634 | 82 | 6 | 0.0339 | True | True | True |
| 0.98 | 91 | 0 | 0 | 17640 | 77 | 6 | 0.0339 | True | True | True |

_Groups are transitive (connected components). largest_group_pct is % of decodable clips; d14_pass = largest_group_pct ≤ 5.0% (D14 chaining check)._

**D14 selected threshold: 0.95** (candidates in order: (0.95, 0.98), else pcm_hash_only)

_d14_eligible = d14_pass AND d14_sanity_pass (every exact-PCM-duplicate pair has similarity ≥ the threshold)._

D14 sanity — exact-PCM-duplicate pairs: {'pairs': 0, 'pairs_without_fingerprint': 0, 'min_sim': None}

D14 sanity check passed at all thresholds.

Max-sim quantiles: {'REAL': {0.5: 0.7301, 0.9: 0.819, 0.99: 1.0, 1.0: 1.0}, 'FAKE': {0.5: 0.7416, 0.9: 0.8003, 0.99: 0.8798, 1.0: 1.0}}

_Limitation: aligned fingerprints do not detect time-shifted overlapping excerpts of the same source recording._

## 9. Requires human review (not automatable)
- Speaker / source-recording metadata: inspect §6 tokens and the dataset card.
- Generator (TTS engine) metadata: inspect §6 tokens and the dataset card.
- License and redistribution terms.