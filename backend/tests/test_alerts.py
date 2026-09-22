import json
from datetime import datetime, timezone
from unittest.mock import patch

from app.alerts import publish_findings
from app.models import Finding, Severity


def finding(finding_id: str, severity: Severity) -> Finding:
    return Finding(
        id=finding_id,
        severity=severity,
        finding_type="cost_spike",
        title="Unexpected cost increase",
        service="Amazon EC2",
        region="ca-central-1",
        detected_at=datetime.now(timezone.utc),
        monthly_impact=125,
        evidence="Daily spend exceeded the trailing baseline.",
        recommendation="Review recent usage changes.",
    )


@patch("app.alerts.boto3.client")
def test_publish_findings_skips_when_topic_is_not_configured(mock_client):
    assert publish_findings(None, [finding("fin-high", "high")]) == 0
    mock_client.assert_not_called()


@patch("app.alerts.boto3.client")
def test_publish_findings_suppresses_non_urgent_findings(mock_client):
    topic_arn = "arn:aws:sns:ca-central-1:123456789012:finops"
    assert publish_findings(topic_arn, [finding("fin-low", "low")]) == 0
    mock_client.assert_not_called()


@patch("app.alerts.boto3.client")
def test_publish_findings_sends_only_urgent_findings(mock_client):
    findings = [
        finding("fin-critical", "critical"),
        finding("fin-high", "high"),
        finding("fin-medium", "medium"),
    ]

    published = publish_findings("arn:aws:sns:ca-central-1:123456789012:finops", findings)

    assert published == 2
    mock_client.assert_called_once_with("sns")
    request = mock_client.return_value.publish.call_args.kwargs
    assert request["TopicArn"] == "arn:aws:sns:ca-central-1:123456789012:finops"
    assert request["Subject"] == "FinOps monitor: 2 urgent finding(s)"
    payload = json.loads(request["Message"])
    assert [item["id"] for item in payload] == ["fin-critical", "fin-high"]
    assert [item["severity"] for item in payload] == ["critical", "high"]
