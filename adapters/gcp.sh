#!/usr/bin/env bash
# ITC531 Module 7 & 8: Google Cloud Run + Google Cloud Storage adapter.
# Source after adapters/gcp.env. Every provider operation targets GCP_PROJECT.
set -euo pipefail

: "${GCP_PROJECT:?GCP_PROJECT must be set}"
: "${GCP_REGION:?GCP_REGION must be set}"
: "${SERVICE_NAME:?SERVICE_NAME must be set}"
: "${IMAGE_REF:?IMAGE_REF must be set}"
: "${HMAC_CREDENTIAL_FILE:?HMAC_CREDENTIAL_FILE must be set}"

# Impersonation rule removed per earlier teardown lockout fix
_gcp() { gcloud --project="$GCP_PROJECT" "$@"; }

adapter_meta() {
  cat <<META
provider:        Google Cloud (GCP)
project:         ${GCP_PROJECT}
region:          ${GCP_REGION}
compute service: Cloud Run
storage service: Cloud Storage XML API (SigV4)
auth model:      gcloud user OAuth with project IAM; project-scoped HMAC service account
contract check:  $(date -u +%Y-%m-%d)
META
}

adapter_enumerate() {
  local run_json hmac_json sa_json policy_json
  run_json="$(_gcp run services list --region "$GCP_REGION" --format=json)" || return 1
  printf '%s' "$run_json" | python3 -c '
import json,os,sys
name=os.environ["SERVICE_NAME"]
for x in json.load(sys.stdin):
    n=x.get("metadata",{}).get("name",x.get("name",""))
    if n.split("/")[-1]==name:
        state="READY" if any(c.get("type")=="Ready" and c.get("status")=="True" for c in x.get("status",{}).get("conditions",[])) else "PRESENT"
        print("cloud-run  %s  %s"%(n,state))
' || return 1

  hmac_json="$(_gcp storage hmac list --format=json)" || return 1
  printf '%s' "$hmac_json" | python3 -c '
import json,sys,os
for x in json.load(sys.stdin):
    x=x.get("metadata",x)
    if x.get("serviceAccountEmail")==os.environ["SERVICE_ACCOUNT"] and x.get("state") != "DELETED":
        print("hmac-key  %s  %s"%(x.get("accessId","unknown"),x.get("state","PRESENT")))
' || return 1

  sa_json="$(_gcp iam service-accounts list --format=json)" || return 1
  printf '%s' "$sa_json" | python3 -c '
import json,os,sys
email=os.environ["SERVICE_ACCOUNT"]
for x in json.load(sys.stdin):
    if x.get("email")==email:
        print("service-account  %s  PRESENT"%email)
' || return 1

  policy_json="$(_gcp projects get-iam-policy "$GCP_PROJECT" --format=json)" || return 1
  printf '%s' "$policy_json" | python3 -c '
import json,os,sys
member="serviceAccount:"+os.environ["SERVICE_ACCOUNT"]
for b in json.load(sys.stdin).get("bindings",[]):
    if member in b.get("members",[]):
        print("iam-binding  %s:%s  PRESENT"%(b.get("role","unknown"),member))
' || return 1

  if [[ -n "${S3_BUCKET:-}" ]]; then
    local bucket_json
    bucket_json="$(_gcp storage buckets list --format=json)" || return 1
    printf '%s' "$bucket_json" | python3 -c '
import json, os, sys
wanted = os.environ["S3_BUCKET"]
for item in json.load(sys.stdin):
    name = str(item.get("name") or item.get("id") or "").rsplit("/", 1)[-1]
    if name == wanted:
        print(f"gcs-bucket  gs://{wanted}  PRESENT")
' || return 1
  fi

  local secrets_json
  secrets_json="$(_gcp secrets list --format=json)" || return 1
  printf '%s' "$secrets_json" | python3 -c '
import json, sys
wanted = {
    "itc531-jobtracker-jwt",
    "itc531-jobtracker-hmac-id",
    "itc531-jobtracker-hmac-secret",
}
for item in json.load(sys.stdin):
    name = item.get("name", "").rsplit("/", 1)[-1]
    if name in wanted:
        print("secret-manager  %s  PRESENT" % name)
' || return 1
}

adapter_verify() {
  local failed=0 output billing budget_json role_json
  if _gcp run services list --region "$GCP_REGION" --format=json >/dev/null; then
    echo "C1 compute      : OK — Cloud Run API authenticated; project=$GCP_PROJECT"
  else
    echo 'C1 compute      : FAIL — Cloud Run list failed'; failed=1
  fi

  if [[ -f "$HMAC_CREDENTIAL_FILE" ]] && python3 - "$HMAC_CREDENTIAL_FILE" <<'PY'
import json, sys, boto3
with open(sys.argv[1], encoding='utf-8') as fh:
    creds=json.load(fh)
client=boto3.client('s3', endpoint_url='https://storage.googleapis.com',
    region_name='auto', aws_access_key_id=creds['metadata']['accessId'],
    aws_secret_access_key=creds['secret'])
result=client.list_buckets()
assert result['ResponseMetadata']['HTTPStatusCode']==200
PY
  then
    echo 'C2 storage      : OK — signed SigV4 list-buckets HTTP 200'
  else
    echo 'C2 storage      : FAIL — HMAC SigV4 request failed'; failed=1
  fi

  if role_json="$(_gcp projects get-iam-policy "$GCP_PROJECT" --format=json)" && \
      printf '%s' "$role_json" | python3 -c '
import json,os,sys
p=json.load(sys.stdin); member="serviceAccount:"+os.environ["SERVICE_ACCOUNT"]
roles={b["role"] for b in p.get("bindings",[]) if member in b.get("members",[])}
sys.exit(0 if roles=={"roles/storage.bucketViewer"} else 1)
'; then
    echo "C3 credential   : OK — storage HMAC service account: roles/storage.bucketViewer on project $GCP_PROJECT"
  else
    echo 'C3 credential   : FAIL — dedicated storage service account not limited to expected project role'; failed=1
  fi

  if output="$(adapter_enumerate)"; then
    local count=0
    [[ -z "$output" ]] || count="$(printf '%s\n' "$output" | grep -c . || true)"
    echo "C4 enumerate    : OK — all configured resource categories readable ($count present)"
  else
    echo 'C4 enumerate    : FAIL — an enumeration request failed'; failed=1
  fi

  if billing="$(_gcp billing projects describe "$GCP_PROJECT" --format='value(billingAccountName)')" && \
     [[ -n "$billing" ]] && \
     budget_json="$(gcloud billing budgets list --billing-account="$billing" --format=json)" && \
     printf '%s' "$budget_json" | python3 -c '
import json,os,sys
from decimal import Decimal
expected=Decimal(os.environ["SPEND_ALERT_THRESHOLD"])
name=os.environ["BUDGET_NAME"]
for b in json.load(sys.stdin):
    a=b.get("amount",{}).get("specifiedAmount",{})
    value=Decimal(str(a.get("units",0)))+Decimal(str(a.get("nanos",0)))/Decimal(10**9)
    if b.get("displayName")==name and a.get("currencyCode")=="USD" and value==expected and b.get("thresholdRules"):
        sys.exit(0)
sys.exit(1)
'; then
    echo "C5 spend alert : OK — $BUDGET_NAME; USD $SPEND_ALERT_THRESHOLD configured"
  else
    echo 'C5 spend alert : FAIL — expected budget not found'; failed=1
  fi

  if [[ "$IMAGE_REF" != *:latest ]] && [[ "$MIN_INSTANCES" == "0" ]] && [[ "$MAX_INSTANCES" == "1" ]]; then
    echo "C6 cost model  : OK — Cloud Run free allowance (2M requests/month); 0 min instances"
  else
    echo 'C6 cost model  : FAIL — image or scale settings differ from cost model'; failed=1
  fi
  return "$failed"
}

adapter_deploy() {
  : "${DATABASE_URL:?DATABASE_URL must be set}"
  : "${S3_ENDPOINT_URL:?S3_ENDPOINT_URL must be set}"
  : "${S3_BUCKET:?S3_BUCKET must be set}"
  : "${S3_REGION:?S3_REGION must be set}"
  : "${AMQP_URL:?AMQP_URL must be set}"

  _gcp run deploy "$SERVICE_NAME" \
    --image "$IMAGE_REF" \
    --region "$GCP_REGION" \
    --service-account "$SERVICE_ACCOUNT" \
    --allow-unauthenticated \
    --port "$CONTAINER_PORT" \
    --min-instances "$MIN_INSTANCES" \
    --max-instances "$MAX_INSTANCES" \
    --cpu "$CPU" \
    --memory "$MEMORY" \
    --timeout "$TIMEOUT" \
    --set-env-vars "ENVIRONMENT=cloud,DATABASE_URL=$DATABASE_URL,S3_ENDPOINT_URL=$S3_ENDPOINT_URL,S3_PUBLIC_ENDPOINT_URL=$S3_ENDPOINT_URL,S3_BUCKET=$S3_BUCKET,S3_REGION=$S3_REGION,AMQP_URL=$AMQP_URL" \
    --set-secrets "JWT_SECRET=itc531-jobtracker-jwt:latest,AWS_ACCESS_KEY_ID=itc531-jobtracker-hmac-id:latest,AWS_SECRET_ACCESS_KEY=itc531-jobtracker-hmac-secret:latest" \
    --quiet >&2

  local url
  url="$(_gcp run services describe "$SERVICE_NAME" \
    --region "$GCP_REGION" \
    --format='value(status.url)')" || return 1

  [[ "$url" == https://* ]] || {
    echo "Deployment did not return an HTTPS URL" >&2
    return 1
  }

  printf '%s\n' "$url"
}

adapter_destroy() {
  local run_json hmac_json sa_json roles_json
  run_json="$(_gcp run services list --region "$GCP_REGION" --format=json)" || return 1
  if printf '%s' "$run_json" | python3 -c '
import json,os,sys
name=os.environ["SERVICE_NAME"]
sys.exit(0 if any(x.get("metadata",{}).get("name")==name or x.get("name","").split("/")[-1]==name for x in json.load(sys.stdin)) else 1)
'; then
    _gcp run services delete "$SERVICE_NAME" --region "$GCP_REGION" --quiet
  fi

  if [[ -n "${S3_BUCKET:-}" ]]; then
    local bucket_json
    bucket_json="$(_gcp storage buckets list --format=json)" || return 1
    if printf '%s' "$bucket_json" | python3 -c '
import json, os, sys
wanted = os.environ["S3_BUCKET"]
items = json.load(sys.stdin)
sys.exit(0 if any(
    str(x.get("name") or x.get("id") or "").rsplit("/", 1)[-1] == wanted
    for x in items
) else 1)
'; then
      _gcp storage rm --recursive "gs://$S3_BUCKET"
    fi
  fi

  local secrets_json secret_name
  secrets_json="$(_gcp secrets list --format=json)" || return 1

  for secret_name in itc531-jobtracker-jwt itc531-jobtracker-hmac-id itc531-jobtracker-hmac-secret
  do
    if printf '%s' "$secrets_json" | python3 -c '
import json, sys
wanted = sys.argv[1]
sys.exit(0 if any(
    x.get("name", "").rsplit("/", 1)[-1] == wanted
    for x in json.load(sys.stdin)
) else 1)
' "$secret_name"; then
      _gcp secrets delete "$secret_name" --quiet || return 1
    fi
  done

  hmac_json="$(_gcp storage hmac list --format=json)" || return 1
  local keyrows access state
  keyrows="$(printf '%s' "$hmac_json" | python3 -c '
import json,sys,os
for x in json.load(sys.stdin):
    x=x.get("metadata",x)
    if x.get("serviceAccountEmail")==os.environ["SERVICE_ACCOUNT"] and x.get("state")!="DELETED" and x.get("accessId"):
        print(x["accessId"]+" "+x.get("state","ACTIVE"))
')" || return 1
  while read -r access state; do
    [[ -n "$access" ]] || continue
    if [[ "$state" != INACTIVE ]]; then
      _gcp storage hmac update "$access" --deactivate --quiet
    fi
    _gcp storage hmac delete "$access" --quiet
  done <<< "$keyrows"

  roles_json="$(_gcp projects get-iam-policy "$GCP_PROJECT" --format=json)" || return 1
  local roles role
  roles="$(printf '%s' "$roles_json" | python3 -c '
import json,os,sys
member="serviceAccount:"+os.environ["SERVICE_ACCOUNT"]
for b in json.load(sys.stdin).get("bindings",[]):
    if member in b.get("members",[]): print(b["role"])
')" || return 1
  while IFS= read -r role; do
    [[ -n "$role" ]] || continue
    _gcp projects remove-iam-policy-binding "$GCP_PROJECT" \
      --member="serviceAccount:$SERVICE_ACCOUNT" --role="$role" --all --quiet >/dev/null
  done <<< "$roles"

  sa_json="$(_gcp iam service-accounts list --format=json)" || return 1
  if printf '%s' "$sa_json" | python3 -c '
import json,os,sys
email=os.environ["SERVICE_ACCOUNT"]
sys.exit(0 if any(x.get("email")==email for x in json.load(sys.stdin)) else 1)
'; then
    _gcp iam service-accounts delete "$SERVICE_ACCOUNT" --quiet
  fi

  local remaining
  remaining="$(adapter_enumerate)" || { echo 'Post-destroy enumeration failed' >&2; return 1; }
  if [[ -n "${remaining//[[:space:]]/}" ]]; then
    printf 'Resources remain:\n%s\n' "$remaining" >&2
    return 1
  fi
  rm -f -- "$HMAC_CREDENTIAL_FILE"
  echo 'Module 7 Cloud Run, temporary HMAC key, project IAM binding, and service account removed.'
}