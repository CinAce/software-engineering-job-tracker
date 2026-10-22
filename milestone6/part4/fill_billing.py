#!/usr/bin/env python3
"""Insert verified Google Cloud Billing figures into existing measurement report.
No new latency tests are run; this only edits 4b, leaving 4a and 4c unchanged.
"""
from __future__ import annotations
import argparse
import math
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--amount', type=float, default=None, help='Actual USD from GCP Billing Reports')
p.add_argument('--observed-at', default=None, help='Exact timestamp/timezone when you read billing')
p.add_argument('--period', default=None, help='Report time range, e.g. 2026-10-18 to 2026-10-19 (charge period)')
p.add_argument('--report', default='milestone6/MEASUREMENT.md')
a = p.parse_args()
if a.amount is None:
    try:
        a.amount = float(input('Actual GCP Billing Reports USD total (not a guess): ').strip())
    except ValueError:
        p.error('Enter the actual numeric amount shown in Billing Reports')
if a.observed_at is None:
    a.observed_at = input('When did you view the billing total? Include timezone: ').strip()
if a.period is None:
    a.period = input('Exact report filter/date range shown on screenshot: ').strip()
if not math.isfinite(a.amount) or a.amount < 0:
    p.error('amount must be a finite, nonnegative number')
if not a.observed_at.strip() or not a.period.strip():
    p.error('both timestamp and selected report date range are required')
report = Path(a.report)
if not any(Path(f).is_file() for f in ['milestone6/evidence/gcp-billing-report.png', 'milestone6/evidence/gcp-billing-report.pdf']):
    p.error('First save a safely cropped/redacted GCP Billing Reports screenshot to milestone6/evidence/gcp-billing-report.png (or PDF)')
if not report.is_file():
    p.error(f'First run measure_latency.py to create {report}')
s = report.read_text()
start_marker = '## 4b. Cost: Google Cloud billing versus the Milestone 3 model'
end_marker = '## 4c. Reversal criterion (original Milestone 3)'
if s.count(start_marker) != 1 or s.count(end_marker) != 1:
    p.error('Unexpected report sections; refusing to rewrite')
start = s.index(start_marker)
end = s.index(end_marker, start)
section = f'''## 4b. Cost: Google Cloud billing versus the Milestone 3 model

**Original Milestone 3 model:** `milestone3/COST_MODEL.md` assumed AWS `us-east-1`, 15,000 requests/month, 256 MB and 120 ms Lambda duration, and estimated **$0.025/month** for Lambda + API Gateway versus **$31.28/month** for Fargate + ALB; these were forecasts before free allowances, not observed bills.

**Deployed solution:** Google Cloud Run in `us-central1` with 0 minimum and 1 maximum instance, Google Cloud Storage, three Secret Manager secrets, and ephemeral SQLite. The configuration uses a different provider, storage service mix, compute shape, and time horizon from the original AWS model.

**Actual Google Cloud billing reported:** **${a.amount:.4f} USD** for GCP project `itc531-module7`, as observed **{a.observed_at}**.

**Selected time range and filter:** **{a.period}**, `itc531-module7` project, grouped by Service, including applicable credits/discounts. Screenshot: `milestone6/evidence/gcp-billing-report.png`. A project total can include Module 7 and other demonstrations in that same window; it must not be mislabeled as costs of the Job Tracker alone.

**Variance:** A numerical AWS-versus-GCP difference is **not a like-for-like variance**; the actual ${a.amount:.4f} is a project-period GCP charge, while $0.025 and $31.28 are monthly AWS models for different infrastructure and a hypothetical 15,000 requests. The main reasons for divergence are scale-to-zero instead of an always-on Fargate task and ALB, GCP's allowance and credit structure, regional prices, billed resources (Cloud Storage / Secret Manager / logging / egress) that AWS's stateless examples treat differently, and the small demonstration traffic volume. Check the screenshot for which line items actually have a charge; do not assume they were all free. Billing reports can lag fresh usage.

**Measurement method:** Google Cloud Console → Billing → Reports; Charge period starting October 18, 2026; project filter `itc531-module7`; group by Service. Read the filtered subtotal after credits and screenshot date/time and filters. See https://docs.cloud.google.com/billing/docs/how-to/reports (read October 18, 2026). The $5 budget alarm is notification only, not a hard spending cap.

'''
report.write_text(s[:start] + section + s[end:])
print(f'Updated {report} using explicitly supplied Billing Reports measurement (${a.amount:.4f}).')
print('Ensure milestone6/evidence/gcp-billing-report.png actually shows that number and the filter.')
