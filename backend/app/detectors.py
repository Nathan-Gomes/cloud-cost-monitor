from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha1
from statistics import median

from .models import CostRecord, Finding, ResourceRecord


def _finding_id(*parts: str) -> str:
    digest = sha1("|".join(parts).encode("utf-8")).hexdigest()[:10]
    return f"fin-{digest}"


def detect_resource_findings(resources: list[ResourceRecord]) -> list[Finding]:
    findings: list[Finding] = []
    now = datetime.now(timezone.utc)

    for resource in resources:
        utilization = resource.utilization_pct
        if (
            resource.resource_type == "EC2 instance"
            and resource.state == "running"
            and utilization is not None
            and utilization < 5
            and resource.age_days >= 7
        ):
            findings.append(
                Finding(
                    id=_finding_id("idle-ec2", resource.resource_id),
                    severity="high",
                    finding_type="idle_compute",
                    title=f"Idle compute instance: {resource.name}",
                    resource_id=resource.resource_id,
                    service="Amazon EC2",
                    region=resource.region,
                    detected_at=now,
                    monthly_impact=round(resource.monthly_cost, 2),
                    evidence=(
                        f"Average CPU was {utilization:.1f}% over 7 days while the instance "
                        f"remained running. Estimated monthly cost is ${resource.monthly_cost:,.0f}."
                    ),
                    recommendation="Confirm ownership, then schedule or stop the instance during unused periods.",
                )
            )
        elif (
            resource.resource_type in {"EC2 instance", "RDS database"}
            and resource.state in {"running", "available"}
            and utilization is not None
            and utilization < 20
            and resource.monthly_cost >= 100
        ):
            findings.append(
                Finding(
                    id=_finding_id("oversized", resource.resource_id),
                    severity="medium",
                    finding_type="oversized_resource",
                    title=f"Rightsizing candidate: {resource.name}",
                    resource_id=resource.resource_id,
                    service=resource.service,
                    region=resource.region,
                    detected_at=now,
                    monthly_impact=round(resource.monthly_cost * 0.4, 2),
                    evidence=(
                        f"Average utilization was {utilization:.1f}% over 14 days. "
                        f"Current monthly run rate is ${resource.monthly_cost:,.0f}."
                    ),
                    recommendation="Compare p95 utilization with the next smaller instance class before resizing.",
                )
            )

        if resource.resource_type == "EBS volume" and resource.state == "available":
            findings.append(
                Finding(
                    id=_finding_id("unattached-ebs", resource.resource_id),
                    severity="high" if resource.monthly_cost >= 50 else "medium",
                    finding_type="unattached_storage",
                    title=f"Unattached storage volume: {resource.name}",
                    resource_id=resource.resource_id,
                    service="Amazon EBS",
                    region=resource.region,
                    detected_at=now,
                    monthly_impact=round(resource.monthly_cost, 2),
                    evidence=(
                        f"The volume has been unattached for {resource.age_days} days and continues "
                        f"to cost approximately ${resource.monthly_cost:,.0f} per month."
                    ),
                    recommendation="Verify backup and retention requirements, snapshot if required, then remove the volume.",
                )
            )

        if resource.resource_type == "EBS snapshot" and resource.age_days > 90:
            findings.append(
                Finding(
                    id=_finding_id("stale-snapshot", resource.resource_id),
                    severity="low",
                    finding_type="stale_snapshot",
                    title=f"Snapshot exceeds retention window: {resource.name}",
                    resource_id=resource.resource_id,
                    service="Amazon EBS",
                    region=resource.region,
                    detected_at=now,
                    monthly_impact=round(resource.monthly_cost, 2),
                    evidence=f"Snapshot age is {resource.age_days} days with no retention tag.",
                    recommendation="Confirm the recovery policy and expire the snapshot if it is no longer required.",
                )
            )

    return findings


def detect_cost_spikes(costs: list[CostRecord], threshold_pct: float = 35) -> list[Finding]:
    by_service: dict[str, list[CostRecord]] = defaultdict(list)
    for record in costs:
        by_service[record.service].append(record)

    findings: list[Finding] = []
    now = datetime.now(timezone.utc)
    for service, records in by_service.items():
        ordered = sorted(records, key=lambda record: record.date)
        if len(ordered) < 8:
            continue
        latest = ordered[-1]
        baseline = median(record.amount for record in ordered[-15:-1])
        if baseline <= 0:
            continue
        increase_pct = ((latest.amount - baseline) / baseline) * 100
        monthly_impact = max(0, (latest.amount - baseline) * 30)
        if increase_pct < threshold_pct or monthly_impact < 20:
            continue
        severity = "critical" if increase_pct >= 100 else "high" if increase_pct >= 60 else "medium"
        findings.append(
            Finding(
                id=_finding_id("cost-spike", service, str(latest.date)),
                severity=severity,
                finding_type="cost_spike",
                title=f"Unusual {service} cost increase",
                service=service,
                region=latest.region,
                detected_at=now,
                monthly_impact=round(monthly_impact, 2),
                evidence=(
                    f"Latest daily spend was ${latest.amount:,.2f}, {increase_pct:.0f}% above "
                    f"the trailing 14-day median of ${baseline:,.2f}."
                ),
                recommendation="Review service usage, recent deployments, and cost-allocation tags before the next billing cycle.",
            )
        )
    return findings


def run_detectors(costs: list[CostRecord], resources: list[ResourceRecord]) -> list[Finding]:
    findings = detect_resource_findings(resources) + detect_cost_spikes(costs)
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return sorted(findings, key=lambda finding: (order[finding.severity], -finding.monthly_impact))

