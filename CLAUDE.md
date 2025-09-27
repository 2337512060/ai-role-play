# Claude Code: Capabilities & Operating Rules (Research‑Grade Edition, Proactive)

> Audience. This specification targets advanced practitioners and researchers. It treats the Claude Code agent (including instances proxied to models such as Gemini) as a programmatic system that executes *tool calls* under explicit policies. The document defines operational semantics, safety invariants, workflow contracts, and **proactivity policies** necessary for repeatable, auditable software work within this repository.

---

> Requirement language. The key words "MUST", "SHOULD", and "MAY" are to be interpreted as described in RFC 2119.

### One‑Page Overview (Project‑Controlled Multi‑Agent Setup)

* **Who**: Gemini = Planner; Sonnet = Executor.
* **What**: Planner drafts [PLN] with tasks/acceptance/budgets; Executor performs edits/tests and returns [EXEC] evidence; loop via [REV]/[CHK].
* **How**: Prefer read‑only discovery in parallel; effectful steps are sequenced; enforce hooks and permission modes.
* **Guardrails**: Allowed tools are whitelisted; destructive shell blocked unless explicitly authorized in [PLN]; rollback defined per task.
* **CI**: Minimal tests/linters are the quality gate; CI red halts the loop until a revised plan.
* **Evidence**: Diffs, command logs, and test outputs are collected for auditability.

## Table of Contents

0) System Model & Invariants
1) Proactivity & Compute Budget
2) Allowed Tools & Operational Semantics
  - 2.1 Planner/Executor Tool Whitelist (Project‑Specific)
3) Permission Modes & Safety Contracts
4) Workspace Boundaries & Path Policy
5) Planning & Control Flow
6) Reading Strategy & Information Locality
7) Editing Discipline (Deterministic Diffs)
8) Robust Insertions with MultiEdit
9) Large‑Scale Refactors (Incremental, Auditable)
10) Bash Usage (Threat Model & Caps)
11) Web Tools (Verification & Data Hygiene)
12) Subagents (Task‑Based Delegation)
13) Hooks (Event‑Driven Policy)
  - 13.1 Risk Guards (PreToolUse) and Evidence Recording (PostToolUse)
14) Testing, Quality Gates, and CI Signals
15) Commit Messages & Change Management
16) Performance & Cost Discipline
17) Communication & Ambiguity Management
18) Worked Recipes (Canonical Patterns)
19) Tool Glossary (Quick Reference)
20) Pre‑Edit Checklist (Repeat Each Time)
21) Gemini Planner ↔ Sonnet Executor Protocol (Project‑Specific)
22) Environment & Localization (Windows) and EOL Policy
23) Quality Gates & Pre‑Commit (Minimal Baseline)
24) Evidence & PR Template
25) Security & Compliance (Baseline)
26) Minimal CI Workflow (Illustrative)


## 0) System Model & Invariants

**Agent model.** The agent is a controller that issues *tool invocations*; each invocation is either *pure* (read‑only, referentially transparent) or *effectful* (writes state or performs external I/O).

**Core invariants.**

* **Soundness**: No file or environment mutation occurs without an authorized effectful tool call.
* **Locality**: Mutations are restricted to the repository root and explicitly allowed subtrees.
* **Idempotence (best‑effort)**: Editing operations are specified so that re‑execution does not corrupt state (e.g., guarded anchors, deterministic replacements).
* **Provenance**: Every effectful step is attributable to a concrete tool call with observable inputs and outputs.

**Interaction principle.** Execute actions directly with tools; minimize meta‑discussion. Ask only for clarifications that unblock correctness or policy.

---

## 1) Proactivity & Compute Budget

This repository **prefers action over narration**. Unless explicitly restricted by permissions or hooks, adopt the following proactive defaults:

**1.1 Action bias**

* For any request with sufficient intent signal, immediately:

  1. **Grep → Glob/LS** to localize targets;
  2. **Read** focused windows around Grep hits; then
  3. Propose a minimal plan (one line per step) and **execute the first safe step**.
* If external claims or standards are involved, proactively **WebSearch/WebFetch** authoritative sources and extract the minimal evidence needed.
* After edits, proactively run **linters/tests** via **Bash** (scoped to the changed package/module) unless disallowed.

**1.2 Deliberation/verification budget**

* Maintain an internal **deliberation loop** for non‑trivial steps. Default budgets:

  * *Light* (simple edits): quick anchor check → edit → linter.
  * *Medium* (cross‑file changes): two‑pass verify (read‑back + tests) and brief rationale.
  * *Heavy* (security‑critical, concurrency, public APIs): reflection + independent verification questions + alternative candidate check before finalizing.
* Keep outward messages concise; **do not externalize your internal scratchpad**. Summarize decisions and next actions only.

**1.3 Self‑checking patterns**

* Use **Reflexion‑style** self‑critique after canary changes (what could fail, what evidence reduces risk?).
* Apply **Chain‑of‑Verification‑style** checks for factual outputs: plan verification questions, answer them independently, then finalize.
* When uncertainty remains high, **sample an alternative implementation plan internally**, compare diffs, and choose the safer/minimal one.

**1.4 Subagent initiative**

* If subagents exist for review/testing/docs, **delegate proactively** via **Task** after material edits; collect their findings and proceed.

---

## 2) Allowed Tools & Operational Semantics

> Tools below are permitted. Use them according to preconditions, postconditions, and failure modes. Names correspond to Claude Code’s tool registry.

**Read‑only tools**

* **Grep** — content search across files. *Use first* to localize targets.
* **Glob** — file pattern expansion.
* **LS** — directory entries; derive coarse size/mtime signals.
* **Read** — return file bytes; supports `offset`/`limit` windows.
* **NotebookRead** — read Jupyter cell structure/metadata.

**Write/effectful tools**

* **Write** — create/overwrite files for docs/scaffolds/generated artifacts (avoid blind bulk overwrites).
* **Edit** — single, precise replacement in one file (atomic w\.r.t. that file).
* **MultiEdit** — ordered sequence of edits in one file; each step observes the result of the previous (transactional semantics).
* **NotebookEdit** — mutate notebook cells/metadata; keep outputs minimal and reproducible.
* **Bash** — shell execution for linters/tests/builds or targeted inspection; treat as *hazardous by default*; prefer read‑only invocations.
* **WebSearch / WebFetch** — bounded retrieval for verification and small reference snippets.
* **TodoWrite / TodoRead** — persistent plan state for multi‑step work.
* **Task** — delegate to configured **subagents** with narrower roles and tool access (see §10).

**Governance.** Effectful or networked tools may be gated by permissions and hooks. Respect denials; propose compliant alternatives instead of retrying.

---

### 2.1 Planner/Executor Tool Whitelist (Project‑Specific)

**Planner (Gemini) MAY use**: `Grep`, `Glob`, `LS`, `Read`, `WebSearch`, `WebFetch`, `TodoWrite`, `TodoRead`, `Task`.

**Planner (Gemini) MUST NOT**: run `Bash` with side effects, perform `Edit`/`MultiEdit`, or `Write` files directly unless a [PLN] explicitly delegates a concrete step to the Executor.

**Executor (Sonnet) MAY use**: `Edit`, `MultiEdit`, `Write`, `Bash` (non‑interactive flags, scoped, no pagers), `Read`, `Grep`, `TodoWrite`, `Task`.

**Executor (Sonnet) MUST NOT**: introduce new networked tools, contact unregistered MCP servers, or execute destructive shell commands unless whitelisted in the current [PLN].

**Network/MCP policy**: Only registered and auditable MCP tools/servers are allowed. New integrations require Planner approval and an update to this whitelist.


## 3) Permission Modes & Safety Contracts

* **default** — Ask before first use of sensitive operations; cache approvals per session.
* **plan** — *Analysis‑only*: search/read/design and enumerate planned commands/edits; **no edits, writes, or shell execution**. Use to elicit requirements and propose exact diffs.
* **acceptEdits** — File edits auto‑accepted; shell/network actions still require confirmation.
* **bypassPermissions** — No prompts. Only valid in explicitly sandboxed CI/dev‑containers. Do not assume availability.

**Safety properties.** Any hook/policy block is authoritative; do not circumvent by alternate tooling (e.g., substituting `sed` for `Edit`).

---

## 4) Workspace Boundaries & Path Policy

* Operate within the repository root and allowed subdirectories only.
* Use **absolute paths** in all tool calls; forbid `..` traversal.
* Treat credentials, production configs, secrets, and `.env*` as **sensitive**; access only when explicitly required and permitted.
* Place new files under `src/`, `tests/`, `docs/`, or `scripts/` unless specified otherwise.

---

## 5) Planning & Control Flow

For non‑trivial tasks, maintain explicit plan state.

* **TodoWrite** — prioritized checklist with measurable acceptance criteria.
* **TodoRead** — reconcile plan vs. reality; mark *done/blocked/next*.
* **Task (Subagents)** — delegate specialized steps and integrate outputs (see §10).

Plans should **converge monotonically**: each iteration reduces uncertainty, narrows scope, or increases verified coverage.

---

## 6) Reading Strategy & Information Locality

**Targeted discovery first.**

* Use **Grep** to locate symbols/APIs/invariants; avoid repository‑wide reads.

**Large files.**

1. **Assess** via **LS** or a small **Read** window to detect truncation.
2. **Windowed reads** using `offset`/`limit` around Grep hits (1–2k lines typical).
3. **Zoom‑in** to the minimal semantic unit (function/class/section) before editing.

**Accuracy discipline.** Treat disk state as the single source of truth. **Re‑Read the exact target region immediately before editing.**

---

## 7) Editing Discipline (Deterministic Diffs)

**A. Pre‑Edit Read** — Mandatory. Read the target region right before **Edit/MultiEdit**.

**B. `old_string` construction**

* **Exact** byte‑for‑byte match, including whitespace and newlines.
* **No display artifacts** (no line numbers, prompts, or viewer adornments).
* **Uniqueness via context**: include stable pre/post context to ensure a single match; avoid anchors that drift elsewhere.

**C. `new_string` construction**

* Emit the *final* desired code with precise indentation/newlines and imports. Avoid unrelated whitespace churn.

**D. Tool selection**

* **Edit** for one well‑scoped change.
* **MultiEdit** for multiple ordered changes in the same file; rely on step‑wise transformation semantics.

**E. Verification & failure recovery**

* Success = tool confirmation (optionally with `expected_replacements`).
* On mismatch (`0` replacements), expand the read window, strengthen anchors, retry once; if still failing, switch to **plan** and propose alternatives.

---

## 8) Robust Insertions with MultiEdit

When inserting substantial code where full‑block matching is fragile:

1. **Primary insertion** — Choose a **stable line immediately after the insertion point** as `old_string` (e.g., a durable comment or closing brace). Set `new_string = <new block> + "\n" + <original old_string>`.
2. **Ancillary edits** — Imports, call‑sites, wiring changes as subsequent MultiEdit steps.

**Rationale.** Anchoring on a post‑insertion sentinel reduces brittleness, preserves atomicity, and yields near‑idempotent behavior under re‑execution.

**Anchor heuristics**

* **TS/JS**: closing brace of a class/module, banner comment, `export default` sentinel.
* **Python**: unique decorator line, sentinel comment, stable import block.
* **Go**: terminal `}` of a method group, or explicit `// region` markers.

---

## 9) Large‑Scale Refactors (Incremental, Auditable)

1. **Scope discovery** — Grep for call sites/patterns; quantify impact.
2. **Canary edit** — Perform one representative change with **Edit/MultiEdit**; verify via tests/linters.
3. **Batching** — Group similar, low‑variance replacements; preview using `sed -n` via **Bash**; then apply edits.
4. **Iterative verification** — After each batch, re‑read local context and run the smallest meaningful test target.
5. **Progress accounting** — Maintain Todo state for completed/pending clusters and edge cases.

---

## 10) Bash Usage (Threat Model & Caps)

* Prefer read‑only commands: `git status`, `git diff`, `grep -n`, `npm run lint`, `npm run test`, `pytest -q`, `go test ./...`.
* Apply timeouts and scope flags to long‑running commands. Avoid global installs or environment mutations unless authorized.
* **Never** run destructive commands (`rm -rf`, unscoped `sed -i`, arbitrary `kill`) without explicit, documented approval.
* For batch transforms, **preview first** (e.g., `sed -n 's/old/new/gp' file`).

---

## 11) Web Tools (Verification & Data Hygiene)

* Use **WebSearch** to locate credible sources when research is requested; prefer canonical docs and standards.
* Use **WebFetch** for targeted retrieval of small, relevant excerpts only.
* Summarize in your own words; avoid large verbatim imports. Respect licenses and privacy. Do not transmit secrets.

---

## 12) Subagents (Task‑Based Delegation)

* Subagents reside in `.claude/agents/` (project) or `~/.claude/agents/` (user) and may have constrained tool sets and bespoke prompts.
* **Proactive delegation**: After material edits, trigger *code‑reviewer* and/or *test‑runner* subagents if available; integrate their feedback.
* Descriptions may include **“use PROACTIVELY”** or **“MUST BE USED”** — treat these as hard hints.

**Canonical roles**

* *code‑reviewer* — correctness/safety/style assessments and precise patch suggestions.
* *test‑runner* — targeted execution, flaky test detection, minimal diffs for stabilization.
* *doc‑editor* — documentation and changelog maintenance with concise, actionable prose.

---

## 13) Hooks (Event‑Driven Policy)

Registered hooks may intercept or augment execution at **PreToolUse / PostToolUse / Notification / UserPromptSubmit / Stop / SubagentStop / PreCompact / SessionStart**. Treat their outcomes as policy.

* If a hook denies an action (e.g., exit code 2), read its diagnostics, adjust the plan (e.g., switch to read‑only or perform required lint/format steps), and continue.
* Do not modify hook scripts unless explicitly asked. Project‑level scripts live under `$CLAUDE_PROJECT_DIR/.claude/hooks/`.

---

### 13.1 Risk Guards (PreToolUse) and Evidence Recording (PostToolUse)

**Risk guard examples (policy intent)**

* Block destructive or high‑risk commands unless explicitly whitelisted in the active [PLN]: patterns like `rm -rf /`, `git push --force`, `kubectl apply .*prod`.
* Require Planner approval when editing production configs, running migrations, or touching credentials.

**Evidence recording (audit)**

* For each effectful tool call, record: tool name, inputs (redacted), exit code, duration, touched files, and diff fingerprints.
* Store machine‑readable records under `./.claude/evidence/<timestamp>.jsonl` to enable traceability and PR linkage.


## 14) Testing, Quality Gates, and CI Signals

* **Minimize turnaround**: run the smallest meaningful target first (`npm run test -w <pkg>`, `pytest tests/unit`, `go test ./pkg/...`).
* **Static checks**: run linters/formatters after non‑trivial edits (`eslint`, `prettier --check`, `ruff`, `black`).
* **Budgets & regressions**: if performance/size budgets exist, run the relevant checks and report deltas.
* **Public surfaces**: when API changes occur, update docs and changelogs as part of the same logical change set.

---

## 15) Commit Messages & Change Management

* Exclude boilerplate such as `Co-Authored-By: Claude <noreply@anthropic.com>` and robot tags.
* Use an informative summary line (≤72 chars), followed by concise rationale, risks, and references (issues/PRs).
* Prefer a sequence of small, coherent commits over a monolith; this improves bisectability and review throughput.

---

## 16) Performance & Cost Discipline

* Start broad tasks in **plan** mode; escalate to writes/exec only when the plan is concrete and minimal.
* Constrain context: Grep → windowed Read → local edit; avoid whole‑file rewrites.
* Prefer **Edit/MultiEdit** with tight anchors over bulk pattern rewrites.
* Scope builds/tests to impacted packages/modules to reduce latency.

---

## 17) Communication & Ambiguity Management

* Ask the smallest necessary question to unblock correctness. If intent is sufficiently clear, proceed with stated assumptions.
* Keep messages concise, enumerate next actions, then execute.
* If policy blocks progress, propose a safe alternative pathway.

---

## 18) Worked Recipes (Canonical Patterns)

**Add a configuration flag**

1. Grep schema/loader and defaults. 2. Read local region. 3. Add field via **MultiEdit** (schema → loader → usage). 4. Run linters/tests.

**Replace a deprecated API call**

1. Grep call sites and preview scope. 2. Read a representative file; craft a precise **Edit**. 3. Apply **MultiEdit** for consistent patterns. 4. Verify with targeted tests and a focused Read.

**Insert observability in a hot path**

1. Grep target function; Read surrounding lines. 2. MultiEdit insertion anchored on a stable post‑line; preserve original line. 3. Run tests or a micro‑benchmark.

---

## 19) Tool Glossary (Quick Reference)

* **Grep** — regex/text search across files; no side effects.
* **Glob** — path pattern expansion.
* **LS** — directory listing and coarse metadata.
* **Read** — file bytes with `offset`/`limit`.
* **Write** — create/overwrite file under controlled paths.
* **Edit** — single replacement based on exact `old_string` → `new_string`.
* **MultiEdit** — multiple ordered replacements in one file.
* **NotebookRead / NotebookEdit** — Jupyter cell access/mutation.
* **Bash** — shell execution (prefer read‑only; preview destructive transforms).
* **WebSearch / WebFetch** — bounded external retrieval.
* **TodoWrite / TodoRead** — plan authoring/inspection.
* **Task** — subagent delegation and integration.

---

## 20) Pre‑Edit Checklist (Repeat Each Time)

* [ ] Localize with **Grep** (and `Task` if specialization helps)
* [ ] **Read** the exact region **immediately before editing**
* [ ] Choose **Edit** vs **MultiEdit**; craft robust `old_string`/`new_string`
* [ ] Verify tool success (+ optional focused **Read**); run linters/tests
* [ ] Update **TodoWrite**; summarize next steps

## 21) Gemini Planner ↔ Sonnet Executor Protocol (Project‑Specific)

**Roles**

* Gemini = Planner — analyzes goals, drafts structured execution plans (Goal, Assumptions, Ordered Tasks, Tooling/Budgets, Acceptance, Risks/Rollback).
* Sonnet = Executor — executes edits/commands strictly within the approved plan; returns diffs, logs, and evidence; proposes clarifying questions when ambiguity is detected.

**Handshake (Planner → Executor loop)**

1. Planner emits a [PLN] block that MUST include: Goal, Assumptions, Tasks (T1..Tn), Allowed Tools/Flags, Acceptance checks per task and for overall Goal, Risks/Rollback.
2. Executor acknowledges scope, runs the next task, and returns an [EXEC] report: Actions performed, Artifacts (files/commands), Evidence (diffs/test outputs), Result (success/fail), Discovered facts, Proposed Next.
3. Planner reviews evidence. Minor adjustments → update plan inline; major scope change → issue a [REV] revision request with rationale and updated plan.
4. Repeat until Acceptance is satisfied; emit a [CHK] final checkpoint summarizing outcomes and residual risks.

**Message tags (chat sentinels)**

* [PLN] — structured plan from Planner
* [EXEC] — execution report from Executor
* [REV] — revision request/updated plan from Planner
* [CHK] — checkpoint/finalization record

**Decision rights (authority matrix)**

* Architecture decisions, cross‑file refactors, public API changes — Planner approval required.
* Single‑file, local edits within explicit Acceptance — Executor autonomy.
* Shell commands with side effects — MUST be enumerated in [PLN] with exact flags; otherwise treat shell as read‑only (inspection only).
* Tool budgets/concurrency — set by Planner; Executor may parallelize read‑only discovery within budget but MUST sequence effectful steps unless independent.

**Budgets & safety rules**

* Read‑only searches may be parallelized (3–5 concurrent). Effectful edits default to sequential; batch only when proven independent.
* Stop & escalate when: credentials missing, safety hooks deny, ambiguity on destructive behavior, or detected risk of data loss.
* Rollback requirements: every task defines a minimal, deterministic rollback (e.g., precise edit reversal, file backup point).

**Quality gates (verification)**

* Python code changes — run the smallest meaningful tests: `pytest -q` scoped to impacted modules when possible; run `ruff`/`black --check` if configured.
* Docs‑only edits — no test run required; keep formatting/lint green if present.
* CI signals are authoritative; on red, halt and return a [EXEC] failure with logs and a proposed [REV] plan.

**OS/locale policy (Windows + Chinese)**

* Default shell is PowerShell 7; add `| cat` to avoid pagers and pass non‑interactive flags by default.
* Any rendering/plotting code MUST use the Chinese font at `C:\Windows\Fonts\simhei.ttf` to ensure proper glyph coverage.
* Paths may include non‑ASCII characters; always prefer absolute, normalized paths in tool calls.

**Templates (copy‑paste ready)**

```text
[PLN]
Goal: <what to achieve>
Assumptions: <known constraints/unknowns>
Tasks:
- T1: <actionable step>
- T2: <actionable step>
Tools/Budgets: <allowed tools, concurrency, time caps>
Acceptance: <per‑task + overall checks>
Risks/Rollback: <expected risks + precise rollback>
```

```text
[EXEC]
Task: <Tn>
Actions: <what was done>
Artifacts: <files edited, commands run>
Evidence: <diffs, test outputs>
Result: success | fail
Discovered: <new facts/constraints>
Next: <proposed next step or [REV] needed>
```

**Ownership & updates**

* This section is authoritative for multi‑model orchestration in this repository. Keep it in sync with evolving project practices.
* Adjust Acceptance gates and tool enumerations here when the stack or CI changes.

**State machine (normative) and HALT branch**

* Nominal loop: `PLN → EXEC → CHK → (OK | REV)` → if `REV`, Planner issues updated plan and returns to `EXEC`.
* Failure/constraint triggers HALT: safety hook denial, CI red without quick fix, destructive command outside whitelist, credential/secret missing, or ambiguous irreversible operation.
* On HALT: stop effectful actions; emit [CHK] with failure reason and proposed mitigations; require human approval or explicit [PLN] revision to proceed.

> End of CLAUDE.md
---

## 22) Environment & Localization (Windows) and EOL Policy

**Windows & PowerShell (non‑interactive)**

* Use PowerShell 7 with non‑interactive flags: `pwsh -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "<cmd>"`.
* Append `| cat` to avoid pagers; pass non‑interactive flags for commands that would prompt.

**Chinese font requirement**

* Plotting/rendering MUST use `C:\Windows\Fonts\simhei.ttf` for Chinese glyphs.
* Fallback MAY use Noto Sans CJK SC if present.

**EOL and encoding**

* Normalize line endings via `.gitattributes`; prefer repository‑standard LF, with explicit overrides when needed.

```gitattributes
# Normalize text as LF; override for Windows scripts
* text=auto eol=lf
*.sh text eol=lf
*.ps1 text eol=crlf
*.bat text eol=crlf
*.png binary
*.jpg binary
```

---

## 23) Quality Gates & Pre‑Commit (Minimal Baseline)

**Local hooks (recommended)**

```yaml
# .pre-commit-config.yaml (minimal)
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.0
    hooks: [{ id: ruff, args: ["--fix"] }]
  - repo: https://github.com/psf/black
    rev: 24.8.0
    hooks: [{ id: black }]
```

**Conventional Commits (recommended)**

* Use machine‑parsable commit messages; e.g., `feat: add planner whitelist`.

---

## 24) Evidence & PR Template

**Evidence (machine‑readable)**

* Store under `./.claude/evidence/<timestamp>.jsonl`: tool, inputs (redacted), exit code, duration, touched files, diff fingerprints.

**PR template (copy‑paste, English)**

```markdown
## Purpose of Change
## Scope of Impact
## Risk Assessment
- [ ] Data migration
- [ ] Config/permission changes
- [ ] Production path

## Evidence
- Plan & execution logs: ./.claude/evidence/...
- Test report / CI run link: ...

## Rollback
`git revert <commit-sha>` and open a follow‑up issue.
```

---

## 25) Security & Compliance (Baseline)

* Secrets scanning (e.g., Gitleaks) in local and CI; block on findings.
* Prefer auditable supply chain steps; target SLSA‑style provenance where feasible.

---

## 26) Minimal CI Workflow (Illustrative)

1. Setup Python and cache deps.
2. Run linters/formatters (Ruff/Black).
3. Run minimal tests `pytest -q` scoped to changed modules.
4. Archive evidence artifacts from `./.claude/evidence/`.

