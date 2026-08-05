# Priority Board

A compact, local-first planning board for people whose work spans many
categories. It combines urgency and importance, due dates, estimates, actual
time tracking, recurring tasks, waiting/blocked states, and a durable activity
log.

The interface is intentionally dense: four or more categories can remain
visible at once, and each task exposes the information needed for daily
planning without opening a modal.

## Note from the creator

> This is my ~10th attempt to organize my work through some platform. The
> previous ones included physical notebooks and whiteboards, note-taking apps,
> Asana, Trello, Google Sheets, Notion and my own vibe-coded app. Let's see how
> long this one will survive.

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
- Manually assignable core and second-tier recommendation colors
- Inline two-step task deletion
- Revision-aware saves that merge concurrent edits instead of silently
  overwriting another browser tab
- Append-only JSONL activity log for later analysis
- JSON files remain on your computer
- Responsive mobile layout with swipeable, nearly full-width categories

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

## Deploy on ChatGPT.site

Priority Board can also be deployed privately on
[ChatGPT.site](https://chatgpt.site) for access from desktop and mobile
browsers. A hosted deployment can use ChatGPT sign-in for access control and
D1 for durable board state and activity logs, so changes persist and remain
available across devices.

The easiest route is to open this repository in Codex and submit:

> Convert this Priority Board into a private ChatGPT Site. Preserve the current
> interface and behavior, use D1 for the board and activity log, and deploy it
> to ChatGPT.site.

The local and hosted storage backends are separate. Treat `data/board.json` and
`data/activity-log.jsonl` as private: only seed or migrate them into the hosted
database when you intentionally want that information online. Keep the
deployment owner-only unless you explicitly want to share the board.

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
request explicitly marks them for deletion. Revision-aware saves let the
browser merge non-conflicting changes made in another tab or device and retry
without silently replacing the newer board.

Tasks have a small × control. The first click arms deletion and changes the
control to **Delete**; the second click performs the deletion. This avoids
browser confirmation dialogs while still protecting against accidental taps.

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
Task deletions and automatic conflict merges are logged as well.

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

The included Python server is a local, single-user application. Do not expose
it directly to the public internet. For remote access, use an authenticated
deployment such as a private ChatGPT Site with durable server-side storage.

## License

[MIT](LICENSE)
