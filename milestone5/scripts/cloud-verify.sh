#!/usr/bin/env bash
set -euo pipefail

PROVIDER="${1:-}"

if [[ "$PROVIDER" != "aws" ]]; then
  echo "Usage: bash scripts/cloud-verify.sh aws" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVIDENCE="$ROOT/members/adams5ma/evidence"

if [[ -f "$ROOT/adapters/aws.env" ]]; then
  set -a
  source "$ROOT/adapters/aws.env"
  set +a
fi

source "$ROOT/adapters/aws.sh"

echo "======================================"
echo "ITC531 Cloud Capability Verification"
echo "======================================"

adapter_meta
echo

if ! adapter_verify; then
  echo "CONTRACT NOT SATISFIED"
  exit 1
fi

echo
echo "Checking C3 supporting evidence..."

for file in \
  "$EVIDENCE/06-aws-iam-permissions.png" \
  "$EVIDENCE/06-aws-iam-policy.png"; do
  if [[ ! -s "$file" ]]; then
    echo "C3 FAIL: missing $file"
    exit 1
  fi
done

echo "C3: IAM screenshots present"
echo "C3: Policy scope must match the reviewed read-only policies"

echo
echo "Checking C6 supporting evidence..."

COST="$EVIDENCE/06-aws-cost-evidence.txt"

if [[ ! -s "$COST" ]]; then
  echo "C6 FAIL: cost evidence missing"
  exit 1
fi

if ! grep -q 'Estimated subtotal:' "$COST"; then
  echo "C6 FAIL: cost estimate missing"
  exit 1
fi

echo "C6: Cost estimate present"

echo
echo "======================================"
echo "VERIFICATION INCOMPLETE"
echo "C1: Deployment capability not yet proven"
echo "C3: IAM policy scope requires review"
echo "C4: Resource deletion capability not yet proven"
echo "C6: Full deployment cost estimate incomplete"
echo "======================================"
exit 1
