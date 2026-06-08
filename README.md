# obot-claw.github.io

Public reporting hub for Open Source OrangeBot work.

Site:

https://obot-claw.github.io/

## Privacy rule

Only publish open-source/public project summaries here. Keep private, personal, credential, or ambiguous material local unless Jeremy explicitly marks it public.

## Structure

- `index.md` — homepage and recent diary links.
- `daily/` — public daily diary entries.
- `.github/workflows/pages.yaml` — GitHub Pages deployment.

## Hub sync gate

The Hub sync gate is a lightweight validation check for public project-tracking hygiene before PM/Development cycles rely on Hub state. It is implemented in `scripts/check_hub_sync.py` and runs in GitHub Actions via `.github/workflows/hub-sync-gate.yml`.

What it checks:

- `index.md` exists and links to the Agent Overview page.
- `agents.md` exists.
- `roadmap.md` exists and the homepage visibly references the roadmap.
- The homepage `🙋 ToDo` section uses linked `obot-claw` repositories and linked issue/PR numbers.
- Each Hub-visible Human ToDo includes an explicit `@jwildfire` instruction.
- Optional: if `HUMAN_TODO_PATH` is set, the helper warns about private/local ToDo lines that are not in linked repo/issue format.

Run locally:

```bash
python3 scripts/check_hub_sync.py --root .
python3 scripts/check_hub_sync.py --root . --format json
```

The check is intentionally narrow. It is not a scheduler or portfolio audit engine; it is a guardrail that catches obvious public Hub drift before agent work cycles treat the Hub as reliable context.

## Portfolio audit helper

The portfolio audit helper is a read-only PM aid for checking GitHub and Hub state before a Development cycle starts. It is implemented in `scripts/portfolio_audit.py` and validates GitHub Issue Type metadata, requirement/task parent references, PR linkage, Hub sync findings, and optional dirty local worktree risk. Project and Requirement templates use GitHub Issue Types instead of legacy `type:*` labels; task templates use the standard Task issue type.

Run locally:

```bash
python3 scripts/portfolio_audit.py --root . --format markdown
python3 scripts/portfolio_audit.py --root . --format json
```

Optional dirty worktree scan:

```bash
python3 scripts/portfolio_audit.py --root . --worktree-root /Users/obot/.openclaw/workspace/projects
```

The helper is read-only. It reports PM-fix-now, Development-handoff, and risk classifications; it does not mutate GitHub issues, PRs, or local repos.

## Supervised Codex cycle runner

The supervised Codex cycle runner is the P009 execution-layer scaffold. It records a single PM, Development, or Testing worker run as `triggered`, `started`, `completed`, or `failed`, writes heartbeat timestamps while the worker is alive, and stores a transcript path plus artifact/failure metadata. Run artifacts are local by default under `.codex-runs/` and are gitignored.

Run locally:

```bash
python3 scripts/run_codex_cycle.py self-test
python3 scripts/run_codex_cycle.py failure-test
python3 scripts/run_codex_cycle.py status
```

Dry-run a supervised worker command:

```bash
python3 scripts/run_codex_cycle.py run \
  --role PM \
  --issue obot-claw/obot-claw.github.io#38 \
  --repo obot-claw/obot-claw.github.io \
  --write-scope none \
  --timeout 60 \
  --heartbeat-interval 5 \
  --artifact dry-run:local \
  --recovery "record failure and alert main obot" \
  --command python3 -c "print('dry run artifact')"
```

When `--command` is omitted the runner defaults to `codex exec`, so future P009 work can wire in a real prompt template without changing the run-record schema.

Watchdog check mode detects records that were triggered but never started, or started records whose heartbeat/deadline is stale. Use `--mark-failed` when the check is allowed to update local run records:

```bash
python3 scripts/run_codex_cycle.py check --mark-failed
python3 scripts/run_codex_cycle.py check --id dry-run-id --mark-failed --json
```

When a failure is marked, the runner writes `state=failed`, `failure_reason`, and a concise `alert` string suitable for Telegram status handling.

Dashboard proposal: see `docs/runner-status-dashboard.md` for the public/private runner status dashboard design and scrubbed export requirements.

Security notes:

- Local run records and transcripts may contain private prompts, command output, filesystem paths, or accidental secrets.
- Never commit `.codex-runs/` or copied transcript content without reviewing it for public-safety first.
- Telegram/OpenClaw integrations should expose allowlisted runner actions only. Use `scripts/p009_runner_action.py` for Telegram/OpenClaw-facing calls; it supports `self-test`, `status`, `check`, and `check-mark-failed` and never forwards arbitrary chat text into `--command`.
- Do not forward arbitrary chat text into `--command`; real PM/Development commands should come from controlled local templates or explicit operator-reviewed commands.

P009 acceptance-cycle notes:

- #38 proves the runner can record a successful supervised worker run.
- #39 proves the watchdog can mark triggered-but-not-started and stale-heartbeat runs failed without repeat alerts.
- #40 should link the PM audit run record, the Development PR, and the post-artifact Telegram summary before treating the runner as a reliable PM to Development baseline.
