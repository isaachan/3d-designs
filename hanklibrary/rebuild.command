#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=${0:A:h}
cd "$SCRIPT_DIR"

if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python generate_plaques.py

echo ""
echo "完成：模型位于 $SCRIPT_DIR/generated/EN 和 $SCRIPT_DIR/generated/CN"
