import json
import unittest
from pathlib import Path

from experiment import build_model, solve, uniform_matrix, validate_matrix, verify_solution


ROOT = Path(__file__).resolve().parents[1]


class TopologyTests(unittest.TestCase):
    def test_uniform_demand_is_hose_feasible(self):
        matrix = uniform_matrix(7, 3)
        self.assertEqual(validate_matrix(matrix, 3), 7)
        for i in range(7):
            self.assertAlmostEqual(sum(matrix[i]), 3)
            self.assertAlmostEqual(sum(row[i] for row in matrix), 3)

    def test_rejects_invalid_or_unbounded_inputs(self):
        with self.assertRaisesRegex(ValueError, "zero matrix"):
            validate_matrix([[0, 0], [0, 0]], 1)
        with self.assertRaisesRegex(ValueError, "row and column"):
            validate_matrix([[0, 5, 0], [0, 0, 0], [0, 0, 0]], 1)
        with self.assertRaisesRegex(ValueError, "Diagonal"):
            validate_matrix([[1, 0], [0, 0]], 1)

    def test_model_size_stays_under_restricted_license(self):
        model, *_ = build_model(uniform_matrix(8, 4), 4)
        model.update()
        self.assertEqual(model.NumVars, 449)
        self.assertEqual(model.NumConstrs, 136)

    def test_exact_uniform_small_instance(self):
        result = solve(uniform_matrix(7, 3), 3)
        self.assertTrue(result["is_proven_optimal"])
        self.assertAlmostEqual(result["lambda_value"], 2 / 3, places=7)
        self.assertAlmostEqual(result["objective_bound"], 2 / 3, places=7)
        verify_solution(result)

    def test_explicit_seven_node_construction(self):
        n = 7
        shifts = {1, 2, 4}
        paths = {3: [(1, 2), (2, 1)],
                 5: [(1, 4), (4, 1)],
                 6: [(2, 4), (4, 2)]}
        flow = {}
        for source in range(n):
            for offset in range(1, n):
                dest = (source + offset) % n
                if offset in shifts:
                    arcs = [(source, dest)]
                    amount = 1 / 3
                    for i, j in arcs:
                        flow[dest, i, j] = flow.get((dest, i, j), 0) + amount
                else:
                    for first, second in paths[offset]:
                        middle = (source + first) % n
                        for i, j in [(source, middle), (middle, dest)]:
                            flow[dest, i, j] = flow.get((dest, i, j), 0) + 1 / 6
        result = {
            "n": n, "d": 3, "matrix": uniform_matrix(n, 3), "lambda_value": 2 / 3,
            "edges": [[i, (i + shift) % n] for i in range(n) for shift in shifts],
            "flows": [{"destination": t, "from": i, "to": j, "amount": amount}
                      for (t, i, j), amount in flow.items()],
        }
        verify_solution(result, tol=1e-9)

    def test_full_hose_and_sparse_hose(self):
        for filename, expected in [("regular_hose_8_4.json", 1.0),
                                   ("sparse_hose_8_4.json", 4.0)]:
            matrix = json.loads((ROOT / "inputs" / filename).read_text())
            result = solve(matrix, 4)
            self.assertTrue(result["is_proven_optimal"])
            self.assertAlmostEqual(result["lambda_value"], expected, places=7)
            verify_solution(result)


if __name__ == "__main__":
    unittest.main()
