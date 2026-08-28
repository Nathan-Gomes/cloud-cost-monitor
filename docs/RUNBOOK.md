# Operating runbook

## A finding appears

1. Validate the owner, environment, and business purpose using tags.
2. Confirm the evidence window in CloudWatch and Cost Explorer.
3. Estimate service impact and rollback requirements.
4. Apply the approved change through Terraform or the owning deployment pipeline.
5. Mark the finding resolved after the next collection confirms the result.

## Collection fails

1. Check the EventBridge target and ECS task exit code.
2. Inspect `/ecs/cloud-cost-monitor` in CloudWatch Logs.
3. Verify Cost Explorer is enabled and the task role has the documented read permissions.
4. Verify the RDS endpoint and Secrets Manager value.
5. Run the collector in demo mode to distinguish infrastructure failure from application failure.

## Cost controls

- Run collection once daily, not continuously.
- Keep CloudWatch metric windows aggregated to daily periods.
- Set log retention to 14 days for the pilot.
- Review Cost Explorer API usage before increasing collection frequency.
- Destroy the optional live stack when it is not being evaluated.

