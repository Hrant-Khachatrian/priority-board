# Priority Board

A compact, local-first planning board for people whose work spans many
categories. It combines urgency and importance, due dates, estimates, actual
time tracking, recurring tasks, waiting/blocked states, and a durable activity
log.

The interface is intentionally dense: four or more categories can remain
visible at once, and each task exposes the information needed for daily
planning without opening a modal.

## Features

- Drag tasks between editable categories
- Rename, reorder, add, and safely delete categories
- Four-level urgency and importance controls
- Automatic urgency from due dates:
  - 4: today or overdue
  - 3: tomorrow
  - 2: within three days
  - 1: later
- Sort and filter by urgency and importance
- Estimates and editable actual time
- Play/pause timers with persisted checkpoints
- Weekly recurring tasks
- Ready, waiting, and blocked states
- Completed-task visibility toggle
- Optional tags and next-action notes
- Core and second-tier recommendation colors
- Append-only JSONL activity log for later analysis
- JSON files remain on your computer

## Quick start

### With a coding agent

The easiest way to start is to open Codex, Claude Code, or a similar coding
agent in a new project and submit this prompt:

> Install [Hrant-Khachatrian/priority-board](https://github.com/Hrant-Khachatrian/priority-board) on my machine and start it.

The agent can clone the repository, check that Python is available, start the
local server, and give you the URL to open.

### Manually

Priority Board has no third-party runtime dependencies. It needs Python 3.10 or
newer.

```bash
git clone https://github.com/Hrant-Khachatrian/priority-board.git
cd priority-board
python3 server.py
```

On Windows, `py server.py` may be used instead. Open
[http://127.0.0.1:4175](http://127.0.0.1:4175).

Choose another port when needed:

```bash
python3 server.py --port 8080
```

The server binds to localhost by default. This is deliberate: the app has no
authentication and is designed as a private, single-user tool.

## Your data

On first launch, `data/board.example.json` is copied to
`data/board.json`. All subsequent changes are written to:

- `data/board.json` — current board state
- `data/activity-log.jsonl` — timestamped task and planning events

Both runtime files are excluded from Git, so cloning, committing, or updating
the application will not publish your tasks.

Back up the `data` directory if the board becomes important to your workflow.

## Category deletion

The × button in a category header deletes an empty category after confirmation.
A category containing tasks cannot be deleted: move its tasks elsewhere first.
This prevents accidental task loss.

The server also distinguishes an explicit deletion from an old browser tab
that is merely missing newer data. Missing records are preserved unless the
request explicitly marks them for deletion.

## Task fields

The board accepts normal JSON. A minimal task looks like this:

```json
{
  "id": "review-results",
  "title": "Review experiment results",
  "categoryId": "research",
  "urgency": 4,
  "importance": 4,
  "estimateMinutes": 90,
  "actualSeconds": 0,
  "status": "active",
  "tags": ["analysis"],
  "nextAction": "Summarize the findings."
}
```

Optional fields include `dueDate`, `recurrence`, `seriesId`,
`recommendationTier`, and completion/timer timestamps. Recommendation tier
values are `core` and `second`; tasks without the field retain the neutral
card color.

## Activity log

The log is newline-delimited JSON. Events include timer starts and pauses,
estimate changes, corrected actual time, priority and status changes,
completions, recurring-task creation, and category deletion.

The log is intended for later analysis of estimation accuracy, planning
overhead, work fragmentation, and recurring bottlenecks. It is not required to
render the board and can be archived independently.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The integration tests use a temporary data directory and do not touch your
board.

## Project structure

```text
priority-board/
├── index.html                  # Entire browser interface
├── server.py                   # Static server and JSON API
├── data/
│   └── board.example.json      # Safe starter data
└── tests/
    └── test_server.py          # Persistence and deletion tests
```

## Security and scope

Priority Board is a local, single-user application. Do not expose it directly
to the public internet. If you want multi-user or remote access, add
authentication, authorization, TLS, and a production-grade data store.

## License

[MIT](LICENSE)
