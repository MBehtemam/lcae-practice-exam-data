"""Replay the committed experiments.json into the buyer's own LangSmith workspace.

The second script a buyer runs, after upload_traces.py. Reads the static, maintainer-generated
experiments.json (never calls an LLM or regenerates anything) and uploads the support-faq-eval
dataset plus its two compared experiments via langsmith.Client. See README.md for setup.
"""

import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

for _var in ("LANGSMITH_CURSOR_ENDPOINT", "LANGSMITH_CURSOR_PROJECT", "LANGSMITH_ENDPOINT",
             "LANGSMITH_PROJECT", "LANGSMITH_TRACING"):
    os.environ.pop(_var, None)

os.environ.setdefault("LANGSMITH_API_URL", "https://api.smith.langchain.com")

from langsmith import Client  # noqa: E402  (import after env setup, matches upload_traces.py)

EXPERIMENTS_PATH = Path(__file__).parent / "experiments.json"


def upload_experiment(client: Client, dataset_id: str, now: datetime, experiment: dict,
                       pending_feedback: list[tuple[str, str, dict]],
                       example_ids: dict[str, str]) -> None:
    project = client.create_project(experiment["name"], reference_dataset_id=dataset_id)

    for run in experiment["runs"]:
        # A fresh id per upload, not baked into experiments.json — a fixed id reused across
        # separate uploads (e.g. after reset.py deletes and recreates this project) collides with
        # the prior run of the same id server-side and breaks feedback attachment.
        run_id = str(uuid.uuid4())
        start_time = now
        end_time = start_time + timedelta(seconds=run["duration_seconds"])
        client.create_run(
            id=run_id,
            name="support_chat_completion",
            run_type="llm",
            inputs=run["inputs"],
            outputs=run["outputs"],
            reference_example_id=example_ids[run["reference_example_id"]],
            start_time=start_time,
            end_time=end_time,
            project_name=project.name,
        )
        for fb in run.get("feedback", []):
            pending_feedback.append((run_id, str(project.id), fb))


def main() -> None:
    data = json.loads(EXPERIMENTS_PATH.read_text())
    dataset_name = data["dataset_name"]

    client = Client()
    now = datetime.now(timezone.utc)

    # Without this the create_dataset below raises a raw 409 traceback, so there is no safe way
    # to merge into an existing dataset.
    existing = [dataset_name] if list(client.list_datasets(dataset_name=dataset_name)) else []
    existing += [e["name"] for e in data["experiments"]
                 if client.has_project(project_name=e["name"])]
    if existing:
        print("Already present in this workspace: " + ", ".join(f"'{n}'" for n in existing))
        print("Run `uv run python reset.py` first, then re-run this script.")
        sys.exit(1)

    # Example ids are unique across LangSmith, so the ids baked into experiments.json can already
    # belong to a dataset elsewhere (another workspace, or one deleted earlier), and create_examples
    # then 409s even on a fresh workspace. Mint fresh ids per upload and remap.
    example_ids = {example["id"]: str(uuid.uuid4()) for example in data["examples"]}

    dataset = client.create_dataset(dataset_name=dataset_name)
    client.create_examples(
        dataset_id=dataset.id,
        examples=[
            {
                "id": example_ids[example["id"]],
                "inputs": example["inputs"],
                "outputs": example["outputs"],
            }
            for example in data["examples"]
        ],
    )

    pending_feedback: list[tuple[str, str, dict]] = []
    for experiment in data["experiments"]:
        upload_experiment(client, dataset.id, now, experiment, pending_feedback, example_ids)

    # See upload_traces.py's main() for why runs must be flushed before feedback is attached.
    client.flush()
    for run_id, session_id, fb in pending_feedback:
        client.create_feedback(run_id=run_id, key=fb["key"], score=fb["score"], session_id=session_id)
    client.flush()

    print(f"Uploaded dataset '{dataset_name}' with {len(data['experiments'])} experiment(s).")
    print(f"https://smith.langchain.com/o/-/datasets/{dataset.id}")


if __name__ == "__main__":
    main()
