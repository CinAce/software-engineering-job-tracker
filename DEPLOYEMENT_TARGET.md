# Team Deployment Target Decision (Milestone 5, Part 7)

## 1. Selected Deployment Target
* **Primary Target Provider:** Amazon Web Services (AWS)
* **Lead Member / Adapter Source:** `members/adams5ma/`
* **Adapter Verification:** Satisfied via `adapters/aws.sh` and verified in Milestone 5 evidence.

---

## 2. Capability Assessment (C1–C6 Analysis)

The team evaluated both AWS and GCP adapters against the six course capability contracts:

* **C1: Isolated Provisioning & Authentication:** AWS IAM user and access keys are provisioned with least-privilege scoping, validated via CLI and credentials loaded from environment variables (`adapters/aws.env`).
* **C2: Compute & Container Runtime:** Supported via AWS container services (ECS/App Runner/EC2) capable of driving the application containers defined in `compose.yml`.
* **C3: Principle of Least Privilege (IAM Scope):** IAM permissions are scoped strictly to project resources, avoiding root or wildcard administrative access. Supporting policy definitions and console screenshots are recorded under `members/adams5ma/evidence/`.
* **C4: Clean Teardown Capability:** Complete teardown instructions and resource-tagging allow fast script-driven destruction to avoid lingering zombie infrastructure.
* **C5: Storage Portability:** Object storage interfaces adhere to S3-compatible endpoints, matching the application's storage port.
* **C6: Budget & Spend Guardrails:** Hard budget alerts and billing thresholds are configured at or below $5 to satisfy course spend safety constraints.

---

## 3. Fallback / Contingency Plan
* **Secondary Target Provider:** Google Cloud Platform (GCP)
* **Contingency Member / Adapter Source:** `members/diazm1a/`
* **Switch Trigger:** If AWS account quotas, unexpected billing anomalies, or IAM permission blocks arise during Module 7 deployment, the team will immediately pivot to GCP.
* **Readiness:** The GCP adapter (`members/diazm1a/adapter.sh`) has passed full capability verification (`cloud-verify.txt` ending in `CONTRACT SATISFIED`) utilizing service account impersonation, with billing guardrails verified via `members/diazm1a/spend-alert.png`.

---

## 4. Operational Responsibilities
* **AWS Primary Infrastructure Lead:** `adams5ma` (Configuration, container deployment, pipeline alignment).
* **GCP Fallback & Verification Lead:** `diazm1a` (Cross-cloud validation, health-check replication, test harness verification).
* **Shared Responsibilities:** Test suite maintenance (`tests/test_security.py`), environment secret isolation, and documentation upkeep.

## Milestone 6 Provider Update

Date: October 18, 2026

The team is using Google Cloud Platform for Milestone 6,
rather than the earlier AWS primary target.

The application was deployed to Google Cloud Run in
project itc531-module7, region us-central1.

The original Milestone 5 provider evaluation is retained
above for historical context.
