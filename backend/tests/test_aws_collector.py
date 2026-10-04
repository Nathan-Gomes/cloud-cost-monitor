from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from app.aws_collector import AwsCollector


class FakePaginator:
    def __init__(self, pages):
        self.pages = pages
        self.kwargs = None

    def paginate(self, **kwargs):
        self.kwargs = kwargs
        return iter(self.pages)


@patch("app.aws_collector.boto3.client")
def test_collect_costs_reads_every_cost_explorer_page(mock_client):
    client = MagicMock()
    client.get_cost_and_usage.side_effect = [
        {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2026-09-01"},
                    "Groups": [
                        {
                            "Keys": ["Amazon EC2"],
                            "Metrics": {"UnblendedCost": {"Amount": "12.34567"}},
                        }
                    ],
                }
            ],
            "NextPageToken": "page-2",
        },
        {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2026-09-02"},
                    "Groups": [
                        {
                            "Keys": ["Amazon S3"],
                            "Metrics": {"UnblendedCost": {"Amount": "8.1"}},
                        }
                    ],
                }
            ]
        },
    ]
    mock_client.return_value = client

    records = AwsCollector(("ca-central-1",)).collect_costs(days=30)

    assert [
        (str(record.date), record.service, record.amount) for record in records
    ] == [
        ("2026-09-01", "Amazon EC2", 12.3457),
        ("2026-09-02", "Amazon S3", 8.1),
    ]
    mock_client.assert_called_once_with("ce", region_name="us-east-1")
    assert client.get_cost_and_usage.call_count == 2
    first_request = client.get_cost_and_usage.call_args_list[0].kwargs
    second_request = client.get_cost_and_usage.call_args_list[1].kwargs
    assert first_request["Granularity"] == "DAILY"
    assert first_request["GroupBy"] == [{"Type": "DIMENSION", "Key": "SERVICE"}]
    assert "NextPageToken" not in first_request
    assert second_request["NextPageToken"] == "page-2"


@patch("app.aws_collector.boto3.client")
def test_collect_resources_reads_every_ec2_page(mock_client):
    now = datetime.now(timezone.utc)
    instance_pages = [
        {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-first",
                            "LaunchTime": now - timedelta(days=30),
                            "State": {"Name": "running"},
                            "Tags": [{"Key": "Name", "Value": "api-first"}],
                        }
                    ]
                }
            ]
        },
        {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-second",
                            "LaunchTime": now - timedelta(days=20),
                            "State": {"Name": "stopped"},
                        }
                    ]
                }
            ]
        },
    ]
    volume_pages = [
        {
            "Volumes": [
                {
                    "VolumeId": "vol-first",
                    "CreateTime": now - timedelta(days=10),
                    "State": "in-use",
                    "Size": 100,
                    "Attachments": [{"InstanceId": "i-first"}],
                }
            ]
        },
        {
            "Volumes": [
                {
                    "VolumeId": "vol-second",
                    "CreateTime": now - timedelta(days=5),
                    "State": "available",
                    "Size": 50,
                }
            ]
        },
    ]
    paginators = {
        "describe_instances": FakePaginator(instance_pages),
        "describe_volumes": FakePaginator(volume_pages),
    }
    ec2 = MagicMock()
    ec2.get_paginator.side_effect = paginators.__getitem__
    cloudwatch = MagicMock()
    cloudwatch.get_metric_statistics.return_value = {"Datapoints": []}

    def client(service, **kwargs):
        assert kwargs == {"region_name": "ca-central-1"}
        return {"ec2": ec2, "cloudwatch": cloudwatch}[service]

    mock_client.side_effect = client

    records = AwsCollector(("ca-central-1",)).collect_resources()

    assert [record.resource_id for record in records] == [
        "i-first",
        "i-second",
        "vol-first",
        "vol-second",
    ]
    assert records[0].name == "api-first"
    assert records[2].attached_to == "i-first"
    assert records[2].monthly_cost == 8.0
    assert records[3].attached_to is None
    assert ec2.get_paginator.call_args_list[0].args == ("describe_instances",)
    assert ec2.get_paginator.call_args_list[1].args == ("describe_volumes",)
