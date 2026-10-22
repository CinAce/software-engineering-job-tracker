# CI Pipeline OIDC Configuration

https://github.com/CinAce/software-engineering-job-tracker/actions/runs/39177991451 

## Workflow Excerpt
yaml
build:
needs: test
runs-on: ubuntu-latest
timeout-minutes: 15

permissions:
      contents: read
      packages: write
      id-token: write

    steps:
      - uses: actions/checkout@v5

      - name: Google Cloud login
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        id: google_auth
        uses: google-github-actions/auth@v3
        with:
          workload_identity_provider: projects/284041991449/locations/global/workloadIdentityPools/m7-github/providers/job-tracker
          service_account: m7-github-ci@itc531-module7.iam.gserviceaccount.com
          token_format: access_token
          create_credentials_file: false

## Subject Condition
The subject condition configured at the GCP Workload Identity provider to restrict access to this specific repository is:
`attribute.repository == "CinAce/software-engineering-job-tracker"`
