# Pipeline Orchestration — How It Works

## The Big Picture

When a user creates a sprint ("Write a thriller pilot" or "Run a sales campaign for fintech startups"), the system needs to coordinate multiple AI agents to get the work done. Each department has a **leader agent** that acts as the project manager — it decides what work needs to happen next, assigns tasks to worker agents, reviews the results, and advances through the pipeline until the sprint is complete.

The leader doesn't do the work itself. It orchestrates. Think of it like a film director: they don't operate the camera or act in scenes, but they decide what happens in what order, review takes, and call "cut" or "do it again."

## The Event Loop

The entire system is **event-driven**. There is no long-running process sitting in a loop. Instead:

1. Something happens (sprint created, task completed, task approved)
2. The system calls `create_next_leader_task`
3. The leader blueprint looks at the current state and proposes the next piece of work
4. That work gets created, executed, and completed
5. Go back to step 2

Each time the leader is asked "what's next?", it looks at one snapshot of the world — what phase are we in, what tasks exist, what's done, what's still running — and makes one decision. Then it goes away. It gets called again when something changes.

This means the leader must be able to reconstruct its full understanding from the database state alone. It cannot hold anything in memory between calls. All state lives in the sprint state record (AgentSprintState).

## The Three Layers

### Layer 1: The Base Class (PipelineLeaderBlueprint)

This is the shared machinery. Every department's leader inherits from it. It handles:

**Phase tracking.** It knows which phase the pipeline is on (stored in sprint state). When asked "what's next?", it looks up the current phase and either handles it directly (simple phases) or delegates to the leader's handler method (complex phases).

**Task status queries.** When anyone needs to know "is this step's work done?", "is something already running?", or "give me all completed tasks for these agent types" — the base class provides these as methods. No leader ever writes a raw database query for task status. This is where bugs lived before, because each leader was writing these queries slightly differently.

**Simple phase execution.** If a phase is just "run agent X with command Y" — the base class handles everything. It checks if the task exists, if it's done, if it's running. If nothing exists, it creates the task, optionally injecting output from prior phases as context. The leader doesn't need to write any code for this.

**Phase advancement.** When a phase is complete, the base class moves to the next phase, updates sprint state, and calls an optional hook (e.g., "persist this output as a document"). If it was the last phase, it completes the sprint.

**Sprint lifecycle.** Completing a sprint means setting the status to DONE, recording the completion time, writing a summary, and broadcasting the update via WebSocket so the frontend updates in real time. The base class owns all of this.

**Review utilities.** A simple function `should_accept_review(score, round, polish_count)` that answers: "Given this review score, this many rounds, and this many polish attempts, should we accept the work or send it back?" The thresholds are universal: 9.5/10 is automatic acceptance, 9.0/10 with 3+ polish attempts is acceptance by diminishing returns. This is just a utility — leaders call it when they need it.

### Layer 2: The Phase Definition

Each leader defines its pipeline as a list of phases. A phase is a simple data object:

```
Phase:
  name          — what this phase is called ("research", "pitch", etc.)
  agent_type    — which agent runs this phase (for simple phases)
  command       — which command the agent runs
  agents        — for parallel tasks: a list of agent+command pairs
  context_from  — which prior phases to inject as context
  handler       — method name for complex phases (escape hatch)
  on_complete   — method name called when the phase finishes
```

For simple phases (most of the sales pipeline), you just declare agent_type, command, and context_from. The base class does the rest.

For complex phases (sales QA review, all writers room stages), you specify a handler. The base class calls your handler, and the handler returns either a task proposal ("here's what to do next") or None ("this phase is done, advance").

### Layer 3: The Leader's Custom Logic (Handlers)

Handlers are where department-specific intelligence lives. A handler receives the agent, sprint, and sprint state, and returns a task proposal or None.

A handler is responsible for:
- Its own sub-state tracking (e.g., writers room tracks "creative_writing" → "creative_gate" → "lead_writing" etc. within each stage)
- Deciding what tasks to propose
- Managing review loops (calling `should_accept_review` and routing fixes)
- Returning None when the phase is complete

A handler uses the base class task status queries — it never writes raw database queries.

## How Sales Works

The sales leader defines 7 phases:

```
research → strategy → pitch_design → profile_selection → personalization → qa_review → dispatch
```

**Phases 1-5 are simple config.** Each one names an agent and command. The base class handles all of them automatically:

- "Research" — base class creates a task for the researcher agent with the "research-industry" command. When it completes, base class advances to "strategy."
- "Strategy" — base class creates a task for the strategist agent with "draft-strategy". It injects the research phase's output as context (because context_from=["research"]). When done, advance.
- "Pitch design" — same pattern. Injects research + strategy as context.
- "Profile selection" — same. Injects strategy as context.
- "Personalization" — same. Injects pitch_design + profile_selection as context.

For each of these, the base class does the same thing:
1. Is there a completed task for this agent+command in this sprint? → Advance to next phase.
2. Is there an active task (running, queued, awaiting approval)? → Wait, do nothing.
3. Neither? → Create the task with injected context.

**Phase 6 (QA Review) uses a handler** because it has a review loop:

1. Handler checks: is there a completed QA review with a score?
2. If no review exists yet → propose a QA review task (the QA agent reviews all prior work).
3. If review exists and score is good enough (calls `should_accept_review`) → return None (phase done, base advances to dispatch).
4. If score is not good enough → figure out which earlier agent produced the weakest dimension, send them a fix task with the QA feedback. When the fix completes, the handler proposes another QA review. This loops until the score passes or we hit the maximum rounds.

**Phase 7 (Dispatch) uses a handler** because it fans out to multiple outreach agents:

1. Handler checks: are there outreach agents in the department?
2. If no dispatch tasks created yet → create one "send-outreach" task per outreach agent (all in parallel).
3. If all dispatch tasks are done → call `self.complete_sprint()`. Pipeline finished.
4. If some are still running → wait.

## How Writers Room Works

The writers room leader defines 4 phases:

```
pitch → expose → treatment → first_draft
```

But there's a wrinkle: not every sprint runs all 4. Format detection (a one-time Claude call at sprint start) determines the entry stage and terminal stage. A standalone movie might run pitch → expose → treatment. A series might start at expose and stop at treatment. The base class handles this — it knows which phase to start at and when to stop.

**All 4 phases use the same handler** (`handle_stage`). The stages differ in content but follow the same internal pattern. Here's what happens inside each stage:

**Step A — Creative Writing.** The handler proposes tasks for the creative agents. The story researcher goes first (it gathers raw material). Once research is done, the story architect, character designer, and dialog writer all run in parallel (they don't depend on each other, only on the research). The handler tracks this with a sub-status: "creative_writing".

**Step B — Creative Gate.** Once all creative agents finish, the handler proposes authenticity analyst tasks to review each creative agent's output. If the authenticity checks pass, move on. If they fail, loop back to Step A with critique feedback. Sub-status: "creative_gate".

**Step C — Lead Writer Synthesis.** The handler proposes a task for the lead writer, who takes all the creative agents' outputs and synthesizes them into one cohesive document for the stage (e.g., a pitch document, an expose document). Sub-status: "lead_writing".

**Step D — Deliverable Gate.** A quality gate analyst reviews the synthesized document for structural integrity. If it passes, move on. If it fails, the lead writer gets a revision task with the feedback. Sub-status: "deliverable_gate".

**Step E — Feedback.** The handler proposes feedback tasks — multiple feedback agents run in parallel, each critiquing the deliverable from a different angle (e.g., emotional resonance, narrative structure, market viability). The specific feedback agents vary by stage. Sub-status: "feedback".

**Step F — Review.** A creative reviewer consolidates all feedback into a single critique, then scores the work. The handler calls `should_accept_review()`. If the score passes, the handler sets the stage status to "passed" and returns None — telling the base class this phase is done. If the score fails, the handler loops back to Step A with the consolidated critique. Sub-status: "review".

**When the handler returns None**, the base class advances to the next stage (e.g., pitch → expose). If this was the terminal stage, the base class completes the sprint.

## What the Base Class Decides vs. What the Leader Decides

| Decision | Who makes it |
|----------|-------------|
| What phase are we on? | Base class (reads sprint state) |
| Is this phase's work done? | Base class (for simple phases) or handler (for complex phases) |
| Is a task already running? | Base class (query helpers) |
| What task to create next? | Base class (for simple phases) or handler (for complex phases) |
| What context to inject from prior phases? | Base class (reads completed task reports) |
| When to advance to the next phase? | Base class (when simple phase task completes, or when handler returns None) |
| When to complete the sprint? | Base class (when last phase is done) |
| How to run a review loop? | Handler (using `should_accept_review` utility) |
| How to route a fix after failed review? | Handler (domain-specific logic) |
| What agents run in parallel vs. sequential? | Phase config (for simple phases) or handler (for complex phases) |
| How to handle format detection? | Handler (writers room specific) |

## The Lifecycle of a Single Invocation

Every time a task completes or gets approved, `create_next_leader_task` fires. Here's what happens in one invocation:

1. Load the leader agent and its blueprint.
2. Call `generate_task_proposal(agent)`.
3. Inside generate_task_proposal (base class):
   a. Find the running sprint.
   b. Load sprint state → get current phase.
   c. Look up the phase definition.
   d. If the phase has a handler → call the handler, get back a proposal or None.
   e. If the phase is simple → check task status, create task or advance.
   f. If the handler returned None or simple phase completed → advance to next phase, repeat from (c) for the new phase.
   g. If we ran out of phases → complete the sprint, return None.
   h. If we have a proposal → return it with sprint metadata.
4. Back in `create_next_leader_task`: create the AgentTask records from the proposal, broadcast via WebSocket, queue for execution.
5. Done. Wait for next event.

## Why This Design

The previous design had each leader reimplementing the entire orchestration loop from scratch. Sales wrote its own "check if task is done" queries. Writers room wrote its own. They used slightly different query patterns, slightly different status checks, slightly different advancement logic. When a bug appeared in one, it didn't get fixed in the other.

The new design puts all the mechanical parts in one place (the base class) and keeps only the genuinely different parts in each leader. Sales is mostly configuration — 5 of 7 phases are just data. Writers room has real complexity in its stage sub-machine, but it doesn't have to worry about phase advancement, sprint completion, or task status queries.

When we add a new department (e.g., engineering, marketing), it inherits the tested base class machinery and only needs to define its phases and any custom handlers. The boring parts are solved once.
