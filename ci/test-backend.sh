#!/usr/bin/env bash
# Stage "Unit tests / Backend": ruff, mypy and pytest inside a container.
source "$(dirname "$0")/lib.sh"
run_tests backend-test backend
