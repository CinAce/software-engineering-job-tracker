#!/usr/bin/env bash
# =============================================================================
# ITC 531 — Provider adapter template
#
# THIS FILE IS YOUR WORK. Copy it to adapters/<yourprovider>.sh and implement the
# five functions below using your chosen provider's CLI or API.
#
# It is the primary artifact for SLO 3 ("develop scripts to assist in the
# management and automation of current cloud platform solutions"). The course
# deliberately does not write it for you, because the whole point is that you
# can automate a platform you selected yourself against a stated contract.
#
# The course scripts (cloud-verify / cloud-audit / cloud-down) source this file
# and call these functions. They never call a provider directly.
#
# RULES
#   1. Every function must be safe to run twice.
#   2. adapter_destroy must remove everything adapter_deploy created. If you
#      cannot destroy it, do not create it.
#   3. Print to stdout. Return 0 for success, non-zero for failure.
#   4. Never echo a secret. `set -x` is not your friend here.
#   5. Read configuration from adapters/<yourprovider>.env. No literals.
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# adapter_meta — who you are targeting and what you claim it does.
# Printed by every course script so your evidence is self-describing.
# -----------------------------------------------------------------------------
adapter_meta() {
  cat <<'META'
provider:        <name>
region:          <region or "n/a">
compute service: <the thing that runs your OCI image>
storage service: <the S3-compatible endpoint>
auth model:      <"OIDC federation" or "scoped API token">
contract check:  <date you last verified C1-C6>
META
}

# -----------------------------------------------------------------------------
# C1-C6: adapter_verify
#
# Prove the target satisfies the capability contract, WITHOUT creating anything
# that costs money. Read-only calls only. This is the Module 6 gate.
#
# Required checks:
#   C1  the container service exists and you are authenticated to it
#   C2  the S3-compatible endpoint answers a signed list-buckets
#   C3  the credential in use is NOT account-wide (print its scope)
#   C4  an enumerate command exists and returns (even if empty)
#   C5  a spend alert is configured — print its threshold
#   C6  print the current published free allowance or expected term cost
# -----------------------------------------------------------------------------
adapter_verify() {
  echo "C1 compute      : NOT IMPLEMENTED"; return 1
  echo "C2 storage      : NOT IMPLEMENTED"
  echo "C3 credential   : NOT IMPLEMENTED"
  echo "C4 enumerate    : NOT IMPLEMENTED"
  echo "C5 spend alert  : NOT IMPLEMENTED"
  echo "C6 cost model   : NOT IMPLEMENTED"
}

# -----------------------------------------------------------------------------
# adapter_deploy — push the image and run it. Must print the resulting HTTPS URL
# on the last line of stdout, and nothing else on that line.
#
# It must be idempotent: running it twice updates the running service rather
# than creating a second one.
# -----------------------------------------------------------------------------
adapter_deploy() {
  echo "NOT IMPLEMENTED" >&2; return 1
}

# -----------------------------------------------------------------------------
# adapter_enumerate — list everything that exists in the account, one resource
# per line, in the form:   <type>  <identifier>  <state>
#
# `bash scripts/cloud-audit.sh <yourprovider>` treats ANY output as a failure at teardown time, so this
# must be complete. An adapter that under-reports is worse than none: it is how
# a student ends the term believing they cleaned up when they did not.
# -----------------------------------------------------------------------------
adapter_enumerate() {
  echo "NOT IMPLEMENTED" >&2; return 1
}

# -----------------------------------------------------------------------------
# adapter_destroy — remove everything adapter_deploy created, then verify by
# calling adapter_enumerate and failing if anything remains.
#
# Object storage note: a bucket delete fails while objects remain, and on a
# versioned bucket "remove the objects" also means the non-current versions AND
# the delete markers. app/ports/storage.py:empty_bucket() does this correctly —
# call it rather than reimplementing it.
# -----------------------------------------------------------------------------
adapter_destroy() {
  echo "NOT IMPLEMENTED" >&2; return 1
}

# =============================================================================
# ILLUSTRATIVE FRAGMENTS
#
# Three shapes, so you can see that the pattern is provider-SHAPED rather than
# provider-SPECIFIC. These were syntactically current on 2026-07-28. Treat them
# as a starting point to check against today's documentation, NOT as answers.
# The course does not endorse or require any of these.
#
# --- shape A: a CLI with an explicit deploy verb -----------------------------
# adapter_deploy() {
#   "$CLI" auth login --token "$PROVIDER_TOKEN" >/dev/null
#   "$CLI" image push "$IMAGE_REF"
#   "$CLI" service update "$SERVICE_NAME" --image "$IMAGE_REF" --env-file "$ENV_FILE"
#   "$CLI" service describe "$SERVICE_NAME" --format '{{.URL}}'   # last line = URL
# }
#
# --- shape B: a registry push plus a declarative apply ------------------------
# adapter_deploy() {
#   docker push "$IMAGE_REF"
#   "$CLI" apply -f infra/service.yaml
#   "$CLI" get service "$SERVICE_NAME" -o jsonpath='{.status.url}'
# }
#
# --- shape C: OpenTofu all the way ------------------------------------------
# adapter_deploy() {
#   tofu -chdir=infra/tofu init -input=false
#   tofu -chdir=infra/tofu apply -auto-approve -var "image=$IMAGE_REF"
#   tofu -chdir=infra/tofu output -raw service_url
# }
# adapter_destroy() {
#   tofu -chdir=infra/tofu destroy -auto-approve
#   adapter_enumerate | tee /dev/stderr | grep -q . && { echo "residue remains"; return 1; }
#   return 0
# }
# =============================================================================
