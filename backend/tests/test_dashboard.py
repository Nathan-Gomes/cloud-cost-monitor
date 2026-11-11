from datetime import date
from unittest.mock import patch

from app.dashboard import build_dashboard
from app.detectors import run_detectors
from app.models import CostRecord
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


def test_forecast_and_change_use_latest_completed_cost_day():
    costs = [
        CostRecord(date=date(2026, 11, day), service="Amazon EC2", amount=10)
        for day in range(1, 11)
    ]
    costs.extend(
        CostRecord(
            date=date(2026, 10, day),
            service="Amazon EC2",
            amount=100 if day == 11 else 10,
        )
        for day in range(1, 12)
    )

    with patch("app.dashboard.date") as mock_date:
        mock_date.today.return_value = date(2026, 11, 11)
        dashboard = build_dashboard(costs, [], [], "aws", 1000)

    assert dashboard.summary["current_month_cost"] == 100
    assert dashboard.summary["forecast_cost"] == 304.4
    assert dashboard.summary["change_pct"] == 0

