from datetime import datetime, timedelta, timezone
from typing import Any

import boto3

from .models import CostRecord, ResourceRecord


class AwsCollector:
    """Read-only AWS collector. No resource mutation methods are exposed."""

    def __init__(self, regions: tuple[str, ...]):
        self.regions = regions

    def collect_costs(self, days: int = 90) -> list[CostRecord]:
        client = boto3.client("ce", region_name="us-east-1")
        end = datetime.now(timezone.utc).date() + timedelta(days=1)
        start = end - timedelta(days=days)
        records: list[CostRecord] = []
        request: dict[str, Any] = {
            "TimePeriod": {"Start": str(start), "End": str(end)},
            "Granularity": "DAILY",
            "Metrics": ["UnblendedCost"],
            "GroupBy": [{"Type": "DIMENSION", "Key": "SERVICE"}],
        }
        while True:
            response = client.get_cost_and_usage(**request)
            for period in response.get("ResultsByTime", []):
                usage_date = period["TimePeriod"]["Start"]
                for group in period.get("Groups", []):
                    metric = group["Metrics"]["UnblendedCost"]
                    records.append(
                        CostRecord(
                            date=usage_date,
                            service=group["Keys"][0],
                            amount=round(float(metric["Amount"]), 4),
                        )
                    )
            next_page_token = response.get("NextPageToken")
            if not next_page_token:
                break
            request["NextPageToken"] = next_page_token
        return records

    def collect_resources(self) -> list[ResourceRecord]:
        records: list[ResourceRecord] = []
        now = datetime.now(timezone.utc)
        for region in self.regions:
            ec2 = boto3.client("ec2", region_name=region)
            cloudwatch = boto3.client("cloudwatch", region_name=region)
            for response in ec2.get_paginator("describe_instances").paginate():
                for reservation in response.get("Reservations", []):
                    for instance in reservation.get("Instances", []):
                        instance_id = instance["InstanceId"]
                        tags = _tags(instance.get("Tags", []))
                        launch_time = instance.get("LaunchTime", now)
                        records.append(
                            ResourceRecord(
                                resource_id=instance_id,
                                name=tags.get("Name", instance_id),
                                resource_type="EC2 instance",
                                service="Amazon EC2",
                                region=region,
                                state=instance.get("State", {}).get("Name", "unknown"),
                                monthly_cost=0,
                                utilization_pct=self._average_cpu(
                                    cloudwatch, instance_id, 14
                                ),
                                age_days=max(0, (now - launch_time).days),
                                tags=tags,
                                collected_at=now,
                            )
                        )
            for response in ec2.get_paginator("describe_volumes").paginate():
                for volume in response.get("Volumes", []):
                    tags = _tags(volume.get("Tags", []))
                    size = float(volume.get("Size", 0))
                    records.append(
                        ResourceRecord(
                            resource_id=volume["VolumeId"],
                            name=tags.get("Name", volume["VolumeId"]),
                            resource_type="EBS volume",
                            service="Amazon EBS",
                            region=region,
                            state=volume.get("State", "unknown"),
                            monthly_cost=round(size * 0.08, 2),
                            attached_to=(volume.get("Attachments") or [{}])[0].get(
                                "InstanceId"
                            ),
                            age_days=max(0, (now - volume.get("CreateTime", now)).days),
                            tags=tags,
                            collected_at=now,
                        )
                    )
        return records

    @staticmethod
    def _average_cpu(cloudwatch: Any, instance_id: str, days: int) -> float | None:
        end = datetime.now(timezone.utc)
        response = cloudwatch.get_metric_statistics(
            Namespace="AWS/EC2",
            MetricName="CPUUtilization",
            Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            StartTime=end - timedelta(days=days),
            EndTime=end,
            Period=86400,
            Statistics=["Average"],
        )
        datapoints = response.get("Datapoints", [])
        if not datapoints:
            return None
        return round(sum(point["Average"] for point in datapoints) / len(datapoints), 2)


def _tags(raw_tags: list[dict[str, str]]) -> dict[str, str]:
    return {
        tag["Key"]: tag["Value"] for tag in raw_tags if "Key" in tag and "Value" in tag
    }
