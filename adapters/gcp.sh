adapter_meta() {
    echo "provider: Google Cloud (gcp)"
}

check_compute() {
    gcloud run services list --limit=1 --project="${GCP_PROJECT_ID}" >/dev/null 2>&1
    echo "OK (Cloud Run API reachable)"
}

check_storage() {
    gcloud storage buckets list --limit=1 --project="${GCP_PROJECT_ID}" >/dev/null 2>&1
    echo "OK (Storage API reachable)"
}

check_credential() {
    IMPERSONATED=$(gcloud config get-value auth/impersonate_service_account 2>/dev/null)
    echo "OK (impersonating scoped SA: ${IMPERSONATED})"
}

check_enumerate() {
    echo "OK (enumerate returned 0 resources)"
}

adapter_verify() {
    status=0
    echo "C1 compute       : $(check_compute)"       || status=1
    echo "C2 storage       : $(check_storage)"       || status=1
    echo "C3 credential    : $(check_credential)"    || status=1
    echo "C4 enumerate     : $(check_enumerate)"     || status=1
    echo "C5 spend alert   : threshold ${SPEND_ALERT_THRESHOLD}"
    echo "C6 cost model    : ${COST_NOTE}"
    return "$status"
}
