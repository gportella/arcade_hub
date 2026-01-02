#!/usr/bin/env bash
# Import all bundled puzzle sets into the Chess Pit database.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PUZZLES_DIR="${BACKEND_ROOT}/../puzzles"

if [[ ! -d "${PUZZLES_DIR}" ]]; then
  echo "[puzzles] Puzzle directory not found at ${PUZZLES_DIR}" >&2
  exit 1
fi

COMMAND_PREFIX=(poetry run python scripts/import_puzzles.py)

declare -a IMPORT_JOBS=(
  "${PUZZLES_DIR}/brakto_kopec.epd::medium::Bratko-Kopec"
  "${PUZZLES_DIR}/eigennmann_rapid_engine.epd::hard::Eigendmann-Rapid"
  "${PUZZLES_DIR}/Lc0_Sf_test_suite_tcec15.epd::expert::TCEC15-Lc0-SF"
  "${PUZZLES_DIR}/lct_2.epd::medium::LCT-II"
  "${PUZZLES_DIR}/wacknew.epd::hard::WackNew"
)

cd "${BACKEND_ROOT}"

for job in "${IMPORT_JOBS[@]}"; do
  file="${job%%::*}"
  rest="${job#*::}"
  if [[ "${rest}" == "${job}" ]]; then
    echo "[puzzles] Invalid job definition: ${job}" >&2
    continue
  fi
  difficulty="${rest%%::*}"
  source="${rest#*::}"
  if [[ -z "${file}" || -z "${difficulty}" || "${source}" == "${rest}" ]]; then
    echo "[puzzles] Invalid job definition: ${job}" >&2
    continue
  fi
  if [[ ! -f "${file}" ]]; then
    echo "[puzzles] Skipping missing file ${file}" >&2
    continue
  fi
  echo "[puzzles] Importing $(basename "${file}") as ${difficulty} (source=${source})" >&2
  "${COMMAND_PREFIX[@]}" "${file}" --difficulty "${difficulty}" --source "${source}" "$@"
  echo "[puzzles] Completed ${file}" >&2
  echo >&2
done

echo "[puzzles] All imports finished." >&2
