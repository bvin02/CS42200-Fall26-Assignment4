"""Check saved solver certificates and independent analytic bounds."""

import json
from pathlib import Path

from experiment import verify_solution


ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "uniform_5_2.json": 2 / 3,
    "uniform_7_3.json": 2 / 3,
    "uniform_8_4.json": 0.7,
    "regular_hose_8_4.json": 1.0,
    "sparse_hose_8_4.json": 4.0,
}


def main() -> None:
    for filename, upper_bound in EXPECTED.items():
        result = json.loads((ROOT / "results" / filename).read_text())
        verify_solution(result)
        assert result["is_proven_optimal"] and result["status"] == "optimal"
        assert abs(result["lambda_value"] - upper_bound) < 1e-6
        assert abs(result["objective_bound"] - upper_bound) < 1e-6
        print(f"{filename}: lambda={result['lambda_value']:.6f}, "
              f"bound={result['objective_bound']:.6f}, edges={len(result['edges'])}, "
              "flow/degrees/capacities valid")


if __name__ == "__main__":
    main()
