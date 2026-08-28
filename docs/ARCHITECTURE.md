# Architecture

## Data flow

1. EventBridge starts a small ECS Fargate collector each morning.
2. The collector uses read-only IAM permissions to query Cost Explorer, EC2, EBS, RDS, and CloudWatch.
3. Normalized daily costs, resource snapshots, and findings are upserted into PostgreSQL.
4. Deterministic rules compare current observations with trailing baselines.
5. High-severity findings are published to SNS.
6. FastAPI exposes one dashboard contract to the React application.

## Detection rules

| Rule | Evidence | Default trigger | Estimated impact |
| --- | --- | --- | --- |
| Idle compute | Seven-day average CPU and running state | CPU below 5% for at least 7 days | Full monthly run rate |
| Rightsizing candidate | Fourteen-day utilization and monthly cost | Utilization below 20%, cost at least $100 | 40% of monthly run rate |
| Unattached storage | EBS attachment state and age | Volume is `available` | Full monthly storage cost |
| Stale snapshot | Snapshot age and retention tag | Older than 90 days without retention | Full monthly snapshot cost |
| Cost spike | Latest daily spend versus trailing median | At least 35% and $20 monthly impact | Daily excess multiplied by 30 |

All recommendations require human review. The application does not stop, resize, or delete cloud resources.

## Security boundary

- IAM access is read-only except for publishing to one SNS topic.
- Database credentials are loaded from AWS Secrets Manager.
- PostgreSQL is private and accepts traffic only from the collector security group.
- The dashboard demo contains generated data and no cloud credentials.
- Destructive cloud actions are intentionally excluded.

