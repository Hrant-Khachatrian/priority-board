import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server import create_server


class PriorityBoardServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "data").mkdir()
        source = Path(__file__).resolve().parents[1] / "data" / "board.example.json"
        (self.root / "data" / "board.example.json").write_text(
            source.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (self.root / "index.html").write_text("<h1>Priority Board</h1>", encoding="utf-8")
        self.server = create_server(root=self.root, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def get_board(self):
        with urllib.request.urlopen(f"{self.base}/api/board") as response:
            self.assertEqual(response.status, 200)
            return json.load(response)

    def post_board(self, board, *, base_revision=None, expected_status=200, **metadata):
        board = json.loads(json.dumps(board))
        embedded_revision = board.pop("_revision", None)
        payload = json.dumps(
            {
                "board": board,
                "baseRevision": base_revision or embedded_revision,
                **metadata,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base}/api/board",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request) as response:
                self.assertEqual(response.status, expected_status)
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code != expected_status:
                raise
            return json.load(error)

    def test_first_run_copies_example_board(self):
        board = self.get_board()
        self.assertGreaterEqual(len(board["categories"]), 1)
        self.assertTrue((self.root / "data" / "board.json").exists())

    def test_interface_includes_mobile_width_and_full_task_form(self):
        interface = (
            Path(__file__).resolve().parents[1] / "index.html"
        ).read_text(encoding="utf-8")
        self.assertIn("calc(100vw - 32px)", interface)
        self.assertIn("min-width:320px", interface)
        self.assertIn("newTaskDraft", interface)
        self.assertIn("refreshRecommendationTiers", interface)
        self.assertIn("cycleRecommendationTier", interface)
        self.assertIn("deleteArmedTaskId", interface)
        self.assertIn("board_conflict_merged", interface)

    def test_stale_save_preserves_missing_category(self):
        stale = self.get_board()
        current = json.loads(json.dumps(stale))
        current["categories"].append({"id": "empty", "name": "Empty"})
        self.post_board(current)

        stale["tasks"][0]["title"] = "Edited in a stale tab"
        conflict = self.post_board(stale, expected_status=409)

        category_ids = {category["id"] for category in conflict["board"]["categories"]}
        self.assertIn("empty", category_ids)
        self.assertEqual(conflict["error"], "revision_conflict")

    def test_explicit_deletion_removes_empty_category_and_logs_event(self):
        board = self.get_board()
        board["categories"].append({"id": "empty", "name": "Empty"})
        self.post_board(board)

        changed = self.get_board()
        changed["categories"] = [
            category for category in changed["categories"] if category["id"] != "empty"
        ]
        event = {
            "type": "category_deleted",
            "categoryId": "empty",
            "categoryName": "Empty",
        }
        self.post_board(
            changed,
            deletedCategoryIds=["empty"],
            events=[event],
        )

        category_ids = {category["id"] for category in self.get_board()["categories"]}
        self.assertNotIn("empty", category_ids)
        log = (self.root / "data" / "activity-log.jsonl").read_text(encoding="utf-8")
        self.assertIn('"type": "category_deleted"', log)

    def test_explicit_task_deletion_removes_task_and_logs_event(self):
        board = self.get_board()
        task = board["tasks"][0]
        board["tasks"] = [item for item in board["tasks"] if item["id"] != task["id"]]
        self.post_board(
            board,
            deletedTaskIds=[task["id"]],
            events=[{"type": "task_deleted", "taskId": task["id"]}],
        )

        task_ids = {item["id"] for item in self.get_board()["tasks"]}
        self.assertNotIn(task["id"], task_ids)
        log = (self.root / "data" / "activity-log.jsonl").read_text(encoding="utf-8")
        self.assertIn('"type": "task_deleted"', log)

    def test_server_rejects_orphaned_tasks(self):
        board = self.get_board()
        category_id = board["tasks"][0]["categoryId"]
        board["categories"] = [
            category for category in board["categories"] if category["id"] != category_id
        ]
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.post_board(board, deletedCategoryIds=[category_id])
        self.assertEqual(raised.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
