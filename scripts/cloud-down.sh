#!/usr/bin/env bash
# ITC 531 — destroy everything the course created in your cloud account.
#
#   bash scripts/cloud-down.sh <yourprovider>
#
# Runs your adapter's destroy, then independently re-enumerates and fails if
# anything survived. "The destroy command exited 0" is not evidence; an empty
# enumerate is.
set -uo pipefail

# Runs from anywhere: resolve everything relative to this script, not to your
# current directory, so it resolves to this module's root wherever you unzipped it.
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1


ADAPTER="${1:-}"
[[ -n "${ADAPTER}" && "${ADAPTER}" != "local" ]] || { echo "Usage: bash scripts/cloud-down.sh <yourprovider>" >&2; exit 2; }

SH="adapters/${ADAPTER}.sh"; ENVF="adapters/${ADAPTER}.env"
[[ -f "${SH}" && -f "${ENVF}" ]] || { echo "adapter ${ADAPTER} incomplete" >&2; exit 2; }

set -a; source "${ENVF}"; set +a
source "${SH}"

echo "ITC 531 teardown — adapter=${ADAPTER} — $(date -u '+%Y-%m-%d %H:%M UTC')"
adapter_meta | sed 's/^/  /'
echo "---------------------------------------------------------------"
echo "About to destroy:"
adapter_enumerate 2>/dev/null | sed 's/^/  /' || echo "  (enumerate failed — continuing anyway)"
echo "---------------------------------------------------------------"

if [[ "${ITC531_ASSUME_YES:-}" != "1" ]]; then
  # Every real adapter carries `set -euo pipefail` from TEMPLATE.sh, and it is
  # still active in this process after `source "${SH}"` above. `read` returns
  # non-zero on EOF (a closed terminal, a script, a CI runner with no stdin),
  # and without the `|| reply=""` guard that non-zero status triggers errexit
  # right here -- silently exiting before the "Aborted. Nothing changed."
  # message and its exit 130 ever run. Nothing unsafe happened either way
  # (adapter_destroy is never reached), but the intended message did not fire.
  read -r -p "Destroy all of the above? [y/N] " reply || reply=""
  [[ "${reply}" =~ ^[Yy]$ ]] || { echo "Aborted. Nothing changed."; exit 130; }
fi

adapter_destroy || { echo "destroy reported a failure — re-running audit anyway"; }

echo "---------------------------------------------------------------"
echo "Verifying..."
RESIDUE="$(adapter_enumerate 2>&1 || true)"
if [[ -z "${RESIDUE//[[:space:]]/}" ]]; then
  echo "CLEAN. Nothing remains."
  echo
  echo "Save this output — it is the teardown evidence the final project requires."
  exit 0
fi

echo "RESIDUE REMAINS:"
echo "${RESIDUE}"
echo
cat <<'MSG'
Common causes, in the order they usually bite:

  * a bucket that still contains objects — a versioned bucket also has
    non-current versions and delete markers. app/ports/storage.py:empty_bucket()
    handles all three; call it from adapter_destroy.
  * a deletion-protection or prevent-destroy flag set at create time.
  * a final snapshot taken automatically on delete, which then persists and
    bills separately and is invisible to the thing that created it.
  * a resource in a region other than the one your adapter enumerates.
  * a dependency ordering problem — the network cannot go until the thing
    inside it has gone.

Fix adapter_destroy and run this again. Do not leave it here.
MSG
exit 1
