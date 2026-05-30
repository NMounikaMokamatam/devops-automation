#!/usr/bin/env python3
"""
k8s_health_check.py
Checks health of all nodes and pods across namespaces.
Outputs a summary and exits non-zero if critical issues are found.
Usage: python k8s_health_check.py [--namespace all] [--slack-webhook URL]
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import urllib.request


@dataclass
class HealthReport:
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    node_issues: list = field(default_factory=list)
    pod_issues: list = field(default_factory=list)
    crash_looping: list = field(default_factory=list)
    pending_pods: list = field(default_factory=list)

    @property
    def critical(self) -> bool:
        return bool(self.node_issues or self.crash_looping)

    def summary(self) -> str:
        lines = [f"K8s Health Report — {self.timestamp}"]
        if not any([self.node_issues, self.pod_issues, self.crash_looping, self.pending_pods]):
            lines.append("✅ All nodes and pods healthy")
        else:
            if self.node_issues:
                lines.append(f"🔴 Node issues ({len(self.node_issues)}): {', '.join(self.node_issues)}")
            if self.crash_looping:
                lines.append(f"🔴 Crash looping ({len(self.crash_looping)}): {', '.join(self.crash_looping)}")
            if self.pending_pods:
                lines.append(f"🟡 Pending pods ({len(self.pending_pods)}): {', '.join(self.pending_pods)}")
        return "\n".join(lines)


def run(cmd: str) -> dict:
    result = subprocess.run(cmd.split(), capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")
    return json.loads(result.stdout)


def check_nodes(report: HealthReport):
    data = run("kubectl get nodes -o json")
    for node in data["items"]:
        name = node["metadata"]["name"]
        for condition in node["status"]["conditions"]:
            if condition["type"] == "Ready" and condition["status"] != "True":
                report.node_issues.append(f"{name}:NotReady")
            if condition["type"] in ("MemoryPressure", "DiskPressure", "PIDPressure"):
                if condition["status"] == "True":
                    report.node_issues.append(f"{name}:{condition['type']}")


def check_pods(report: HealthReport, namespace: str):
    ns_flag = "--all-namespaces" if namespace == "all" else f"-n {namespace}"
    data = run(f"kubectl get pods {ns_flag} -o json")
    for pod in data["items"]:
        name = pod["metadata"]["name"]
        ns   = pod["metadata"]["namespace"]
        full = f"{ns}/{name}"

        phase = pod["status"].get("phase", "")
        if phase == "Pending":
            report.pending_pods.append(full)

        for cs in pod["status"].get("containerStatuses", []):
            if cs.get("restartCount", 0) > 5:
                report.crash_looping.append(f"{full}:{cs['name']}(restarts={cs['restartCount']})")


def notify_slack(webhook_url: str, report: HealthReport):
    color = "danger" if report.critical else "warning" if report.pod_issues else "good"
    payload = json.dumps({
        "attachments": [{
            "color": color,
            "text": report.summary(),
            "footer": "k8s-health-check",
            "ts": datetime.utcnow().timestamp()
        }]
    }).encode()
    req = urllib.request.Request(webhook_url, data=payload,
                                  headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=10)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--namespace", default="all")
    parser.add_argument("--slack-webhook", default=None)
    args = parser.parse_args()

    report = HealthReport()
    check_nodes(report)
    check_pods(report, args.namespace)

    print(report.summary())

    if args.slack_webhook:
        notify_slack(args.slack_webhook, report)

    sys.exit(1 if report.critical else 0)


if __name__ == "__main__":
    main()
