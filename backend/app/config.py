from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_path: str = os.getenv("DATABASE_PATH", "data/cloud_costs.db")
    database_url: str | None = os.getenv("DATABASE_URL")
    app_mode: str = os.getenv("APP_MODE", "demo")
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    monitored_regions: tuple[str, ...] = tuple(
        part.strip()
        for part in os.getenv("MONITORED_REGIONS", "us-east-1,ca-central-1").split(",")
        if part.strip()
    )
    budget_monthly: float = float(os.getenv("MONTHLY_BUDGET", "10000"))
    sns_topic_arn: str | None = os.getenv("SNS_TOPIC_ARN")
    allowed_origins: tuple[str, ...] = tuple(
        part.strip()
        for part in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
        if part.strip()
    )


settings = Settings()
