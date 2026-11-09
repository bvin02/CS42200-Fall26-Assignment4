# CS 422 - Assignment 4

Bhavin Gupta
Repository: https://github.com/bvin02/CS42200-Fall26-Assignment4

This project solves maximum concurrent flow and network design with the Gurobi
Python API. It jointly selects directed unit-capacity links and splittable
routing. Each node has exactly `d` outgoing and `d` incoming links. The uniform
traffic case works for any `1 <= d < n`; the arbitrary-matrix case covers the
8-node, degree-4 hose set in the assignment.

## Setup and run

Python 3.10+ and a working Gurobi license are required. The restricted license
bundled with the current `gurobipy` package is sufficient for the saved 8-node
examples (449 variables and 136 constraints).

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
./run.sh
```

`run.sh` runs the tests, solves five examples, independently checks the saved
solutions, and regenerates the report PDF. To optimize a different nonzero
8 x 8 hose matrix, put it in a JSON file and run:

```bash
.venv/bin/python experiment.py --matrix inputs/your_matrix.json \
  --degree 4 --output results/your_result.json
```

Input rows and columns must each total at most 4, with zero diagonal. The
all-zero matrix has unbounded scaling and is rejected. The solver reports
`is_proven_optimal`; if a time limit stops the solve early, the saved JSON keeps
the incumbent and objective bound and does not call it optimal.

## Files

- `experiment.py` - exact Gurobi formulation, CLI, and solution verification
- `inputs/` - two example hose matrices
- `tests/` - analytic and implementation checks
- `results/report.pdf` - single PDF for Brightspace submission
- `results/report.md` - report source with the proof and model equations
- `results/*.json` - solver output, graph edges, flows, status, and bounds
- `results/plots/topology_adjacency.png` - graph illustrations
- `render_report.py` - regenerates the report and figure

## Submit

Submit only `results/report.pdf` to Brightspace. Keep the repository accessible
for the code links in the report. The assignment also includes an oral exam.

AI assistance was used to draft and review the formulation, code, tests, and
report. I reviewed the mathematical model and am responsible for explaining it.
