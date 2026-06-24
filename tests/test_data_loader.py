import json

from qecdash.data_loader import load_all, load_benchmark, load_syndrome, load_threshold


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_load_threshold(tmp_path):
    path = tmp_path / "threshold.json"
    _write(path, {
        "points": [
            {"distance": 3, "p": 0.01, "logical_error_rate": 0.05, "ci_low": 0.04,
             "ci_high": 0.06, "num_shots": 1000, "num_failures": 50},
        ],
        "threshold_estimate": 0.006,
    })
    frame, estimate = load_threshold(path)
    assert estimate == 0.006
    assert list(frame["distance"]) == [3]


def test_load_benchmark(tmp_path):
    path = tmp_path / "benchmark.json"
    _write(path, {"records": [
        {"decoder": "mwpm", "distance": 3, "p": 0.01, "rounds": 3, "shots": 1000,
         "num_failures": 40, "logical_error_rate": 0.04, "ci_low": 0.03, "ci_high": 0.05,
         "wall_seconds": 0.1, "microseconds_per_shot": 100.0, "peak_kib": 200.0},
    ]})
    frame = load_benchmark(path)
    assert frame.loc[0, "decoder"] == "mwpm"


def test_load_syndrome_explodes_density(tmp_path):
    path = tmp_path / "syndrome.json"
    _write(path, {"entries": [
        {"distance": 3, "p": 0.01, "rounds": 3, "num_detectors": 3,
         "mean_firing": 0.1, "density": [0.1, 0.2, 0.05]},
    ]})
    frame = load_syndrome(path)
    assert len(frame) == 3
    assert set(frame["detector"]) == {0, 1, 2}


def test_load_all_skips_missing(tmp_path):
    bundle = load_all(tmp_path)
    assert bundle == {}
