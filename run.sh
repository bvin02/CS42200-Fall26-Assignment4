#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="${PYTHON:-.venv/bin/python}"
"$PYTHON" -m unittest discover -s tests -v
"$PYTHON" experiment.py --uniform 5 2 --output results/uniform_5_2.json
"$PYTHON" experiment.py --uniform 7 3 --output results/uniform_7_3.json
"$PYTHON" experiment.py --uniform 8 4 --output results/uniform_8_4.json
"$PYTHON" experiment.py --matrix inputs/regular_hose_8_4.json --output results/regular_hose_8_4.json
"$PYTHON" experiment.py --matrix inputs/sparse_hose_8_4.json --output results/sparse_hose_8_4.json
"$PYTHON" verify_results.py
"$PYTHON" render_report.py
