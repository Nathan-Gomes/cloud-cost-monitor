from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .alerts import publish_findings
from .aws_collector import AwsCollector
from .config import settings
from .dashboard import build_dashboard
from .database import create_repository
from .detectors import run_detectors
from .sample_data import generate_cost_records, generate_resources


repository = create_repository(settings.database_path, settings.database_url)


def collect(mode: str | None = None):
    active_mode = mode or settings.app_mode
    if active_mode == "aws":
        collector = AwsCollector(settings.monitored_regions)
        costs = collector.collect_costs()
        resources = collector.collect_resources()
    else:
        costs = generate_cost_records()
        resources = generate_resources()
        active_mode = "demo"
    findings = run_detectors(costs, resources)
    repository.replace_snapshot(costs, resources, findings)
    publish_findings(settings.sns_topic_arn, findings)
    return build_dashboard(costs, resources, findings, active_mode, settings.budget_monthly)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not repository.list_costs():
        collect()
    yield


app = FastAPI(title="Cloud Cost and Resource Monitor", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": settings.app_mode}


@app.get("/api/dashboard")
def dashboard():
    costs = repository.list_costs()
    if not costs:
        raise HTTPException(status_code=503, detail="No collection has completed")
    return build_dashboard(
        costs,
        repository.list_resources(),
        repository.list_findings(),
        settings.app_mode,
        settings.budget_monthly,
    )


@app.post("/api/collect")
def run_collection():
    return collect()
