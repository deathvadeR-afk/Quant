# Comprehensive AI-Assisted Development Skill File

## Overview

This single file contains the complete workflow, sub-skills, and methodology for AI-assisted development in this project. LLMs should read this file to understand the full development lifecycle, skill interactions, and required practices.

When to invoke: Use `/workflow` followed by a task description, or reference this file directly for methodology guidance. Do not auto-trigger; wait for explicit invocation.

## LLM Usage Instructions

1. **Read Linked Sub-Skill URLs**: For every linked skill URL in this file (Grill Me, To-PRD, To-Issues, TDD, Improve Architecture, Diagnose), fetch and read the full skill content from the link before executing the corresponding phase or sub-skill.
2. **Follow Execution Order**: Adhere to the Quick-Start Guide order for the full development methodology.
3. **Respect Guardrails**: All Critical Guardrails apply to every phase and sub-skill execution.

---

## Critical Guardrails (Apply to All Phases)

1. **Smart Zone Management**: LLM performance degrades past ~100K context tokens. Keep tasks small; if approaching 100K tokens mid-phase, stop, summarize, and request a fresh session.
2. **Phase Context Separation**: Clear context entirely between phases (no compacting). Compacting creates sediment that degrades reasoning.
3. **Human-in-Loop Planning**: Grill Me, PRD, and issue review require user presence. Never skip these phases.
4. **Vertical Slices Only**: Issues must cross all system layers (database + service + UI). Reject horizontal slices (single-layer tasks).
5. **Local Issue Storage**: Issues live in `/issues/` as markdown files (not GitHub issues unless explicitly requested).
6. **Deep Modules Preferred**: Favor modules with small interfaces hiding large internal logic over shallow, tangled small files.
7. **Coding Standards**: Implementers pull standards from this file; reviewers have standards pushed explicitly in prompts.

---

## Core Development Workflow

### Phase1 — Align: Grill Me Session (HUMAN)

**Objective**: Reach shared design concept via structured Q&A.

- Fetch full instructions: [Grill Me Skill](https://raw.githubusercontent.com/mattpocock/skills/main/skills/productivity/grill-me/SKILL.md)
- **LLM Instruction**: Read the full Grill Me skill from the linked URL before executing this phase.
- Use user's brief/`@file` as input
- Ask one question at a time with recommended answers
- Resolve all decision branches (20–80+ questions)
- **End of Phase**: User confirms alignment → Clear context → New session

### Phase2 — Document: Write PRD (HUMAN)

**Objective**: Crystallize design into Product Requirements Document.

- Fetch full instructions: [To-PRD Skill](https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/to-prd/SKILL.md)
- **LLM Instruction**: Read the full To-PRD skill from the linked URL before executing this phase.
- Skip redundant re-interviewing if Grill Me session is complete
- PRD must include: Problem statement, Solution, User stories (`As a [role], I can [action], so that [benefit]`), Implementation decisions, Testing decisions, Out-of-scope section, Module map
- Save as `/issues/PRD-short-title.md` (mark `DRAFT` until confirmed)
- **End of Phase**: User skims and confirms → Clear context → New session

### Phase3 — Plan: Break into Kanban Issues (HUMAN)

**Objective**: Convert PRD into vertical-slice issues with blocking relationships.

- Fetch full instructions: [To-Issues Skill](https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/to-issues/SKILL.md)
- **LLM Instruction**: Read the full To-Issues skill from the linked URL before executing this phase.
- Save issues as `/issues/issue-NNN-short-title.md` (local markdown, not GitHub)
- Each issue must include: Title, Description, Acceptance criteria, Blocking relationships (`Blocked by: issue-NNN`), Tag (`[AFK]` or `[HUMAN]`)
- Validate vertical slices and DAG (no circular dependencies)
- **End of Phase**: User approves board → Clear context → New session

### Phase4 — Implement: AFK TDD Loop (AFK)

**Objective**: Work through issues via test-driven development.

- Fetch full instructions: [TDD Skill](https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/tdd/SKILL.md)
- **LLM Instruction**: Read the full TDD skill from the linked URL before executing this phase.
- Pick next unblocked `[AFK]` issue (priority: critical bugs → infrastructure → tracer bullets → quick wins → refactors)
- Follow red-green-refactor loop:
  1. Write failing test for desired behavior
  2. Write minimum implementation to pass test
  3. Refactor while keeping tests green
- Use sub-agents for codebase exploration
- Run feedback loops (tests, type checks, linting) before marking issue `[DONE]`
- Commit work and update issue file

### Phase5 — Review: AI Code Review (AFK)

**Objective**: Review committed code in fresh context (no implementation context inheritance).

- Start new session (no context from implementation)
- Review order: Tests first (behavior, coverage, edge cases) → Implementation (clean code, deep modules, surprises)
- Push coding standards explicitly in reviewer prompt
- Output structured review: Blocker/Warning/Suggestion + Pass/Fail verdict
- Create new issues for blockers

### Phase6 — QA: Human Quality Check (HUMAN)

**Objective**: Manual validation of feature in running application.

- Run application and verify all PRD user stories
- Note any broken/unexpected behavior (even if technically correct)
- Create new issues for defects/refinements (tag `[AFK]`/`[HUMAN]`)
- Close PRD by renaming from `DRAFT` to `DONE` once QA completes
- **Loop back to Phase4** until backlog is clear

### Ongoing: Architecture Maintenance

- Fetch full instructions: [Improve Architecture Skill](https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/improve-codebase-architecture/SKILL.md)
- **LLM Instruction**: Read the full Improve Architecture skill from the linked URL before executing this section.
- Use sub-agents to identify shallow modules
- Present deepening candidates with module details, coupling reasons, and testability gaps
- Spawn parallel sub-agents for interface proposals
- File agreed refactoring as new issue in `/issues/`

---

## Sub-Skills (Full Workflows)

### 1. Diagnose Skill

**LLM Instruction**: Read the full official Diagnose skill from [https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/diagnose/SKILL.md](https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/diagnose/SKILL.md) before executing this sub-skill.

**When to use**: User reports bugs, performance regressions, or says "diagnose this"/"debug this".
**Discipline**: Reproduce → minimise → hypothesise → instrument → fix → regression-test.

---

name: diagnose
description: Disciplined diagnosis loop for hard bugs and performance regressions. Reproduce → minimise → hypothesise → instrument → fix → regression-test. Use when user says "diagnose this" / "debug this", reports a bug, says something is broken/throwing/failing, or describes a performance regression
---

# Diagnose

A discipline for hard bugs. Skip phases only when explicitly justified.

When exploring the codebase, use the project's domain glossary to get a clear mental model of the relevant modules, and check ADRs in the area you're touching.

## Phase1 — Build a feedback loop

**This is the skill.** Everything else is mechanical. If you have a fast, deterministic, agent-runnable pass/fail signal for the bug, you will find the cause — bisection, hypothesis-testing, and instrumentation all just consume that signal. If you don't have one, no amount of staring at code will save you.

Spend disproportionate effort here. **Be aggressive. Be creative. Refuse to give up.**

### Ways to construct one — try them in roughly this order

1. **Failing test** at whatever seam reaches the bug — unit, integration, e2e.
2. **Curl / HTTP script** against a running dev server.
3. **CLI invocation** with a fixture input, diffing stdout against a known-good snapshot.
4. **Headless browser script** (Playwright / Puppeteer) — drives the UI, asserts on DOM/console/network.
5. **Replay a captured trace.** Save a real network request / payload / event log to disk; replay it through the code path in isolation.
6. **Throwaway harness.** Spin up a minimal subset of the system (one service, mocked deps) that exercises the bug code path with a single function call.
7. **Property / fuzz loop.** If the bug is "sometimes wrong output", run 1000 random inputs and look for the failure mode.
8. **Bisection harness.** If the bug appeared between two known states (commit, dataset, version), automate "boot at state X, check, repeat" so you can `git bisect run` it.
9. **Differential loop.** Run the same input through old-version vs new-version (or two configs) and diff outputs.
10. **HITL bash script.** Last resort. If a human must click, drive _them_ with `scripts/hitl-loop.template.sh` so the loop is still structured. Captured output feeds back to you.

Build the right feedback loop, and the bug is 90% fixed.

### Iterate on the loop itself

Treat the loop as a product. Once you have _a_ loop, ask:

- Can I make it faster? (Cache setup, skip unrelated init, narrow the test scope.)
- Can I make the signal sharper? (Assert on the specific symptom, not "didn't crash".)
- Can I make it more deterministic? (Pin time, seed RNG, isolate filesystem, freeze network.)

A 30-second flaky loop is barely better than no loop. A 2-second deterministic loop is a debugging superpower.

### Non-deterministic bugs

The goal is not a clean repro but a **higher reproduction rate**. Loop the trigger 100×, parallelise, add stress, narrow timing windows, inject sleeps. A 50%-flake bug is debuggable; 1% is not — keep raising the rate until it's debuggable.

### When you genuinely cannot build a loop

Stop and say so explicitly. List what you tried. Ask the user for: (a) access to whatever environment reproduces it, (b) a captured artifact (HAR file, log dump, core dump, screen recording with timestamps), or (c) permission to add temporary production instrumentation. Do **not** proceed to hypothesise without a loop.

Do not proceed to Phase2 until you have a loop you believe in.

## Phase2 — Reproduce

Run the loop. Watch the bug appear.

Confirm:

- [ ] The loop produces the failure mode the **user** described — not a different failure that happens to be nearby. Wrong bug = wrong fix.
- [ ] The failure is reproducible across multiple runs (or, for non-deterministic bugs, reproducible at a high enough rate to debug against).
- [ ] You have captured the exact symptom (error message, wrong output, slow timing) so later phases can verify the fix actually addresses it.

Do not proceed until you reproduce the bug.

## Phase3 — Hypothesise

Generate **3–5 ranked hypotheses** before testing any of them. Single-hypothesis generation anchors on the first plausible idea.

Each hypothesis must be **falsifiable**: state the prediction it makes.

> Format: "If <X> is the cause, then <changing Y> will make the bug disappear / <changing Z> will make it worse."

If you cannot state the prediction, the hypothesis is a vibe — discard or sharpen it.

**Show the ranked list to the user before testing.** They often have domain knowledge that re-ranks instantly ("we just deployed a change to #3"), or know hypotheses they've already ruled out. Cheap checkpoint, big time saver. Don't block on it — proceed with your ranking if the user is AFK.

## Phase4 — Instrument

Each probe must map to a specific prediction from Phase3. **Change one variable at a time.**

Tool preference:

1. **Debugger / REPL inspection** if the env supports it. One breakpoint beats ten logs.
2. **Targeted logs** at the boundaries that distinguish hypotheses.
3. Never "log everything and grep".

**Tag every debug log** with a unique prefix, e.g. `[DEBUG-a4f2]`. Cleanup at the end becomes a single grep. Untagged logs survive; tagged logs die.

**Perf branch.** For performance regressions, logs are usually wrong. Instead: establish a baseline measurement (timing harness, `performance.now()`, profiler, query plan), then bisect. Measure first, fix second.

## Phase5 — Fix + regression test

Write the regression test **before the fix** — but only if there is a **correct seam** for it.

A correct seam is one where the test exercises the **real bug pattern** as it occurs at the call site. If the only available seam is too shallow (single-caller test when the bug needs multiple callers, unit test that can't replicate the chain that triggered the bug), a regression test there gives false confidence.

**If no correct seam exists, that itself is the finding.** Note it. The codebase architecture is preventing the bug from being locked down. Flag this for the next phase.

If a correct seam exists:

1. Turn the minimised repro into a failing test at that seam.
2. Watch it fail.
3. Apply the fix.
4. Watch it pass.
5. Re-run the Phase1 feedback loop against the original (un-minimised) scenario.

## Phase6 — Cleanup + post-mortem

Required before declaring done:

- [ ] Original repro no longer reproduces (re-run the Phase1 loop)
- [ ] Regression test passes (or absence of seam is documented)
- [ ] All `[DEBUG-...]` instrumentation removed (`grep` the prefix)
- [ ] Throwaway prototypes deleted (or moved to a clearly-marked debug location)
- [ ] The hypothesis that turned out correct is stated in the commit / PR message — so the next debugger learns

**Then ask: what would have prevented this bug?** If the answer involves architectural change (no good test seam, tangled callers, hidden coupling) hand off to the `/improve-codebase-architecture` skill with the specifics. Make the recommendation **after** the fix is in, not before — you have more information now than when you started.

---

### 2. Setup Matt Pocock Skills

**When to use**: Before first use of `to-issues`, `to-prd`, `triage`, `diagnose`, `tdd`, `improve-codebase-architecture`, or `zoom-out`.
**Purpose**: Configure repo-specific context for engineering skills (issue tracker, triage labels, domain docs).

#### Process

1. **Explore Repo**:
   - Check `git remote -v`, `.git/config` (GitHub/GitLab/other)
   - Check `AGENTS.md`/`CLAUDE.md` for existing `## Agent skills` section
   - Check `CONTEXT.md`, `CONTEXT-MAP.md`, `docs/adr/`, `docs/agents/`, `.scratch/`

2. **Present Findings + Ask (One Section at a Time)**:
   - **Section A: Issue Tracker** (Default: GitHub if remote exists)
     Options: GitHub (gh CLI), GitLab (glab CLI), Local markdown (`.scratch/`), Other (Jira/Linear)
   - **Section B: Triage Labels** (Default: Canonical 5 roles)
     Roles: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`
   - **Section C: Domain Docs** (Default: Single-context)
     Options: Single-context (root `CONTEXT.md` + `docs/adr/`), Multi-context (`CONTEXT-MAP.md` + per-context files)

3. **Confirm + Edit**: Show draft `## Agent skills` block and `docs/agents/` files for user approval.

4. **Write**:
   - Edit `CLAUDE.md` (preferred) or `AGENTS.md` (whichever exists) with `## Agent skills` block
   - Write `docs/agents/issue-tracker.md`, `docs/agents/triage-labels.md`, `docs/agents/domain.md` using seed templates from skill folder

---

## Cross-Skill Integration Guide

| Skill | Integrates With | Purpose |
|-------|----------------|---------|
| Diagnose | TDD, Improve Architecture | Regression tests use TDD; architectural gaps from diagnose feed into improvement |
| Setup Matt Pocock Skills | All engineering skills | Prerequisite configuration for issue tracker, labels, domain docs |
| TDD | Implement Phase, Diagnose | Core of Phase4 implementation; regression tests for diagnose |
| Improve Architecture | Diagnose, Ongoing Maintenance | Fix architectural gaps identified in diagnose or maintenance |

---

## Quick-Start Guide for LLM

Follow this order to execute the full development methodology:

1. **Check Setup**: Run _Setup Matt Pocock Skills_ if `docs/agents/` is missing
2. **Align**: Execute Phase1 (Grill Me) for new features
3. **Document**: Execute Phase2 (Write PRD) after alignment
4. **Plan**: Execute Phase3 (Kanban Issues) after PRD
5. **Implement**: Execute Phase4 (TDD Loop) for `[AFK]` issues
6. **Review**: Execute Phase5 (AI Review) in fresh session after implementation
7. **QA**: Execute Phase6 (Human QA) after review
8. **Diagnose**: Use _Diagnose Skill_ for any bugs/regressions during any phase

---

## References

- Matt Pocock Skills Repo: [https://github.com/mattpocock/skills](https://github.com/mattpocock/skills)
- OpenCode Adapted Fork: [https://github.com/fullheart/mattpocock-skills-opencode](https://github.com/fullheart/mattpocock-skills-opencode)
- Skill Sources (Raw):
  - Grill Me: [https://raw.githubusercontent.com/mattpocock/skills/main/skills/productivity/grill-me/SKILL.md](https://raw.githubusercontent.com/mattpocock/skills/main/skills/productivity/grill-me/SKILL.md)
  - To-PRD: [https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/to-prd/SKILL.md](https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/to-prd/SKILL.md)
  - To-Issues: [https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/to-issues/SKILL.md](https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/to-issues/SKILL.md)
  - TDD: [https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/tdd/SKILL.md](https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/tdd/SKILL.md)
  - Improve Architecture: [https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/improve-codebase-architecture/SKILL.md](https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/improve-codebase-architecture/SKILL.md)
  - Diagnose: [https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/diagnose/SKILL.md](https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/diagnose/SKILL.md)
