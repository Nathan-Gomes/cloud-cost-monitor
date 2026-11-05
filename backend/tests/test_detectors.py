from datetime import datetime, timedelta, timezone

from app.detectors import detect_cost_spikes, detect_resource_findings
from app.models import CostRecord, ResourceRecord


def resource(**overrides):
    values = {
        "resource_id": "i-test",
        "name": "test-instance",
        "resource_type": "EC2 instance",
        "service": "Amazon EC2",
        "region": "ca-central-1",
        "state": "running",
        "monthly_cost": 150,
        "utilization_pct": 2.5,
        "age_days": 30,
        "collected_at": datetime.now(timezone.utc),
    }
    values.update(overrides)
    return ResourceRecord(**values)


def test_idle_instance_is_flagged_with_full_run_rate():
    findings = detect_resource_findings([resource()])
    assert len(findings) == 1
    assert findings[0].finding_type == "idle_compute"
    assert findings[0].monthly_impact == 150


def test_healthy_instance_is_not_flagged():
    assert detect_resource_findings([resource(utilization_pct=48)]) == []


def test_unattached_volume_is_flagged():
    volume = resource(
        resource_id="vol-test",
        resource_type="EBS volume",
        service="Amazon EBS",
        state="available",
        monthly_cost=64,
        utilization_pct=None,
    )
    findings = detect_resource_findings([volume])
    assert findings[0].finding_type == "unattached_storage"


def test_stale_snapshot_is_flagged_after_retention_window():
    snapshot = resource(
        resource_id="snap-test",
        resource_type="EBS snapshot",
        service="Amazon EBS",
        state="completed",
        age_days=120,
        monthly_cost=18,
        utilization_pct=None,
    )
    findings = detect_resource_findings([snapshot])
    assert len(findings) == 1
    assert findings[0].finding_type == "stale_snapshot"
    assert findings[0].severity == "low"


def test_recent_snapshot_is_not_flagged():
    snapshot = resource(
        resource_id="snap-test",
        resource_type="EBS snapshot",
        service="Amazon EBS",
        state="completed",
        age_days=45,
        monthly_cost=18,
        utilization_pct=None,
    )
    assert detect_resource_findings([snapshot]) == []


def test_cost_spike_uses_trailing_median():
    today = datetime.now(timezone.utc).date()
    costs = [
        CostRecord(
            date=today - timedelta(days=14 - index), service="Data Transfer", amount=10
        )
        for index in range(14)
    ]
    costs.append(CostRecord(date=today, service="Data Transfer", amount=28))
    findings = detect_cost_spikes(costs)
    assert len(findings) == 1
    assert findings[0].severity == "critical"
    assert findings[0].monthly_impact == 540


def test_cost_spike_ignores_zero_baseline():
    today = datetime.now(timezone.utc).date()
    costs = [
        CostRecord(
            date=today - timedelta(days=14 - index), service="AWS Lambda", amount=0
        )
        for index in range(14)
    ]
    costs.append(CostRecord(date=today, service="AWS Lambda", amount=8))
    assert detect_cost_spikes(costs) == []


def test_cost_spike_aggregates_accounts_into_daily_service_spend():
    today = datetime.now(timezone.utc).date()
    costs = []
    for days_ago in range(14, 0, -1):
        day = today - timedelta(days=days_ago)
        costs.extend(
            [
                CostRecord(
                    date=day, service="Amazon EC2", amount=100, account_id="platform"
                ),
                CostRecord(
                    date=day, service="Amazon EC2", amount=1, account_id="sandbox"
                ),
            ]
        )
    costs.extend(
        [
            CostRecord(
                date=today, service="Amazon EC2", amount=200, account_id="platform"
            ),
            CostRecord(
                date=today, service="Amazon EC2", amount=1, account_id="sandbox"
            ),
        ]
    )

    findings = detect_cost_spikes(costs)

    assert len(findings) == 1
    assert findings[0].severity == "high"
    assert findings[0].monthly_impact == 3000
    assert "Latest daily spend was $201.00" in findings[0].evidence


def test_cost_spike_requires_eight_distinct_days():
    today = datetime.now(timezone.utc).date()
    costs = []
    for days_ago in range(3, -1, -1):
        day = today - timedelta(days=days_ago)
        costs.extend(
            [
                CostRecord(
                    date=day, service="Amazon S3", amount=1, account_id="platform"
                ),
                CostRecord(
                    date=day,
                    service="Amazon S3",
                    amount=100 if days_ago == 0 else 1,
                    account_id="sandbox",
                ),
            ]
        )

    assert detect_cost_spikes(costs) == []
