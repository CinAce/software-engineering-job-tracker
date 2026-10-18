#!/usr/bin/env bash
# ITC 531 — capability contract check (C1-C6).
#
#   bash scripts/cloud-verify.sh <yourprovider>
#
# Reads only. Creates nothing. This is the Module 6 gate: you may not create a
# single cloud resource in this course until this passes and you have submitted
# its output.
set -uo pipefail

# Runs from anywhere: resolve everything relative to this script, not to your
# current directory, so it resolves to this module's root wherever you unzipped it.
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1


ADAPTER="${1:-}"
if [[ -z "${ADAPTER}" || "${ADAPTER}" == "local" ]]; then
  cat >&2 <<'MSG'
Usage: bash scripts/cloud-verify.sh <yourprovider>

There is no default provider in this course, and 'local' is not a cloud target.
Write adapters/<yourprovider>.sh from adapters/TEMPLATE.sh first (module 6).
MSG
  exit 2
fi

SH="adapters/${ADAPTER}.sh"
ENVF="adapters/${ADAPTER}.env"
[[ -f "${SH}"   ]] || { echo "missing ${SH} — copy adapters/TEMPLATE.sh and implement it" >&2; exit 2; }
[[ -f "${ENVF}" ]] || { echo "missing ${ENVF} — copy adapters/TEMPLATE.env and fill it in" >&2; exit 2; }

set -a; source "${ENVF}"; set +a
source "${SH}"

echo "================================================================"
echo "ITC 531 capability contract check"
echo "adapter : ${ADAPTER}"
echo "date    : $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "================================================================"
adapter_meta
echo "----------------------------------------------------------------"

if adapter_verify; then
  RESULT=0
else
  RESULT=1
fi

echo "----------------------------------------------------------------"
# Local-side checks the adapter cannot fudge.
if [[ "${IMAGE_REF:-}" == *:latest ]]; then
  echo "LOCAL FAIL: IMAGE_REF ends in ':latest'. Deploy a specific digest or git SHA."
  RESULT=1
fi
if [[ "${JWT_SECRET:-}" == *local-development-secret* ]]; then
  echo "LOCAL FAIL: JWT_SECRET is still the local development value."
  RESULT=1
fi
if [[ -z "${SPEND_ALERT_THRESHOLD:-}" ]]; then
  echo "LOCAL FAIL: SPEND_ALERT_THRESHOLD is unset. C5 requires a configured alert."
  RESULT=1
fi
if [[ -d .git ]] && ! git check-ignore -q "${ENVF}"; then
  echo "LOCAL FAIL: ${ENVF} is not gitignored."
  RESULT=1
fi

echo "================================================================"
if (( RESULT == 0 )); then
  echo "CONTRACT SATISFIED. You may now create resources. Submit this output."
else
  echo "CONTRACT NOT SATISFIED. Do not create anything yet."
  echo "If your provider genuinely cannot meet a clause, that is a finding, not a"
  echo "failure — write it up and talk to the instructor about Route B."
fi
exit "${RESULT}"
