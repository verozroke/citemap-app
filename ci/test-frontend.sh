#!/usr/bin/env bash
# Stage "Unit tests / Frontend": oxlint, tsc and Vitest inside a container.
source "$(dirname "$0")/lib.sh"
run_tests frontend-test frontend
