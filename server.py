#!/usr/bin/env python3
"""Local JSON-backed server for Priority Board."""

from __future__ import annotations

import argparse
import json
import shutil
import threading
import uuid
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

SAVE_LOCK = threading.Lock()
MAX_BODY_BYTES = 10 * 1024 * 1024


def ensure_data_files(root: Path) -> tuple[Path, Path]:
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    board_path = data_dir / "board.json"
    example_path = data_dir / "board.example.json"
    log_path = data_dir / "activity-log.jsonl"

    if not board_path.exists():
        if not example_path.exists():
            raise FileNotFoundError(f"Missing seed file: {example_path}")
        shutil.copyfile(example_path, board_path)
    log_path.touch(exist_ok=True)
    return board_path, log_path


def validate_board(board: object) -> None:
    if not isinstance(board, dict):
        raise ValueError("Board must be a JSON object.")
    categories = board.get("categories")
    tasks = board.get("tasks")
    if not isinstance(categories, list) or not isinstance(tasks, list):
        raise ValueError("Board needs categories and tasks lists.")

    category_ids: set[str] = set()
    for category in categories:
        if not isinstance(category, dict):
            raise ValueError("Every category must be an object.")
        category_id = category.get("id")
        if not isinstance(category_id, str) or not category_id:
            raise ValueError("Every category needs a non-empty string id.")
        if category_id in category_ids:
            raise ValueError(f"Duplicate category id: {category_id}")
        if not isinstance(category.get("name"), str) or not category["name"].strip():
            raise ValueError(f"Category {category_id} needs a name.")
        category_ids.add(category_id)

    task_ids: set[str] = set()
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError("Every task must be an object.")
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id:
            raise ValueError("Every task needs a non-empty string id.")
        if task_id in task_ids:
            raise ValueError(f"Duplicate task id: {task_id}")
        if task.get("categoryId") not in category_ids:
            raise ValueError(f"Task {task_id} refers to a missing category.")
        if not isinstance(task.get("title"), str):
            raise ValueError(f"Task {task_id} needs a title.")
        for field in ("urgency", "importance"):
            value = task.get(field)
            if not isinstance(value, int) or not 1 <= value <= 4:
                raise ValueError(f"Task {task_id} has invalid {field}.")
        if not isinstance(task.get("estimateMinutes"), (int, float)) or task["estimateMinutes"] < 0:
            raise ValueError(f"Task {task_id} has invalid estimateMinutes.")
        if not isinstance(task.get("actualSeconds", 0), (int, float)) or task.get("actualSeconds", 0) < 0:
            raise ValueError(f"Task {task_id} has invalid actualSeconds.")
        task_ids.add(task_id)


def merge_board(
    existing: dict,
    incoming: dict,
    deleted_category_ids: set[str],
    deleted_task_ids: set[str],
) -> dict:
    """Protect against stale tabs while honoring explicit deletions."""
    merged = json.loads(json.dumps(incoming))
    incoming_category_ids = {item.get("id") for item in merged["categories"]}
    incoming_task_ids = {item.get("id") for item in merged["tasks"]}

    merged["categories"].extend(
        item
        for item in existing.get("categories", [])
        if item.get("id") not in incoming_category_ids
        and item.get("id") not in deleted_category_ids
    )
    merged["tasks"].extend(
        item
        for item in existing.get("tasks", [])
        if item.get("id") not in incoming_task_ids
        and item.get("id") not in deleted_task_ids
    )
    return merged


def atomic_write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


class BoardHandler(SimpleHTTPRequestHandler):
    root_dir: Path
    board_path: Path
    activity_log_path: Path

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(self.root_dir), **kwargs)

    def _send_json(self, value: object, status: int = 200) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/api/board":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(self.board_path.stat().st_size))
            self.end_headers()
            self.wfile.write(self.board_path.read_bytes())
            return
        if path == "/api/log":
            body = self.activity_log_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/api/board":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY_BYTES:
                raise ValueError("Invalid request body size.")
            payload = json.loads(self.rfile.read(length))
            board = payload.get("board", payload)
            events = payload.get("events", [])
            deleted_category_ids = set(payload.get("deletedCategoryIds", []))
            deleted_task_ids = set(payload.get("deletedTaskIds", []))
            if payload.get("event"):
                events.append(payload["event"])
            if not isinstance(events, list):
                raise ValueError("Events must be a list.")
            if not all(isinstance(event, dict) for event in events):
                raise ValueError("Every event must be an object.")

            validate_board(board)
            with SAVE_LOCK:
                existing = json.loads(self.board_path.read_text(encoding="utf-8"))
                merged = merge_board(
                    existing,
                    board,
                    deleted_category_ids,
                    deleted_task_ids,
                )
                validate_board(merged)
                atomic_write_json(self.board_path, merged)

                if events:
                    with self.activity_log_path.open("a", encoding="utf-8") as log:
                        for event in events:
                            record = {
                                "id": str(uuid.uuid4()),
                                "recordedAt": datetime.now(timezone.utc).isoformat(),
                                **event,
                            }
                            log.write(json.dumps(record, ensure_ascii=False) + "\n")
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            self._send_json({"error": str(error)}, status=400)
            return

        self.send_response(204)
        self.end_headers()


def create_server(
    root: Path | None = None,
    host: str = "127.0.0.1",
    port: int = 4175,
) -> ThreadingHTTPServer:
    root = (root or Path(__file__).resolve().parent).resolve()
    board_path, log_path = ensure_data_files(root)
    handler = type(
        "ConfiguredBoardHandler",
        (BoardHandler,),
        {
            "root_dir": root,
            "board_path": board_path,
            "activity_log_path": log_path,
        },
    )
    return ThreadingHTTPServer((host, port), handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Priority Board locally.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4175)
    args = parser.parse_args()

    server = create_server(host=args.host, port=args.port)
    url = f"http://{args.host}:{server.server_address[1]}"
    print(f"Priority Board is running at {url}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
