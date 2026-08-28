from app.dashboard import build_dashboard
from app.detectors import run_detectors
from app.sample_data import generate_cost_records, generate_resources


def test_dashboard_is_complete_and_consistent():
    costs = generate_cost_records()
    resources = generate_resources()
    findings = run_detectors(costs, resources)
    dashboard = build_dashboard(costs, resources, findings, "demo", 10000)

    assert dashboard.summary["monitored_resources"] == len(resources)
    assert dashboard.summary["active_findings"] == len(findings)
    assert dashboard.summary["potential_savings"] > 0
    assert len(dashboard.cost_series) == 90
    assert sum(item["cost"] for item in dashboard.service_breakdown) > 0

