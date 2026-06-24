"""Generate the bundled sample artifacts the dashboard reads.

This depends on the simulator and benchmark repos (the ``generate`` optional
dependency group). Running it refreshes ``data/sample_runs/`` so the dashboard
has realistic data to display without the user re-running any simulations.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "data" / "sample_runs"


def generate(out_dir: str | Path = DEFAULT_OUT, *, shots: int = 20_000, seed: int = 2026) -> None:
    """Generate threshold, benchmark and syndrome artifacts into ``out_dir``."""
    # Imported lazily so the dashboard itself does not require the heavy deps.
    import numpy as np
    from decbench import run_benchmark
    from decbench.types import BenchmarkConfig
    from surfacecode import run_threshold_sweep
    from surfacecode.circuits import build_surface_code_circuit
    from surfacecode.sampling import sample_syndromes, syndrome_density
    from surfacecode.types import ExperimentConfig

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    distances = [3, 5, 7]
    error_rates = [0.005, 0.008, 0.01, 0.012, 0.015]

    threshold = run_threshold_sweep(distances=distances, error_rates=error_rates, shots=shots, seed=seed)
    (out_dir / "threshold.json").write_text(threshold.model_dump_json(indent=2), encoding="utf-8")

    benchmark = run_benchmark(
        BenchmarkConfig(
            decoders=["mwpm", "union_find", "bp"],
            distances=[3, 5],
            error_rates=[0.005, 0.008, 0.01, 0.012],
            shots=min(shots, 5_000),
            seed=seed,
        )
    )
    (out_dir / "benchmark.json").write_text(benchmark.model_dump_json(indent=2), encoding="utf-8")

    entries = []
    for distance in [3, 5]:
        for p in [0.005, 0.01, 0.02]:
            config = ExperimentConfig(distance=distance, rounds=distance, p=p, shots=shots, seed=seed)
            circuit = build_surface_code_circuit(config)
            sample = sample_syndromes(circuit, shots=shots, seed=seed)
            density = syndrome_density(sample)
            entries.append(
                {
                    "distance": distance,
                    "p": p,
                    "rounds": distance,
                    "num_detectors": int(density.shape[0]),
                    "mean_firing": float(np.mean(density)),
                    "density": [float(value) for value in density],
                }
            )
    (out_dir / "syndrome.json").write_text(json.dumps({"entries": entries}, indent=2), encoding="utf-8")
    print(f"wrote threshold.json, benchmark.json, syndrome.json to {out_dir}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=str, default=str(DEFAULT_OUT))
    parser.add_argument("--shots", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args(argv)
    generate(args.out, shots=args.shots, seed=args.seed)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
