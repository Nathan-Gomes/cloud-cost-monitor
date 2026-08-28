from datetime import date, datetime, timedelta, timezone

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


def test_cost_spike_uses_trailing_median():
    today = date.today()
    costs = [CostRecord(date=today - timedelta(days=14 - index), service="Data Transfer", amount=10) for index in range(14)]
    costs.append(CostRecord(date=today, service="Data Transfer", amount=28))
    findings = detect_cost_spikes(costs)
    assert len(findings) == 1
    assert findings[0].severity == "critical"
    assert findings[0].monthly_impact == 540

