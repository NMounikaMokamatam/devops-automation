# devops-automation

Python scripts for operational tasks. Reduced repetitive ops work by ~50% in production environments.

## Scripts

### `k8s_health_check.py`
Checks node conditions and pod health across namespaces. Posts to Slack on issues. Used as a cron job for proactive monitoring.
```bash
python k8s_health_check.py --namespace production --slack-webhook $SLACK_WEBHOOK
```

### `aws_cost_report.py`
Pulls AWS Cost Explorer data and posts a weekly cost breakdown to Slack. Top 10 services with visual bar chart.
```bash
python aws_cost_report.py --days 7 --slack-webhook $SLACK_WEBHOOK
```

## Setup
```bash
pip install boto3
# AWS credentials via IAM role or ~/.aws/credentials
# kubectl configured with appropriate kubeconfig
```

## Cron Examples
```bash
# Health check every 5 minutes
*/5 * * * * python /opt/scripts/k8s_health_check.py --slack-webhook $SLACK_WEBHOOK

# Cost report every Monday at 9am
0 9 * * 1 python /opt/scripts/aws_cost_report.py --days 7 --slack-webhook $SLACK_WEBHOOK
```
