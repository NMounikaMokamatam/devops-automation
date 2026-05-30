#!/usr/bin/env python3
"""
aws_cost_report.py
Pulls AWS Cost Explorer data and posts a weekly cost summary to Slack.
Usage: python aws_cost_report.py --days 7 --slack-webhook URL
"""

import argparse
import json
from datetime import datetime, timedelta
import boto3
import urllib.request


def get_cost_by_service(days: int) -> list[dict]:
    client = boto3.client("ce", region_name="us-east-1")
    end   = datetime.utcnow().date()
    start = end - timedelta(days=days)

    response = client.get_cost_and_usage(
        TimePeriod={"Start": str(start), "End": str(end)},
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
    )

    results = []
    for group in response["ResultsByTime"][0]["Groups"]:
        service = group["Keys"][0]
        amount  = float(group["Metrics"]["UnblendedCost"]["Amount"])
        if amount > 1.0:
            results.append({"service": service, "cost": round(amount, 2)})

    return sorted(results, key=lambda x: x["cost"], reverse=True)


def format_report(costs: list[dict], days: int) -> str:
    total = sum(c["cost"] for c in costs)
    lines = [f"💰 AWS Cost Report (last {days} days)", f"Total: *${total:,.2f}*", ""]
    for item in costs[:10]:
        bar = "█" * min(int(item["cost"] / total * 20), 20)
        lines.append(f"`{item['service'][:35]:<35}` ${item['cost']:>8,.2f}  {bar}")
    return "\n".join(lines)


def post_to_slack(webhook_url: str, text: str):
    payload = json.dumps({"text": text}).encode()
    req = urllib.request.Request(webhook_url, data=payload,
                                  headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=10)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--slack-webhook", required=True)
    args = parser.parse_args()

    costs  = get_cost_by_service(args.days)
    report = format_report(costs, args.days)
    print(report)
    post_to_slack(args.slack_webhook, report)


if __name__ == "__main__":
    main()
