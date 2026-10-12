#!/usr/bin/env bash

AWS_PROFILE="${AWS_PROFILE:-itc531}"
AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-2}"
AWS_BUDGET_NAME="${AWS_BUDGET_NAME:-My Monthly Cost Budget}"
SPEND_ALERT_THRESHOLD="${SPEND_ALERT_THRESHOLD:-5}"
SERVICE_NAME="${SERVICE_NAME:-itc531-myauth}"
S3_BUCKET="${S3_BUCKET:-itc531-myauth-bucket}"

export AWS_PROFILE AWS_DEFAULT_REGION

adapter_meta() {
  cat <<META
provider:        aws
region:          ${AWS_DEFAULT_REGION}
compute service: Amazon ECS / AWS Fargate
storage service: Amazon S3
auth model:      scoped IAM access keys
contract check:  $(date +%Y-%m-%d)
META
}

adapter_verify() {
  local account clusters buckets budget_limit notifications
  local budget_name
  budget_name="$AWS_BUDGET_NAME"

  echo "Checking AWS authentication..."
  account="$(aws sts get-caller-identity --query Account --output text)" || return 1

  echo "C1 compute: checking ECS access..."
  clusters="$(aws ecs list-clusters \
    --region "$AWS_DEFAULT_REGION" \
    --query 'clusterArns' --output json)" || return 1
  echo "C1 compute: PASS (ECS accessible; clusters: $clusters)"

  echo "C2 storage: checking signed S3 access..."
  aws s3api list-buckets --query 'Buckets[].Name' --output json || return 1
  echo "C2 storage: PASS (signed bucket listing succeeded)"

  echo "C3 credentials: checking identity..."
  local identity
  identity="$(aws sts get-caller-identity --query Arn --output text)" || return 1
  echo "C3 identity: $identity"
  echo "C3 scope: IAM user identified; review its attached policies in AWS IAM Console"
  echo "C3 scope: requires reviewed IAM policy evidence"

  echo "C4 enumerate: checking ECS resource listing..."
  aws ecs list-clusters --region "$AWS_DEFAULT_REGION" \
    --query 'clusterArns' --output json || return 1
  echo "C4 enumerate: PASS (ECS cluster enumeration works)"

  echo "C5 spend alert: checking budget..."
  budget_limit="$(aws budgets describe-budget \
    --account-id "$account" \
    --budget-name "$budget_name" \
    --query 'Budget.BudgetLimit.Amount' --output text)" || return 1

  echo "C5 budget limit: \$${budget_limit}"

  awk -v limit="$budget_limit" -v maximum="$SPEND_ALERT_THRESHOLD" \
    'BEGIN { exit !(limit+0 <= maximum+0) }' || {
      echo "C5 FAIL: budget exceeds threshold"
      return 1
    }

  notifications="$(aws budgets describe-notifications-for-budget \
    --account-id "$account" \
    --budget-name "$budget_name" \
    --query 'Notifications' --output json)" || return 1

  echo "C5 notifications: $notifications"

  printf '%s' "$notifications" | python3 -c '
import json, sys
items=json.load(sys.stdin)
if not any(
    x.get("NotificationType") in ("ACTUAL", "FORECASTED")
    and x.get("Threshold", 999999) <= 100
    and x.get("ComparisonOperator") in ("GREATER_THAN", "GREATER_THAN_OR_EQUAL_TO")
    for x in items
):
    sys.exit("No qualifying budget notification found")
' || return 1

  echo "C5 spend alert: PASS"

  echo "C6 cost model:"
  echo "Amazon ECS/Fargate charges depend on allocated vCPU, memory, operating time, and region."
  echo "Amazon S3 charges depend on storage, requests, and data transfer."
  echo "Pricing references:"
  echo "https://aws.amazon.com/fargate/pricing/"
  echo "https://aws.amazon.com/s3/pricing/"
  echo "C6: requires a documented term-level cost estimate"

  return 0
}

adapter_enumerate() {
  echo "NOT IMPLEMENTED: complete deployment-resource enumeration" >&2
  return 1
}

adapter_deploy() {
  echo "NOT IMPLEMENTED: deployment belongs to a later module" >&2
  return 1
}

adapter_destroy() {
  echo "NOT IMPLEMENTED: cleanup belongs to a later module" >&2
  return 1
}
