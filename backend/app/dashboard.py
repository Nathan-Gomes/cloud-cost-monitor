from collections import defaultdict
from datetime import date, datetime, timezone

from .models import CostRecord, DashboardData, Finding, ResourceRecord


def build_dashboard(costs: list[CostRecord], resources: list[ResourceRecord], findings: list[Finding], mode: str, monthly_budget: float) -> DashboardData:
    today = date.today()
    current_month = [record for record in costs if record.date.year == today.year and record.date.month == today.month]
    previous_month_number = 12 if today.month == 1 else today.month - 1
    previous_month_year = today.year - 1 if today.month == 1 else today.year
    previous_month = [record for record in costs if record.date.year == previous_month_year and record.date.month == previous_month_number]

    current_total = sum(record.amount for record in current_month)
    elapsed_days = max(today.day, 1)
    forecast = current_total / elapsed_days * 30.44
    previous_comparable = sum(record.amount for record in previous_month if record.date.day <= elapsed_days)
    change_pct = ((current_total - previous_comparable) / previous_comparable * 100) if previous_comparable else 0

    daily: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for record in costs:
        day = str(record.date)
        category = _category(record.service)
        daily[day][category] += record.amount
        daily[day]["total"] += record.amount
    cost_series = [
        {"date": day, **{key: round(values.get(key, 0), 2) for key in ["total", "compute", "storage", "database", "network", "other"]}}
        for day, values in sorted(daily.items())
    ]

    by_service: dict[str, float] = defaultdict(float)
    for record in current_month:
        by_service[record.service] += record.amount
    service_breakdown = [
        {"service": service, "cost": round(amount, 2), "share": round(amount / current_total * 100, 1) if current_total else 0}
        for service, amount in sorted(by_service.items(), key=lambda item: item[1], reverse=True)
    ]
    potential_savings = sum(finding.monthly_impact for finding in findings if finding.status == "open")

    return DashboardData(
        meta={"generated_at": datetime.now(timezone.utc).isoformat(), "mode": mode, "period": today.strftime("%B %Y")},
        summary={
            "current_month_cost": round(current_total, 2),
            "forecast_cost": round(forecast, 2),
            "monthly_budget": round(monthly_budget, 2),
            "change_pct": round(change_pct, 1),
            "potential_savings": round(potential_savings, 2),
            "active_findings": sum(1 for finding in findings if finding.status == "open"),
            "monitored_resources": len(resources),
        },
        cost_series=cost_series,
        service_breakdown=service_breakdown,
        findings=findings,
        resources=resources,
    )


def _category(service: str) -> str:
    if service in {"Amazon EC2", "AWS Lambda"}:
        return "compute"
    if service in {"Amazon EBS", "Amazon S3"}:
        return "storage"
    if service == "Amazon RDS":
        return "database"
    if "Transfer" in service or "CloudFront" in service:
        return "network"
    return "other"

