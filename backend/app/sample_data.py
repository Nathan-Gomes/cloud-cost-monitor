from datetime import date, datetime, timedelta, timezone
import math
import random

from .models import CostRecord, ResourceRecord


SERVICES = {
    "Amazon EC2": (150.0, 0.18),
    "Amazon RDS": (84.0, 0.12),
    "Amazon EBS": (42.0, 0.05),
    "Amazon S3": (28.0, 0.04),
    "AWS Data Transfer": (24.0, 0.08),
    "AWS Lambda": (9.0, 0.14),
}


def generate_cost_records(days: int = 90, seed: int = 42) -> list[CostRecord]:
    rng = random.Random(seed)
    today = date.today()
    records: list[CostRecord] = []
    for offset in range(days - 1, -1, -1):
        current = today - timedelta(days=offset)
        trend = 1 + ((days - offset) / days) * 0.06
        weekday = 0.92 if current.weekday() >= 5 else 1.0
        for service, (base, noise) in SERVICES.items():
            seasonal = 1 + 0.04 * math.sin((days - offset) / 6)
            amount = base * trend * weekday * seasonal * (1 + rng.uniform(-noise, noise))
            if service == "AWS Data Transfer" and offset == 0:
                amount *= 2.75
            records.append(
                CostRecord(
                    date=current,
                    service=service,
                    amount=round(max(amount, 0), 2),
                    region="global" if service in {"Amazon S3", "AWS Data Transfer"} else "ca-central-1",
                )
            )
    return records


def generate_resources() -> list[ResourceRecord]:
    now = datetime.now(timezone.utc)
    return [
        ResourceRecord(resource_id="i-0a91f3d2", name="prod-api-01", resource_type="EC2 instance", service="Amazon EC2", region="ca-central-1", state="running", monthly_cost=184.20, utilization_pct=42.6, age_days=241, tags={"Environment": "production", "Owner": "platform"}, collected_at=now),
        ResourceRecord(resource_id="i-0b72e8c1", name="batch-worker-02", resource_type="EC2 instance", service="Amazon EC2", region="ca-central-1", state="running", monthly_cost=121.40, utilization_pct=11.8, age_days=153, tags={"Environment": "production", "Owner": "data"}, collected_at=now),
        ResourceRecord(resource_id="i-0c41a6e9", name="qa-loadtest-old", resource_type="EC2 instance", service="Amazon EC2", region="us-east-1", state="running", monthly_cost=186.30, utilization_pct=1.8, age_days=47, tags={"Environment": "qa", "Owner": "unknown"}, collected_at=now),
        ResourceRecord(resource_id="db-reporting-1", name="reporting-postgres", resource_type="RDS database", service="Amazon RDS", region="ca-central-1", state="available", monthly_cost=312.00, utilization_pct=9.4, age_days=389, tags={"Environment": "production", "Owner": "analytics"}, collected_at=now),
        ResourceRecord(resource_id="db-orders-1", name="orders-postgres", resource_type="RDS database", service="Amazon RDS", region="ca-central-1", state="available", monthly_cost=428.00, utilization_pct=58.3, age_days=510, tags={"Environment": "production", "Owner": "platform"}, collected_at=now),
        ResourceRecord(resource_id="vol-04f39bd1", name="prod-api-root", resource_type="EBS volume", service="Amazon EBS", region="ca-central-1", state="in-use", monthly_cost=18.60, attached_to="i-0a91f3d2", age_days=241, tags={"Environment": "production"}, collected_at=now),
        ResourceRecord(resource_id="vol-09a71ce4", name="legacy-backup-volume", resource_type="EBS volume", service="Amazon EBS", region="us-east-1", state="available", monthly_cost=64.00, age_days=63, tags={"Environment": "unknown", "Owner": "unknown"}, collected_at=now),
        ResourceRecord(resource_id="snap-0318bc44", name="pre-migration-snapshot", resource_type="EBS snapshot", service="Amazon EBS", region="us-east-1", state="completed", monthly_cost=22.40, age_days=184, tags={"Environment": "legacy"}, collected_at=now),
        ResourceRecord(resource_id="bucket-finops-logs", name="central-log-archive", resource_type="S3 bucket", service="Amazon S3", region="ca-central-1", state="active", monthly_cost=74.80, age_days=622, tags={"Environment": "shared", "Owner": "security"}, collected_at=now),
    ]

