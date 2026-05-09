# Architecture

How the agentic-pipeline plugin is organized, what runs where, and which
artifact each stage produces.

This document is for two audiences:

1. **Operators** who want to understand what the plugin does on their
   machine before they trust it with a real codebase.
2. **Contributors** who want to add a new pipeline type, a new role, or a
   new policy check without breaking the contract the rest of the system
   depends on.

If you only want to run a pipeline, read [`USER-MANUAL.md`](USER-MANUAL.md)
first. This document assumes you have already done at least one run.

---

## 1. The big picture

The plugin orchestrates work across **three layers**:

1. **Plugin layer** (`agentic-pipeline/`) — the slash commands, the
   stage definitions, the role files, and the policy scripts. Versioned,
   shared across all your projects.
2. **Project layer** (`<your-project>/`) — copies of the pipeline
   definitions, role files, and policy scripts that `/pipeline-init`
   scaffolded into your project. Yours to customize.
3. **Run layer** (`<your-project>/.agent-runs/<run-id>/`) — one directory
   per pipeline run, containing the manifest, every produced artifact,
   and the append-only `run.log`. Gitignored by default.

```mermaid
flowchart TB
    subgraph PluginLayer["Plugin layer (one install per machine)"]
        direction LR
        A1[".claude-plugin/plugin.json"]
        A2["commands/<br/>pipeline-init<br/>new-run<br/>run-pipeline"]
        A3["pipelines/<br/>feature.yaml<br/>bugfix.yaml<br/>roles/*.md"]
        A4["scripts/<br/>check_*.py<br/>run_all.py"]
    end

    subgraph ProjectLayer["Project layer (per repo, after /pipeline-init)"]
        direction LR
        B1["CLAUDE.md"]
        B2[".pipelines/<br/>copies of YAMLs<br/>copies of roles/"]
        B3["scripts/policy/<br/>copies of check scripts"]
        B4[".gitignore<br/>(adds .agent-runs/)"]
    end

    subgraph RunLayer["Run layer (per pipeline invocation)"]
        direction LR
        C1[".agent-runs/&lt;run-id&gt;/<br/>manifest.yaml<br/>research.md<br/>plan.md<br/>...<br/>manager-decision.md<br/>run.log"]
    end

    PluginLayer -- "/pipeline-init copies into" --> ProjectLayer
    ProjectLayer -- "/new-run + /run-pipeline produce" --> RunLayer
```

The strict separation matters: when an agent stage runs, it only sees the
project layer and the run layer. The plugin layer is read-only template
material; once scaffolded, your project's behavior is yours.

---

## 2. Stage flow — feature pipeline

The default `feature` pipeline runs eight stages in order. Three of them
are **human-approval gates** (orange). One is an **automated policy
gate** (yellow). The rest are agent stages (blue) that delegate to a
fresh subagent per stage.

```mermaid
flowchart TB
    Start([User runs /new-run feature my-task]) --> M[manifest<br/>role: human]
    M -- APPROVE --> R[research<br/>role: researcher<br/>artifact: research.md]
    R --> P[plan<br/>role: planner<br/>artifact: plan.md]
    P -- APPROVE --> TW[test-write<br/>role: test-writer<br/>artifact: failing-tests-report.md]
    TW --> E[execute<br/>role: executor<br/>artifact: implementation-report.md]
    E --> POL[policy<br/>role: pipeline<br/>command: scripts/policy/run_all.py<br/>artifact: policy-report.md]
    POL -- exit 0 --> V[verify<br/>role: verifier<br/>artifact: verifier-report.md]
    V --> MGR[manager<br/>role: manager<br/>artifact: manager-decision.md]
    MGR -- APPROVE --> Done([Pipeline complete])

    M -. BLOCKED .-> Stop1([Stop])
    P -. BLOCKED .-> Stop2([Stop])
    POL -. exit != 0 .-> Stop3([Stop])
    MGR -. BLOCK or REPLAN .-> Stop4([Stop])

    classDef human fill:#ffd9b3,stroke:#cc6600,color:#000
    classDef agent fill:#cce5ff,stroke:#0066cc,color:#000
    classDef policy fill:#fff3b3,stroke:#999900,color:#000
    classDef stop fill:#ffb3b3,stroke:#cc0000,color:#000

    class M,P,MGR human
    class R,TW,E,V agent
    class POL policy
    class Stop1,Stop2,Stop3,Stop4 stop
```

The `bugfix` pipeline collapses test-write and execute into a single
**reproduce → patch** sequence, but the gate structure is identical:
manifest gate at the start, plan gate after research, manager gate at
the end.

---

## 3. Artifact data flow

Each stage reads every prior artifact and writes exactly one new one.
This is what makes the pipeline resumable — at any point, the run
directory is the complete state.

```mermaid
flowchart LR
    subgraph Inputs["Stage inputs"]
        I0["manifest.yaml<br/>(human)"]
    end

    I0 --> R["research.md<br/>(researcher)<br/>+ surfaces director<br/>decisions"]
    I0 --> P["plan.md<br/>(planner)<br/>uses research +<br/>director choices"]
    R --> P
    I0 --> TW["failing-tests-report.md<br/>(test-writer)<br/>tests written, all RED"]
    R --> TW
    P --> TW
    I0 --> E["implementation-report.md<br/>(executor)<br/>code, tests now GREEN"]
    R --> E
    P --> E
    TW --> E
    E --> POL["policy-report.md<br/>(automated)<br/>allowed_paths,<br/>no TODOs, ADRs"]
    POL --> V["verifier-report.md<br/>(verifier)<br/>independent check vs.<br/>manifest exit criteria"]
    I0 --> V
    R --> V
    P --> V
    TW --> V
    E --> V
    V --> MGR["manager-decision.md<br/>(manager)<br/>PROMOTE / BLOCK / REPLAN<br/>cites verifier verbatim"]
    POL --> MGR
    I0 --> MGR

    classDef human fill:#ffd9b3,stroke:#cc6600,color:#000
    classDef agent fill:#cce5ff,stroke:#0066cc,color:#000
    classDef policy fill:#fff3b3,stroke:#999900,color:#000
    class I0 human
    class R,P,TW,E,V,MGR agent
    class POL policy
```

Two important properties of this flow:

- **Append-only.** No stage modifies a prior artifact. The verifier reads
  the executor's report; it does not edit it.
- **Manager has full context.** The PROMOTE/BLOCK/REPLAN decision is made
  by an agent that has read everything and must cite verifier evidence
  verbatim. It cannot be polite or encouraging — the role file forbids
  it.

---

## 4. The three human gates

Every gate uses the same pattern: the prior stage produces an artifact,
the orchestrator pauses, and the human types `APPROVE` or describes a
block. There is no "approve with caveats" — caveats become a block, the
caveats become the next manifest.

```mermaid
sequenceDiagram
    participant U as User
    participant O as Orchestrator
    participant A as Agent (subagent)
    participant FS as .agent-runs/&lt;run-id&gt;/

    Note over U,FS: GATE 1 — manifest
    U->>O: /new-run feature my-task
    O->>FS: write manifest.yaml skeleton
    O-->>U: "Fill in manifest, then re-invoke /run-pipeline"
    U->>FS: edit manifest.yaml
    U->>O: /run-pipeline feature 2026-05-09-my-task
    O->>U: AskUserQuestion: APPROVE manifest?
    U->>O: APPROVE
    O->>FS: append run.log: manifest COMPLETE

    Note over U,FS: GATE 2 — plan
    O->>A: spawn researcher subagent
    A->>FS: write research.md
    O->>A: spawn planner subagent
    A->>FS: write plan.md
    O->>U: AskUserQuestion: APPROVE plan?
    U->>O: APPROVE
    O->>FS: append run.log: plan COMPLETE

    Note over U,FS: AGENT STAGES (no gate)
    O->>A: test-writer
    A->>FS: failing-tests-report.md
    O->>A: executor
    A->>FS: implementation-report.md
    O->>O: bash policy run
    O->>FS: policy-report.md
    O->>A: verifier
    A->>FS: verifier-report.md
    O->>A: manager
    A->>FS: manager-decision.md

    Note over U,FS: GATE 3 — manager-decision
    O->>U: AskUserQuestion: APPROVE manager decision?
    U->>O: APPROVE
    O->>FS: append run.log: manager COMPLETE
    O-->>U: Pipeline complete
```

If the user types anything other than `APPROVE` at any gate, the
orchestrator writes `BLOCKED` to `run.log` and stops. Re-invoking the
same `/run-pipeline` later resumes from the next non-`COMPLETE` stage.
The log is the resume key.

---

## 5. What an agent stage actually sees

When the orchestrator spawns a subagent, it builds a prompt with three
pieces:

1. **Role file** (`.pipelines/roles/<role>.md`) verbatim — the contract
   for what this role does and what it never does.
2. **Run context** — the manifest plus every prior artifact, joined with
   `--- <filename> ---` separators.
3. **Run instructions** — the run id, the working directory, and the
   expected output filename.

```mermaid
flowchart TB
    subgraph Prompt["Prompt sent to fresh subagent"]
        Role["1. Role file content<br/>(verbatim)"]
        Sep1["---"]
        RC["2. RUN CONTEXT:<br/>--- manifest.yaml ---<br/>(content)<br/>--- research.md ---<br/>(content)<br/>--- plan.md ---<br/>(content)<br/>..."]
        Sep2["---"]
        Inst["3. RUN ID: 2026-05-09-my-task<br/>WORKING DIR: .agent-runs/.../<br/>Write your output to<br/>.agent-runs/.../&lt;artifact&gt;<br/>and stop."]
    end

    subgraph Agent["Subagent (general-purpose, fresh context)"]
        Read["Read inputs<br/>(no prior session)"]
        Work["Do the role's work<br/>(role file forbids overreach)"]
        Write["Write artifact<br/>to expected path"]
        Stop["Exit"]
    end

    Prompt --> Agent
    Read --> Work --> Write --> Stop
```

The orchestrator does **not** share its conversation history with the
subagent. The subagent sees the prompt and the filesystem. That is by
design: each stage starts with a clean head and only the artifacts on
disk.

---

## 6. The policy stage

The policy stage is the only non-agent automation in the pipeline. It
runs `python scripts/policy/run_all.py --run <run-id>`, which executes
each check in `CHECKS` and aggregates results. Exit code 0 means
PROMOTE-eligible; non-zero halts the run.

```mermaid
flowchart TB
    Start([orchestrator runs<br/>scripts/policy/run_all.py --run X]) --> Loop{For each check<br/>in CHECKS}
    Loop --> AP[check_allowed_paths.py<br/>--manifest .agent-runs/X/manifest.yaml]
    AP --> AP_OK{exit 0?}
    AP_OK -- yes --> NT[check_no_todos.py<br/>--exclude-paths foo,bar]
    AP_OK -- no --> Fail([fail with stdout])

    NT --> NT_OK{exit 0?}
    NT_OK -- yes --> AG[check_adr_gate.py<br/>--manifest .agent-runs/X/manifest.yaml]
    NT_OK -- no --> Fail

    AG --> AG_OK{exit 0?}
    AG_OK -- yes --> More{More checks?}
    AG_OK -- no --> Fail

    More -- yes --> Loop
    More -- no --> Pass([all pass — exit 0])

    classDef pass fill:#b3f0b3,stroke:#009900,color:#000
    classDef fail fill:#ffb3b3,stroke:#cc0000,color:#000
    class Pass pass
    class Fail fail
```

The default check set is generic. To add project-specific checks,
edit `scripts/policy/run_all.py` and append entries to `CHECKS`. Each
check is a list of CLI args; `run_all.py` runs them, captures stdout +
stderr, and reports any non-zero exit.

Examples of project-specific checks worth adding:

- `check_no_secrets.py` — scan diff for credential patterns
- `check_ffmpeg_wrapper.py` — enforce that all ffmpeg calls go through
  the wrapper module
- `check_no_console_log.py` — block `console.log` in production source

---

## 7. The run.log resume mechanism

The `run.log` is the source of truth for "what's done." It is
append-only. Each line is one stage outcome. The orchestrator parses it
to decide where to start.

```
2026-05-09T14:30:00Z | manifest | COMPLETE | human approved
2026-05-09T14:32:11Z | research | COMPLETE | research.md written
2026-05-09T14:35:42Z | plan | COMPLETE | plan.md written
2026-05-09T14:35:50Z | plan | COMPLETE | human approved
2026-05-09T14:42:01Z | test-write | COMPLETE | failing-tests-report.md written
2026-05-09T14:51:33Z | execute | FAILED | artifact not produced (or empty)
```

```mermaid
stateDiagram-v2
    [*] --> ReadLog
    ReadLog --> ParseStages: read .agent-runs/X/run.log
    ParseStages --> FindResume: collect COMPLETE stage names
    FindResume --> AllDone: all stages COMPLETE?
    FindResume --> RunStage: first non-COMPLETE stage
    AllDone --> WrapUp
    RunStage --> WriteOutcome: stage handler runs
    WriteOutcome --> CheckOutcome
    CheckOutcome --> NextStage: COMPLETE
    CheckOutcome --> Halt: BLOCKED or FAILED
    NextStage --> FindResume
    Halt --> [*]: tell user resume command
    WrapUp --> [*]
```

This means:

- A `BLOCKED` or `FAILED` line does **not** mark the stage as done.
  Re-running picks up at that stage.
- The user never edits `run.log`. If a stage's outcome is wrong, the fix
  is in the underlying artifact or manifest, not the log.
- Crash-safety: if the orchestrator dies mid-stage, the missing
  `COMPLETE` line means the next run starts at that stage cleanly.

---

## 8. File layout — every file explained

```
agentic-pipeline/                        # the plugin
├── .claude-plugin/
│   └── plugin.json                      # plugin metadata, version
├── README.md                            # quick-start
├── USER-MANUAL.md                       # operator-facing
├── ARCHITECTURE.md                      # this file
├── CHANGELOG.md                         # version history
├── LICENSE                              # Apache-2.0
├── docs/
│   └── index.html                       # GitHub Pages landing page
├── commands/
│   ├── pipeline-init.md                 # /pipeline-init logic
│   ├── new-run.md                       # /new-run logic
│   └── run-pipeline.md                  # /run-pipeline logic (orchestrator)
├── pipelines/
│   ├── feature.yaml                     # 8-stage feature flow
│   ├── bugfix.yaml                      # 7-stage bugfix flow
│   ├── manifest-template.yaml           # blank skeleton
│   └── roles/
│       ├── researcher.md                # surfaces director decisions
│       ├── planner.md                   # produces plan.md §1-7
│       ├── test-writer.md               # writes failing tests only
│       ├── executor.md                  # makes tests green
│       ├── verifier.md                  # independent fresh-context check
│       └── manager.md                   # PROMOTE/BLOCK/REPLAN decision
└── scripts/
    ├── __init__.py
    ├── check_allowed_paths.py           # diff vs. manifest allowed_paths
    ├── check_no_todos.py                # scan for TODO/FIXME/HACK
    ├── check_adr_gate.py                # ADRs are append-only
    └── run_all.py                       # check runner
```

After `/pipeline-init`, your project gets:

```
<your-project>/
├── CLAUDE.md                            # scaffolded if absent
├── .gitignore                           # adds .agent-runs/
├── .pipelines/                          # copy of plugin's pipelines/
│   ├── feature.yaml
│   ├── bugfix.yaml
│   ├── manifest-template.yaml
│   └── roles/...
├── scripts/policy/                      # copy of plugin's scripts/
│   ├── __init__.py
│   ├── check_allowed_paths.py
│   ├── check_no_todos.py
│   ├── check_adr_gate.py
│   └── run_all.py
└── .agent-runs/                         # gitignored, created on first /new-run
    └── <run-id>/
        ├── manifest.yaml
        ├── research.md
        ├── plan.md
        ├── failing-tests-report.md
        ├── implementation-report.md
        ├── policy-report.md
        ├── verifier-report.md
        ├── manager-decision.md
        └── run.log
```

---

## 9. Extension points

The plugin is designed for projects to extend, not fork. The places to
extend:

| Extension | Where | Constraint |
|---|---|---|
| New pipeline type | `.pipelines/<name>.yaml` | Must use existing role names or add a role file |
| New role | `.pipelines/roles/<name>.md` | Must produce exactly one named artifact and stop |
| New policy check | `scripts/policy/check_<name>.py` + entry in `CHECKS` | Exit 0 = pass, non-zero = fail; print to stdout |
| Project conventions | `CLAUDE.md` | Roles read this; the planner is required to honor it |
| Manifest fields | `.pipelines/manifest-template.yaml` | Add field + inline comment; downstream roles may reference it |

Anti-patterns to avoid:

- Editing the role files mid-run. The contract changes mid-flight and the
  manager's verdict becomes meaningless.
- Editing the manifest mid-run. The orchestrator treats the manifest as
  immutable; if it needs to change, the manager returns REPLAN and you
  re-issue `/new-run`.
- Adding a stage that produces multiple artifacts. The pipeline's resume
  logic and the verifier's input both depend on one-artifact-per-stage.
- Removing the manifest, plan, or manager gates. The plugin is built
  around three explicit gates; removing one means the run can promote
  without human review at a critical moment.

---

## 10. Why these defaults

Several non-obvious defaults exist because of real failures from prior
projects.

| Default | Reason |
|---|---|
| Three human gates, not two or four | Fewer means autonomous-mode-by-stealth; more means humans rubber-stamp |
| Manager must cite verifier verbatim | Encouragement and summarization let bad runs PROMOTE |
| Policy checks exit non-zero halts pipeline | "It's just a warning" is how scope creep gets in |
| Halt applies to ALL repo state, including unrelated cleanup | Otherwise an agent merges in-flight work while a question is open |
| `run.log` is append-only | Editing the log to "fix" a stage hides the underlying bug |
| Subagents have fresh context | Otherwise the executor inherits the planner's blind spots |
| Manifest has `forbidden_paths` not just `allowed_paths` | Belt-and-suspenders for high-risk dirs (e.g., production configs) |
| `definition_of_done` is required | Without it, the verifier has no objective check |
| Director-decisions are surfaced by the researcher, not the planner | The planner picks; if the researcher picked, no human got to weigh in |
| Cleanroom CI is recommended, not enforced | Some projects don't have Docker available; recommend strongly, don't gate |

If you find yourself wanting to override one of these, that's a real
decision worth recording in your project's `docs/adr/` directory.

---

## 11. Sequence summary — what happens end-to-end

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant CC as Claude Code
    participant Plugin as agentic-pipeline plugin
    participant Proj as your project
    participant Runs as .agent-runs/&lt;run-id&gt;/

    U->>CC: /pipeline-init
    CC->>Plugin: read commands/pipeline-init.md
    CC->>U: ask: PRD / repo / description?
    U->>CC: PRD path or repo URL or description
    CC->>Proj: scaffold .pipelines/, scripts/policy/, CLAUDE.md
    CC->>U: orientation summary; suggest /new-run

    U->>CC: /new-run feature my-task
    CC->>Plugin: read commands/new-run.md
    CC->>Runs: create dir + manifest.yaml skeleton
    CC->>U: display manifest; instruct to fill in
    U->>Runs: edit manifest.yaml

    U->>CC: /run-pipeline feature 2026-05-09-my-task
    CC->>Plugin: read commands/run-pipeline.md
    loop for each stage
        CC->>Runs: read run.log to find resume point
        alt human gate
            CC->>U: AskUserQuestion: APPROVE?
            U->>CC: APPROVE or block
        else policy stage
            CC->>Proj: bash scripts/policy/run_all.py
        else agent stage
            CC->>Plugin: read role file
            CC->>CC: spawn subagent with role + context
            CC->>Runs: subagent writes artifact
        end
        CC->>Runs: append run.log line
    end
    CC->>U: pipeline complete; show manager decision
```

---

## 12. Glossary

- **Manifest** — the human-authored contract for a single run. Lists
  goal, allowed paths, forbidden paths, non-goals, expected outputs,
  required gates, risk, rollback plan, definition of done, director
  notes.
- **Stage** — one entry in the pipeline YAML. Has a `name`, a `role`, an
  `artifact`, and optionally a `gate` or a `command`.
- **Role** — the kind of work a stage does. Defined in
  `.pipelines/roles/<role>.md`.
- **Artifact** — the single named file a stage produces, written into
  `.agent-runs/<run-id>/`.
- **Gate** — a checkpoint where the pipeline halts. Either
  `human_approval` (operator must type APPROVE) or implicit (a failing
  policy check or empty artifact).
- **Subagent** — a fresh Claude Code agent spawned by the orchestrator
  for a single stage. Has no memory of the orchestrator's session.
- **Run ID** — `YYYY-MM-DD-<slug>`, the directory name under
  `.agent-runs/`.
- **Director** — the human who approves the manifest, the plan, and the
  manager decision.
- **Director notes** — free-form section in the manifest where the
  director records goals, constraints, and prior decisions that the
  researcher must surface.
- **Cleanroom CI** — a Docker-based reproduction of the test environment
  with a fresh dependency set, used to catch "works on my machine"
  bugs that local pytest misses.
