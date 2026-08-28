import json
from pathlib import Path

from backend.app.dashboard import build_dashboard
from backend.app.detectors import run_detectors
from backend.app.sample_data import generate_cost_records, generate_resources


def main():
    costs = generate_cost_records()
    resources = generate_resources()
    findings = run_detectors(costs, resources)
    dashboard = build_dashboard(costs, resources, findings, "demo", 10000)
    destination = Path(__file__).parent / "frontend" / "public" / "demo-data.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(dashboard.model_dump(mode="json"), indent=2), encoding="utf-8")
    print(f"Wrote {destination} with {len(findings)} findings")


if __name__ == "__main__":
    main()
