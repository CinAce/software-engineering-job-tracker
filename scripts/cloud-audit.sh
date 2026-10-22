#!/usr/bin/env bash
# ITC 531 — cloud resource audit

set -uo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

ADAPTER="${1:-}"

[[ -n "${ADAPTER}" && "${ADAPTER}" != "local" ]] || {
  echo "Usage: bash scripts/cloud-audit.sh <yourprovider>" >&2
  exit 2
}

SH="adapters/${ADAPTER}.sh"
ENVF="adapters/${ADAPTER}.env"

[[ -f "${SH}" && -f "${ENVF}" ]] || {
  echo "adapter ${ADAPTER} incomplete" >&2
  exit 2
}

set -a
source "${ENVF}"
set +a

source "${SH}"

STAMP="$(date -u '+%Y-%m-%d %H:%M UTC')"

echo "ITC 531 cloud audit — adapter=${ADAPTER} — ${STAMP}"
adapter_meta | sed 's/^/  /'
echo "---------------------------------------------------------------"

OUT="$(adapter_enumerate 2>&1)" || {
  echo "enumerate failed:"
  echo "${OUT}"
  exit 1
}

if [[ -z "${OUT//[[:space:]]/}" ]]; then
  echo "CLEAN — no resources exist."
  echo "---------------------------------------------------------------"
  exit 0
fi

echo "${OUT}"
echo "---------------------------------------------------------------"

COUNT="$(printf '%s\n' "${OUT}" | grep -c . || true)"

echo "NOT CLEAN — ${COUNT} resource(s) exist."
echo
echo "If you are finished with them:   bash scripts/cloud-down.sh ${ADAPTER}"
echo "If you are mid-assignment that is fine — but check again when you finish."

exit 1
