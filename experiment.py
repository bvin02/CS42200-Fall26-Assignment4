"""Exact topology design for CS 422 Assignment 4.

The graph is directed: x[i,j] represents one unit-capacity link i -> j.
Each flow commodity is indexed by its destination. This is equivalent to
source-destination multicommodity flow because a destination commodity can be
decomposed into paths from its individual injection nodes to that destination.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import gurobipy as gp
from gurobipy import GRB


def uniform_matrix(n: int, d: int) -> list[list[float]]:
    if not 1 <= d < n:
        raise ValueError("Require 1 <= d < n")
    return [[0.0 if i == j else d / (n - 1) for j in range(n)] for i in range(n)]


def validate_matrix(matrix: list[list[float]], d: int, hose: bool = True) -> int:
    n = len(matrix)
    if n < 2 or not 1 <= d < n or any(len(row) != n for row in matrix):
        raise ValueError("Matrix must be square and require 1 <= d < n")
    for i in range(n):
        for j in range(n):
            value = matrix[i][j]
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError("Demands must be finite, nonnegative numbers")
            if i == j and value != 0:
                raise ValueError("Diagonal demands must be zero")
    if sum(map(sum, matrix)) <= 0:
        raise ValueError("The zero matrix has unbounded scaling; give a nonzero demand")
    if hose:
        for i in range(n):
            if sum(matrix[i]) > d + 1e-9 or sum(matrix[j][i] for j in range(n)) > d + 1e-9:
                raise ValueError("Each row and column total must be at most d")
    return n


def build_model(matrix: list[list[float]], d: int, hose: bool = True):
    """Return the exact mixed integer linear program and its variables."""
    n = validate_matrix(matrix, d, hose)
    nodes = range(n)
    arcs = [(i, j) for i in nodes for j in nodes if i != j]
    # For destination t, no flow needs to leave t. Circulations can be removed.
    flow_keys = [(t, i, j) for t in nodes for i, j in arcs if i != t]
    model = gp.Model("maximum_concurrent_flow_topology")
    x = model.addVars(arcs, vtype=GRB.BINARY, name="link")
    f = model.addVars(flow_keys, lb=0.0, name="flow_to")
    lam = model.addVar(lb=0.0, name="lambda")

    for i in nodes:
        model.addConstr(gp.quicksum(x[i, j] for j in nodes if j != i) == d,
                        name=f"out_degree_{i}")
        model.addConstr(gp.quicksum(x[j, i] for j in nodes if j != i) == d,
                        name=f"in_degree_{i}")

    for i, j in arcs:
        model.addConstr(gp.quicksum(f[t, i, j] for t in nodes if t != i) <= x[i, j],
                        name=f"capacity_{i}_{j}")

    for t in nodes:
        for i in nodes:
            incoming = gp.quicksum(f[t, k, i] for k in nodes if k != i and k != t)
            if i == t:
                model.addConstr(incoming == lam * sum(matrix[s][t] for s in nodes),
                                name=f"sink_{t}")
            else:
                outgoing = gp.quicksum(f[t, i, j] for j in nodes if j != i)
                model.addConstr(outgoing - incoming == lam * matrix[i][t],
                                name=f"balance_{i}_{t}")

    model.setObjective(lam, GRB.MAXIMIZE)
    return model, x, f, lam


def solve(matrix: list[list[float]], d: int, *, time_limit: float | None = None,
          threads: int = 4, verbose: bool = False, hose: bool = True) -> dict:
    """Optimize topology and routing together; include bound if interrupted."""
    model, x, f, lam = build_model(matrix, d, hose)
    n = len(matrix)
    model.Params.OutputFlag = int(verbose)
    model.Params.Seed = 422
    model.Params.Threads = threads
    model.Params.MIPGap = 0.0
    if time_limit is not None:
        model.Params.TimeLimit = time_limit
    model.optimize()

    status = model.Status
    result = {
        "n": n,
        "d": d,
        "matrix": matrix,
        "status": "optimal" if status == GRB.OPTIMAL else "time_limit" if status == GRB.TIME_LIMIT else str(status),
        "is_proven_optimal": status == GRB.OPTIMAL,
        "runtime_seconds": model.Runtime,
        "model_variables": model.NumVars,
        "model_constraints": model.NumConstrs,
    }
    if model.SolCount == 0:
        result["objective_bound"] = model.ObjBound if status in (GRB.TIME_LIMIT, GRB.INTERRUPTED) else None
        return result

    result.update(
        lambda_value=lam.X,
        objective_bound=model.ObjBound,
        relative_gap=model.MIPGap,
        edges=[[i, j] for i, j in x.keys() if x[i, j].X > 0.5],
        flows=[{"destination": t, "from": i, "to": j, "amount": f[t, i, j].X}
               for t, i, j in f.keys() if f[t, i, j].X > 1e-10],
    )
    verify_solution(result)
    return result


def verify_solution(result: dict, tol: float = 1e-5) -> None:
    """Independently recheck saved degree, capacity, and flow balance values."""
    n, d, matrix = result["n"], result["d"], result["matrix"]
    edges = {tuple(e) for e in result["edges"]}
    assert len(edges) == n * d
    for i in range(n):
        assert sum(a == i for a, b in edges) == d
        assert sum(b == i for a, b in edges) == d
    load = {(i, j): 0.0 for i, j in edges}
    balance = [[0.0] * n for _ in range(n)]  # [destination][node]: out - in
    for item in result["flows"]:
        t, i, j, amount = item["destination"], item["from"], item["to"], item["amount"]
        assert i != j and i != t and amount >= -tol
        if (i, j) in edges:
            load[i, j] += amount
        else:
            # Gurobi's feasibility tolerance may leave a tiny value on a
            # numerically zero arc in a time-limited incumbent.
            assert amount <= tol
        balance[t][i] += amount
        balance[t][j] -= amount
    assert all(value <= 1 + tol for value in load.values())
    lam = result["lambda_value"]
    for t in range(n):
        for i in range(n):
            target = -lam * sum(matrix[s][t] for s in range(n)) if i == t else lam * matrix[i][t]
            assert abs(balance[t][i] - target) <= tol


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, help="JSON file containing an n x n demand matrix")
    parser.add_argument("--uniform", nargs=2, type=int, metavar=("N", "D"))
    parser.add_argument("--degree", type=int, default=4, help="degree for a JSON matrix (default: 4)")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--time-limit", type=float, help="seconds; an incomplete run reports its bound")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    if (args.matrix is None) == (args.uniform is None):
        parser.error("Supply exactly one of --matrix or --uniform")
    matrix, d = (uniform_matrix(*args.uniform), args.uniform[1]) if args.uniform else (
        json.loads(args.matrix.read_text()), args.degree)
    result = solve(matrix, d, time_limit=args.time_limit, threads=args.threads,
                   verbose=args.verbose)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"status={result['status']} lambda={result.get('lambda_value')} "
          f"upper_bound={result.get('objective_bound')} output={args.output}")


if __name__ == "__main__":
    main()
