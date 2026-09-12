"""Replay the committed traces.json into the buyer's own LangSmith workspace.

The only script a buyer runs. Reads the static, maintainer-generated traces.json (never calls an
LLM or regenerates anything) and uploads it via langsmith.Client. See README.md for setup.
"""

import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Strip ambient LANGSMITH_* env vars the SDK would otherwise auto-capture onto every run's
# metadata, so the version/user_id we set explicitly stay easy to find in the UI — same defense
# the reference lcae-practice-exam repo uses.
for _var in ("LANGSMITH_CURSOR_ENDPOINT", "LANGSMITH_CURSOR_PROJECT", "LANGSMITH_ENDPOINT",
             "LANGSMITH_PROJECT", "LANGSMITH_TRACING"):
    os.environ.pop(_var, None)

os.environ.setdefault("LANGSMITH_API_URL", "https://api.smith.langchain.com")

from langsmith import Client  # noqa: E402  (import after env setup, matches reference repo)

TRACES_PATH = Path(__file__).parent / "traces.json"


def _dotted_order_segment(start_time: datetime, run_id: str) -> str:
    # LangSmith's run-tree ordering key: a UTC timestamp plus the run id, chained with "." per
    # ancestor. Required by the API whenever trace_id is set (root or child).
    return f"{start_time.strftime('%Y%m%dT%H%M%S%fZ')}{run_id}"


def upload_run(client: Client, project_name: str, trace_metadata: dict, run: dict,
                trace_id: str, parent_run_id: str | None, parent_dotted_order: str | None,
                start_time: datetime, pending_feedback: list[tuple[str, dict]],
                run_id: str | None = None) -> None:
    run_id = run_id or str(uuid.uuid4())
    end_time = start_time + timedelta(seconds=run.get("duration_seconds", 1))
    segment = _dotted_order_segment(start_time, run_id)
    dotted_order = f"{parent_dotted_order}.{segment}" if parent_dotted_order else segment

    client.create_run(
        id=run_id,
        trace_id=trace_id,
        dotted_order=dotted_order,
        name=run["name"],
        run_type=run.get("run_type", "chain"),
        inputs=run.get("inputs", {}),
        outputs=run.get("outputs"),
        error=run.get("error"),
        start_time=start_time,
        end_time=end_time,
        parent_run_id=parent_run_id,
        project_name=project_name,
        extra={"metadata": {**trace_metadata, **run.get("metadata", {})}},
    )

    for child in run.get("children", []):
        upload_run(client, project_name, trace_metadata, child, trace_id, run_id, dotted_order,
                   start_time + timedelta(seconds=1), pending_feedback)

    for fb in run.get("feedback", []):
        pending_feedback.append((run_id, fb))


def main() -> None:
    data = json.loads(TRACES_PATH.read_text())
    project_name = data["project_name"]
    traces = data["traces"]

    client = Client()

    # create_run auto-creates the project, so a second upload would silently append a duplicate
    # copy of every trace and skew the counts the practice questions ask about. Stop instead.
    if client.has_project(project_name=project_name):
        print(f"Project '{project_name}' already exists in this workspace.")
        print("Run `uv run python reset.py` first, then re-run this script.")
        sys.exit(1)
    now = datetime.now(timezone.utc)
    pending_feedback: list[tuple[str, dict]] = []

    for trace in traces:
        start_time = now + timedelta(minutes=trace.get("start_offset_minutes", 0))
        root_run_id = str(uuid.uuid4())
        upload_run(
            client,
            project_name,
            trace.get("metadata", {}),
            trace["root"],
            trace_id=root_run_id,
            parent_run_id=None,
            parent_dotted_order=None,
            start_time=start_time,
            pending_feedback=pending_feedback,
            run_id=root_run_id,
        )

    # Runs are queued and sent asynchronously by the SDK's background thread; flushing here
    # guarantees every run has actually landed server-side before we attach feedback to it (a
    # feedback call against a run that hasn't been ingested yet 404s as "Session not found").
    client.flush()
    session_id = client.read_project(project_name=project_name).id
    for run_id, fb in pending_feedback:
        client.create_feedback(run_id=run_id, key=fb["key"], score=fb["score"], session_id=session_id)
    client.flush()

    print(f"Uploaded {len(traces)} trace(s) to project '{project_name}'.")
    print(f"https://smith.langchain.com/o/-/projects/p/{project_name}")


if __name__ == "__main__":
    main()
