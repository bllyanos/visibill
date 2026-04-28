# Backlog Guide

Use `backlog.yaml` as the source of truth for backlog items.

When a user says something like `let's pickup task <id>` or asks to pick up a backlog task, interpret it as:

1. Find `<id>` under `backlog.yaml -> backlogs`.
2. Read the task's `status`, `description`, and `plan`.
3. Treat the backlog entry as the active source of context for the work.
4. If the task is missing or ambiguous, ask a short clarification before changing anything.
5. If the task exists, continue the work from that backlog item and update `status` as needed.

Structure:

```yaml
backlogs:
  <id>:
    status: pending|in_progress|blocked|done|cancelled
    description: |
      Multi-line description is allowed.
      Keep it short and specific.
    plan: |
      Multi-line plan is allowed.
      Leave this empty if the plan is not decided yet.
```

Rules:

- Each backlog item must have a stable `<id>` key.
- `status` is required.
- `description` is required and may use YAML block scalars for multiple lines.
- `plan` is optional in content, and may be empty with `plan: ""` or a block scalar with no text.
- Keep entries focused on a single task or outcome.
- Prefer updating the existing item rather than creating duplicates.
- Use `pending` for not started, `in_progress` for active work, `blocked` when waiting, `done` when finished, and `cancelled` when no longer needed.
- When picking up a task, use the backlog entry's `description` and `plan` as the instructions for what to do next.

Example:

```yaml
backlogs:
  advanced-filtering-followup:
    status: done
    description: |
      Track follow-up work for the advanced filtering feature.
    plan: |
      Add quoted value support if users need spaces in structured queries.
```
