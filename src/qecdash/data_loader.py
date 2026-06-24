"""Load QEC run artifacts produced by the simulator/benchmark repos into frames.

The dashboard is intentionally decoupled from the simulators: it consumes JSON
artifacts written by ``surfacecode sweep``, ``decbench run`` and
``mldecoder compare``. This mirrors a production observability stack where the
dashboard reads metrics emitted by upstream jobs rather than recomputing them.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "sample_runs"


def _read_json(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_threshold(path: str | Path) -> tuple[pd.DataFrame, float | None]:
    """Load a threshold sweep artifact into a tidy frame plus the threshold estimate."""
    payload = _read_json(path)
    frame = pd.DataFrame(payload.get("points", []))
    return frame, payload.get("threshold_estimate")


def load_benchmark(path: str | Path) -> pd.DataFrame:
    """Load a decoder benchmark artifact (classical and/or ML) into a frame."""
    payload = _read_json(path)
    return pd.DataFrame(payload.get("records", []))


def load_syndrome(path: str | Path) -> pd.DataFrame:
    """Load a syndrome-statistics artifact into a long-form frame.

    Each entry carries a per-detector firing-probability vector; we explode it
    so each row is one detector at one (distance, p) operating point.
    """
    payload = _read_json(path)
    rows = []
    for entry in payload.get("entries", []):
        for detector_index, probability in enumerate(entry.get("density", [])):
            rows.append(
                {
                    "distance": entry["distance"],
                    "p": entry["p"],
                    "rounds": entry["rounds"],
                    "detector": detector_index,
                    "firing_probability": probability,
                }
            )
    return pd.DataFrame(rows)


def load_all(data_dir: str | Path = DEFAULT_DATA_DIR) -> dict[str, object]:
    """Load all bundled artifacts from ``data_dir``; missing files are skipped."""
    data_dir = Path(data_dir)
    bundle: dict[str, object] = {}
    threshold_path = data_dir / "threshold.json"
    benchmark_path = data_dir / "benchmark.json"
    syndrome_path = data_dir / "syndrome.json"
    if threshold_path.exists():
        frame, estimate = load_threshold(threshold_path)
        bundle["threshold"] = frame
        bundle["threshold_estimate"] = estimate
    if benchmark_path.exists():
        bundle["benchmark"] = load_benchmark(benchmark_path)
    if syndrome_path.exists():
        bundle["syndrome"] = load_syndrome(syndrome_path)
    return bundle
