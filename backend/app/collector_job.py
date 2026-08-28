from .main import collect


if __name__ == "__main__":
    result = collect()
    print(f"Collected {result.summary['monitored_resources']} resources and produced {result.summary['active_findings']} findings.")

