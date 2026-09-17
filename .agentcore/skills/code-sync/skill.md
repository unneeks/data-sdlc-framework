---
name: code-sync
description: Sync code and publish documents through S3 when direct network access to source control is unavailable.
risk_level: MEDIUM
deterministic: true
dependencies: []
tools:
  - sync_code_from_s3
  - push_code_to_s3
  - publish_documents
input_schema:
  type: object
  properties:
    session_id:
      type: string
      description: The current session id, resolved automatically — never pass it yourself.
output_schema:
  type: object
---

# Code Sync

This environment has no direct network access to source control — only to
S3. Code changes and documents move through S3 as the transport, and the
orchestrator watching that S3 event log applies them to the real local
repository on your behalf. You never need to know how that happens; just
follow the workflow below.

## Tools

- `sync_code_from_s3` — Fetch the current code baseline into a scratch
  workspace and create your working branch. Call this ONCE at the start
  of your work. Calling it again in the same session is safe and returns
  the same workspace.
- `push_code_to_s3` — Write your file changes, commit them, and publish
  the result. Pass every changed/added file's full new content and any
  paths to delete. Call this whenever you have a logically complete set
  of changes ready — once at the end of your work, or multiple times for
  incremental checkpoints.
- `publish_documents` — Publish one or more finished documents (specs,
  reports, test plans, etc.) you produced this session. Pass all of them
  in a single call when possible; each publish notifies the orchestrator.

## Workflow

1. Call `sync_code_from_s3` before making any edits.
2. Make your changes conceptually, then call `push_code_to_s3` with the
   full content of every file you changed, an optional list of files to
   delete, and a commit message describing the change.
3. If you produced documents (not source code), call `publish_documents`
   with all of them once you're done.
4. You do not need to wait for confirmation that the sync landed in the
   developer's real repository — that happens asynchronously, out of band.
5. If `sync_code_from_s3` reports no baseline exists yet, stop and report
   that the repo-sync bootstrap step has not been run — do not attempt to
   invent a baseline yourself.

## Usage

Referenced by agents with `skills: [code-sync]` in their instructions file.
