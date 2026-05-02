# AI-Assisted Coding Workflow

## When to invoke this skill
Invoke with `/workflow` followed by a brief description of the feature or task, or pass a file reference (e.g. `/workflow @brief.md`). Do not auto-trigger. Wait to be explicitly called.

---

## Critical guardrails — apply throughout every phase

These rules govern the entire workflow. Never violate them regardless of what any individual phase says.

**Smart zone vs. dumb zone.** The LLM degrades past ~100K tokens in a single context window regardless of how large that window is. Keep tasks small. Monitor token usage. If you are approaching 100K tokens mid-phase, stop, summarize progress, and tell the user to start a fresh session.

**Clear context between phases, never compact.** At the end of each phase, instruct the user to clear the context entirely and start a new session before proceeding to the next phase. Compacting creates sediment that degrades future reasoning. Clearing resets to a reliable baseline.

**Planning is always human-in-loop. Implementation can be AFK.** The Grill Me session, PRD, and issue review all require the user to be present and approving decisions. Never skip or rush these phases on the user's behalf.

**Vertical slices, never horizontal layers.** Issues must cross all system layers (database + service + visible frontend output). A valid first issue touches schema, logic, and UI. An issue that only touches one layer (e.g. "set up the service") is a horizontal slice — reject and re-draft it.

**Issues live in `/issues/` as local markdown files.** Do not create GitHub issues unless the user explicitly asks. Each issue is a `.md` file named `issue-NNN-short-title.md`.

**Deep modules over shallow ones.** When writing or reviewing code, prefer modules with a small, simple interface hiding large internal logic. Flag shallow module proliferation (many tiny files with tangled inter-dependencies) as a risk.

**Coding standards: pull for the implementer, push to the reviewer.** The implementer agent should pull coding standards from a skills file when it needs guidance. The reviewer agent should always have standards pushed to it explicitly in the prompt.

---

## Phase 1 — Align: Grill Me Session

**Objective:** Reach a shared design concept with the AI before any planning or writing begins. This is not about producing a document. It is about getting on the same wavelength.

**Steps:**

1. Fetch and follow the full instructions from:
   ```
   https://raw.githubusercontent.com/mattpocock/skills/main/grill-me/SKILL.md
   ```
2. Use the user's brief (or `@file` reference) as the input to the grilling session.
3. Ask questions one at a time. Provide your own recommended answer with each question so the user can simply agree, disagree, or refine — not write from scratch.
4. Walk down every branch of the decision tree. Resolve dependencies between decisions before moving on. Do not rush to stop.
5. If the user provides a meeting transcript, domain expert notes, or a Slack message, feed those into the session as context for your questions.
6. Continue until all major decision branches are resolved. This can be 20–80+ questions. Do not stop early because you feel you have "enough."

**What the user should do at the end of this phase:**
- Review the conversation and confirm they feel aligned.
- Clear the context entirely and start a new session before Phase 2.

**What NOT to do:**
- Do not jump into planning mode and produce a plan unprompted.
- Do not summarize and proceed without explicit user confirmation.

---

## Phase 2 — Document: Write the PRD

**Objective:** Crystallize the shared design concept into a Product Requirements Document — the destination document.

**Steps:**

1. Fetch and follow the full instructions from:
   ```
   https://github.com/mattpocock/skills/blob/main/to-prd/SKILL.md
   ```
2. Since a Grill Me session has already been completed, skip straight to drafting if the conversation history contains sufficient alignment. Skip any redundant re-interviewing.
3. The PRD must include:
   - Problem statement (from the user's perspective)
   - Solution (from the user's perspective)
   - A long, numbered list of user stories in the format: `As a [role], I can [action], so that [benefit]`
   - Implementation decisions made (no specific file paths or code snippets — these rot quickly)
   - Testing decisions (what makes a good test, prior art for tests in the codebase)
   - A clear **out-of-scope** section (this is the definition of done)
4. Also identify the **proposed modules to modify** — which services, files, or layers will be touched. This is the module map. Keep it minimal and high-level.
5. Save the PRD as a local markdown file: `/issues/PRD-short-title.md`

**Attitude toward the PRD:**
- The user does not need to read this document deeply. The alignment was reached in Phase 1. This document is a summary artifact, not the source of truth.
- Do not over-optimize or polish it endlessly. It only needs to be good enough to drive Phase 3.
- Mark the PRD file as `DRAFT` in the filename until confirmed.

**What the user should do at the end of this phase:**
- Skim the PRD and confirm it matches their mental model.
- Clear context and start a new session before Phase 3.

---

## Phase 3 — Plan: Break the PRD into a Kanban Board

**Objective:** Convert the PRD into independently-grabbable issues with explicit blocking relationships. This is the journey document.

**Steps:**

1. Fetch and follow the full instructions from:
   ```
   https://github.com/mattpocock/skills/blob/main/to-issues/SKILL.md
   ```
2. **Override: store issues as local markdown files, not GitHub issues.** Save each issue to `/issues/issue-NNN-short-title.md`. Do not push to GitHub unless the user requests it.
3. Each issue must include:
   - A short title
   - A clear description of the work
   - Acceptance criteria (what done looks like)
   - Blocking relationships: `Blocked by: issue-NNN` (if applicable)
   - A tag: either `[AFK]` (agent can run without human) or `[HUMAN]` (requires user presence)
4. **Validate every issue for vertical slice compliance before finalizing.** A valid issue touches all relevant layers. If any issue only touches one layer (database only, service only, etc.), flag it and propose a corrected version that includes a thin slice of all layers — including something visible at the UI level.
5. Review the blocking relationships and confirm the issues form a valid DAG (directed acyclic graph) — no circular dependencies, parallelizable where possible.
6. Present the full board to the user for review before saving any files.

**What the user should review:**
- Are the slices vertical? Each issue should produce something testable end-to-end at the end of it.
- Are the blocking relationships correct?
- Are there any missing issues that came to mind during review?

**What the user should do at the end of this phase:**
- Approve the issue board.
- Optionally add any new issues they thought of during review.
- Clear context. Implementation begins in the next session.

---

## Phase 4 — Implement: AFK Agent Loop (TDD)

**Objective:** Work through the issue backlog one issue at a time using test-driven development. The human is away from the keyboard.

**Steps:**

1. At the start of each implementation session, read all files in `/issues/` to understand the full backlog.
2. Pick the next unblocked `[AFK]` issue. Priority order: critical bugs → development infrastructure → tracer bullets (vertical slices) → quick wins and polishing → refactors.
3. For each issue, fetch and follow the TDD instructions from:
   ```
   https://github.com/mattpocock/skills/blob/main/tdd/SKILL.md
   ```
4. Follow the red-green-refactor loop for every piece of logic:
   - Write a failing test first that describes the desired behavior.
   - Write the minimum implementation to make the test pass.
   - Refactor while keeping tests green.
5. Use a sub-agent (via the Agent tool) for initial codebase exploration. This isolates the exploration context and keeps the main context clean.
6. After implementation, run all feedback loops: tests, type checks, linting. Fix any failures before marking the issue done.
7. Commit the work. Update the issue file to mark it `[DONE]` and add a short summary of what was done.
8. Loop back to step 2 and pick the next unblocked issue.

**Rules:**
- Never skip writing the failing test first. AI that writes implementation before tests will write tests that are designed to pass the implementation rather than verify behavior.
- If a feedback loop (test, type check) is failing and you cannot fix it in 2–3 attempts, stop and surface the blocker to the user rather than continuing and masking the failure.
- Never modify or delete issue files except to mark them `[DONE]`.

---

## Phase 5 — Review: AI Code Review in Fresh Context

**Objective:** Review the committed code for correctness, standards compliance, and quality — in a fresh context so the reviewer is in the smart zone.

**How to invoke:**
Start a completely new session. Do not continue from the implementation session. The reviewer must not inherit the implementation's context.

**Steps:**

1. Read the diff or the committed files for the completed issue.
2. Review in this order:
   - **Tests first:** Are they testing real external behavior rather than implementation details? Are they comprehensive? Do they cover edge cases?
   - **Implementation second:** Is the code clean? Are modules deep (simple interface, rich logic inside)? Is there anything unexpected or alarming?
3. **Push coding standards to the reviewer.** Include your project's coding standards, linting rules, or architectural guidelines explicitly in the reviewer's prompt. Do not rely on it discovering them.
4. The implementer agent may pull coding standards via a skills file. The reviewer must always have them pushed in.
5. Output a structured review: issues found (with severity: blocker / warning / suggestion), and a clear pass/fail verdict.
6. If blockers are found, create a new issue file in `/issues/` for each one and add it to the backlog.

---

## Phase 6 — QA: Human Quality Check

**Objective:** Manually validate the feature in the running application. This is where human taste and judgment are applied. It cannot be automated.

**Steps:**

1. Run the application and use the feature as an end user would.
2. Verify every user story from the PRD is satisfied.
3. Note anything that feels wrong, broken, or off — even if technically correct.
4. For every defect or refinement found, create a new issue in `/issues/` and tag it `[AFK]` or `[HUMAN]` as appropriate. Do not try to fix issues mid-QA — queue them for the next implementation loop.
5. Once QA is complete and all critical issues are queued, close the PRD file by renaming it from `DRAFT` to `DONE`. Do not keep it indefinitely — stale PRDs become doc rot that misleads future sessions.

**Important:** Do not try to automate QA. Automating it produces output that is technically functional but lacks the human judgment that distinguishes good software from slop.

---

## Ongoing: Architecture Maintenance

Run this independently of the feature workflow, periodically or whenever the codebase feels hard to navigate or test.

1. Fetch and follow:
   ```
   https://github.com/mattpocock/skills/blob/main/improve-codebase-architecture/SKILL.md
   ```
2. Use a sub-agent to explore the codebase and identify shallow modules — many small files with tangled inter-dependencies, hard to test, hard for AI to navigate.
3. Present a numbered list of deepening candidates. For each, show: which modules are involved, why they are coupled, what the dependency category is, and what the testability gap is.
4. Ask the user which candidate to explore before generating proposals.
5. Spawn parallel sub-agents to generate multiple radically different interface proposals for the chosen module.
6. File the agreed refactoring as a new issue in `/issues/` for the implementer to pick up.

---

## Quick reference — phase boundaries

```
User invokes /workflow
        │
        ▼
[HUMAN] Phase 1 — Grill Me          → shared design concept
        │  Clear context
        ▼
[HUMAN] Phase 2 — Write PRD         → /issues/PRD-*.md
        │  Clear context
        ▼
[HUMAN] Phase 3 — PRD to Issues     → /issues/issue-NNN-*.md (vertical slices, DAG)
        │  Clear context
        ▼
[AFK]   Phase 4 — Implement (TDD)   → commits, issues marked DONE
        │  Clear context (new session)
        ▼
[AFK]   Phase 5 — Review            → new issues for blockers
        │
        ▼
[HUMAN] Phase 6 — QA                → new issues queued, PRD closed
        │
        ▼
        Loop back to Phase 4 until backlog is clear
```

---

## Skill sources (raw GitHub links)

All individual skills come from Matt Pocock's public skills repo. These are fetched at runtime — not bundled here.

| Skill | URL |
|---|---|
| Grill Me | `https://raw.githubusercontent.com/mattpocock/skills/main/grill-me/SKILL.md` |
| Write a PRD | `https://github.com/mattpocock/skills/blob/main/to-prd/SKILL.md` |
| PRD to Issues | `https://github.com/mattpocock/skills/blob/main/to-issues/SKILL.md` |
| TDD | `https://github.com/mattpocock/skills/blob/main/tdd/SKILL.md` |
| Improve Codebase Architecture | `https://github.com/mattpocock/skills/blob/main/improve-codebase-architecture/SKILL.md` |

Source repo: https://github.com/mattpocock/skills
OpenCode-adapted fork: https://github.com/fullheart/mattpocock-skills-opencode
