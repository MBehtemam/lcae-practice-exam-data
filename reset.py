"""Delete everything upload_traces.py / upload_experiments.py create, for a clean re-upload.

Run this before re-running the two upload scripts (e.g. before each practice attempt) instead of
re-running them directly — re-running without a reset appends a fresh, duplicate copy of every
trace/run on top of whatever is already there (see README.md), which skews the very metrics the
Monitor-domain Questions ask about.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

for _var in ("LANGSMITH_CURSOR_ENDPOINT", "LANGSMITH_CURSOR_PROJECT", "LANGSMITH_ENDPOINT",
             "LANGSMITH_PROJECT", "LANGSMITH_TRACING"):
    os.environ.pop(_var, None)

os.environ.setdefault("LANGSMITH_API_URL", "https://api.smith.langchain.com")

from langsmith import Client  # noqa: E402  (import after env setup, matches the upload scripts)

TRACES_PATH = Path(__file__).parent / "traces.json"
EXPERIMENTS_PATH = Path(__file__).parent / "experiments.json"


def delete_project_if_exists(client: Client, project_name: str) -> None:
    if client.has_project(project_name=project_name):
        client.delete_project(project_name=project_name)
        print(f"Deleted project '{project_name}'.")
    else:
        print(f"Project '{project_name}' not found, nothing to delete.")


def delete_dataset_if_exists(client: Client, dataset_name: str) -> None:
    datasets = list(client.list_datasets(dataset_name=dataset_name))
    if not datasets:
        print(f"Dataset '{dataset_name}' not found, nothing to delete.")
        return
    for dataset in datasets:
        client.delete_dataset(dataset_id=dataset.id)
        print(f"Deleted dataset '{dataset_name}' ({dataset.id}).")


def main() -> None:
    client = Client()

    traces_data = json.loads(TRACES_PATH.read_text())
    delete_project_if_exists(client, traces_data["project_name"])

    experiments_data = json.loads(EXPERIMENTS_PATH.read_text())
    for experiment in experiments_data["experiments"]:
        delete_project_if_exists(client, experiment["name"])
    delete_dataset_if_exists(client, experiments_data["dataset_name"])

    print("Reset complete. Re-run upload_traces.py and upload_experiments.py for a clean slate.")


if __name__ == "__main__":
    main()
