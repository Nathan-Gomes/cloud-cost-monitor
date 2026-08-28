import json

import boto3

from .models import Finding


def publish_findings(topic_arn: str | None, findings: list[Finding]) -> int:
    if not topic_arn:
        return 0
    urgent = [finding for finding in findings if finding.severity in {"critical", "high"}]
    if not urgent:
        return 0
    client = boto3.client("sns")
    client.publish(
        TopicArn=topic_arn,
        Subject=f"FinOps monitor: {len(urgent)} urgent finding(s)",
        Message=json.dumps([finding.model_dump(mode="json") for finding in urgent], indent=2),
    )
    return len(urgent)

