# Hermes Mission Brief: Odoo 19 Agile Software Delivery Suite

## Mission

Design and begin implementation of a modular Odoo 19 suite that makes **Odoo Project +
Knowledge a credible software-delivery workspace for Agile/Scrum teams**, with later
integration to Git providers such as GitHub, GitLab, and Bitbucket.

The goal is **not** to recreate Jira or Confluence inside Odoo.

The goal is to add the software-development semantics that Odoo lacks while preserving
native Odoo behavior and taking advantage of Odoo's broader ERP capabilities.

The target experience should eventually provide:

- Product and Sprint Backlogs
- configurable work-item types
- Epic / Story / Task hierarchies
- story-point estimation
- Sprint planning and lifecycle
- acceptance criteria
- Definition of Ready / Definition of Done
- release/version management
- velocity, burndown, burnup, and scope-change analytics
- Project ↔ Knowledge integration
- repository / branch / commit / PR visibility
- configurable Git-driven workflow automation
- optional Jira migration tooling

---

# 1. North Star

> **Make Odoo Project and Knowledge a credible, integrated software-delivery workspace
> without sacrificing the ERP capabilities that make Odoo valuable.**

The suite should feel natural to teams coming from Jira + Confluence + GitHub/Bitbucket,
but the implementation must remain **Odoo-native first**.

Do not force Odoo to mimic Jira's data model where native Odoo concepts already solve
the problem.

---

# 2. Architectural Rules

These rules are non-negotiable unless the team documents a compelling reason to deviate.

### Rule 1 — `project.task` remains the work item

Do not introduce a parallel issue model.

Epics, Stories, Bugs, Tasks, Spikes, and other Agile items remain `project.task` records
with additional metadata.

### Rule 2 — Use native Odoo hierarchy

Odoo 19 supports recursive task hierarchy through `parent_id` / `child_ids`.

Do not make an external ancestor module foundational merely to support:

```text
Epic
└── Story
    └── Task
        └── Subtask
```

Optional hierarchy helpers may be evaluated later for reporting or performance.

### Rule 3 — Use native task dependencies

Use Odoo's existing blocking relationships for:

```text
Blocked By
Blocks
```

Only introduce a new semantic relationship model for relationships Odoo does not
represent, such as:

```text
Relates To
Duplicates
Clones
Supersedes
Tests
Caused By
```

### Rule 4 — A Sprint is not a Milestone

Create a dedicated:

```python
project.sprint
```

A Sprint may optionally reference an Odoo `project.milestone`, but the two concepts must
remain distinct.

### Rule 5 — Agile must be opt-in

Installing this suite must not alter the behavior of ordinary non-Agile Odoo Projects.

Agile behavior should be enabled per project.

### Rule 6 — Scrum is optional

`project_agile` must remain useful independently from Scrum.

Scrum-specific behavior belongs in `project_scrum`.

### Rule 7 — Agile terminology is configurable

Do not hardcode a Jira hierarchy.

Work-item types and allowed parent/child relationships should be configurable.

### Rule 8 — Knowledge is first-class

Do not build a custom wiki.

Use Odoo Knowledge for architecture documentation, ADRs, runbooks, retrospectives,
Definition of Done, release notes, and related project documentation.

### Rule 9 — Git integrations report facts

A Git connector may report:

```text
PR merged
CI failed
branch created
commit pushed
```

It should not intrinsically decide:

```text
Task = Done
```

A separate configurable automation layer determines workflow effects.

### Rule 10 — Historical Scrum data must remain historical

Never calculate past Sprint commitment exclusively from the tasks currently assigned to
a Sprint.

Scope changes must be captured as events or snapshots.

### Rule 11 — Custom OWL UX comes later

A Jira-like Sprint planning UI is valuable, but the backend must first be fully usable
through ordinary Odoo views and actions.

### Rule 12 — Prefer contribution over duplication

Where an OCA project already solves or is actively solving the problem, investigate
extending or forward-porting it before creating a competing implementation.

---

# 3. Proposed Module Layout

Target module structure:

```text
addons/
├── project_agile/
├── project_scrum/
├── project_scrum_analytics/
├── project_agile_knowledge/
├── project_agile_git/
├── project_agile_ui/
└── project_agile_jira_import/
```

Provider modules may ultimately live separately:

```text
project_git
├── project_github
├── project_gitlab
└── project_bitbucket
```

Do not create all of these immediately.

The first implementation target is:

```text
project_agile
project_scrum
```

with analytics following once the Sprint lifecycle is stable.

---

# 4. Phase 1 — `project_agile`

## Objective

Create the smallest stable domain layer required to treat Odoo Projects as
software-development workspaces.

## Extend `project.project`

Proposed configuration fields:

```python
agile_enabled
agile_methodology
agile_key
default_item_type_id
estimation_method
```

Initial `agile_methodology` values:

```text
none
agile
scrum
kanban
```

Do not assume these exact field names are final. Validate naming against Odoo
conventions before implementation.

---

## Work-Item Types

Introduce:

```python
project.agile.item.type
```

Candidate fields:

```text
name
code
sequence
active
color
icon

can_have_parent
can_have_children

allowed_parent_type_ids
allowed_child_type_ids

uses_estimation
can_schedule_in_sprint
```

Seed reasonable defaults:

```text
Epic
Feature
Story
Bug
Task
Spike
Subtask
```

The model must support customer-specific types without Python changes.

---

## Extend `project.task`

Expected Agile fields:

```python
agile_item_type_id
agile_key
story_points
acceptance_criteria
backlog_sequence
```

Do not duplicate fields that Odoo 19 already provides.

---

## Task Keys

Tasks need stable identifiers such as:

```text
ENG-142
WEB-31
OPS-8
```

Requirements:

- generated from project Agile key + sequence;
- unique;
- indexed;
- stable after assignment;
- suitable for branch names, PR titles, and commit messages.

Investigate the best Odoo-native sequence strategy before implementation.

---

## Story Points

Story points belong to the core Agile module.

Initial implementation may simply use:

```python
story_points = fields.Float()
```

Project configuration should prepare for estimation strategies such as:

```text
none
numeric
fibonacci
t_shirt
hours
```

Do not overengineer all estimation strategies in the first implementation.

For MVP:

```text
none
fibonacci
```

is sufficient if that keeps the data model clean.

---

## Hierarchy Validation

Use native `parent_id`.

The Agile layer should optionally enforce parent-child type policies.

Example:

```text
Epic
 ├── Story
 ├── Bug
 └── Spike

Story
 ├── Task
 └── Subtask
```

But this must come from configuration, not hardcoded `if type == "story"` logic.

Prevent invalid relationships with model-level constraints.

UI domains may improve usability, but UI filtering is not sufficient enforcement.

---

## Acceptance Criteria

Add dedicated rich-text acceptance criteria to Agile tasks.

Do not confuse task Acceptance Criteria with Definition of Done.

---

# 5. Phase 2 — `project_scrum`

## Objective

Add Scrum Sprint semantics without redefining ordinary Odoo Project behavior.

Introduce:

```python
project.sprint
```

Candidate fields:

```text
name
project_id
team_id

date_start
date_end

state
goal

task_ids
milestone_id

planned_story_points
completed_story_points
added_story_points
removed_story_points
completion_percentage
```

Lifecycle:

```text
Draft
  ↓
Active
  ↓
Closed
```

Possible later addition:

```text
Canceled
```

---

# 6. Sprint Assignment

A Sprint-eligible task may be:

```text
Unscheduled → Product Backlog

or

Assigned → Sprint
```

A task may not simultaneously belong to multiple Sprints.

Initial UI should use standard Odoo mechanisms:

- Sprint field
- filters
- grouping
- multi-record server actions
- list/Kanban views

Do not begin with a custom drag-and-drop interface.

---

# 7. Product Backlog

For the initial design:

> Product Backlog = Sprint-eligible Agile tasks that are not assigned to a Sprint.

Backlog ordering must use an explicit sequence rather than task creation date.

Support:

```text
Move up/down
Reorder
Assign selected items to Sprint
Remove selected items from Sprint
```

Investigate whether native sequence-handle widgets are sufficient.

---

# 8. Sprint Lifecycle

## Start Sprint

Starting a Sprint must:

1. validate dates;
2. ensure lifecycle constraints;
3. create the commitment snapshot;
4. mark the Sprint Active;
5. prevent silent modification of historical commitment.

Whether multiple Active Sprints may exist must be configurable by team.

Do not assume globally:

```text
one active Sprint per project
```

because one product may have multiple delivery teams.

---

## Close Sprint

Closing a Sprint must explicitly handle unfinished work.

Options should eventually include:

```text
Move to Product Backlog
Move to next Sprint
Move to selected Sprint
Leave unscheduled
```

Moving a task out of the Sprint must not erase the historical fact that it was part of
the Sprint commitment.

---

# 9. Sprint Scope History

This is required before analytics can be trusted.

Evaluate:

```python
project.sprint.scope.event
```

Candidate fields:

```text
sprint_id
task_id
event_type
story_points
timestamp
user_id
```

Candidate event types:

```text
committed
added
removed
completed
reopened
```

The design must support reconstructing:

```text
Original Commitment
Added Scope
Removed Scope
Completed Scope
Carry-Over
```

for a closed Sprint.

Do not derive those values solely from current task relationships.

---

# 10. Phase 3 — Scrum Analytics

After Sprint behavior stabilizes, add:

```text
project_scrum_analytics
```

Required first reports:

```text
Velocity
Sprint Burndown
Sprint Burnup
Scope Change
Commitment vs Completion
```

Definitions:

### Velocity

Story points completed during a closed Sprint.

### Burndown

Remaining Sprint scope over time.

### Burnup

Completed scope versus total scope over time.

### Scope Change

Show changes explicitly:

```text
Initial Commitment: 32
Added:               8
Removed:             3
Final Scope:        37
Completed:          30
```

Do not globally override Odoo Project's existing analytics.

Agile reports must be additive.

---

# 11. Phase 4 — Knowledge Integration

Module:

```text
project_agile_knowledge
```

## Objective

Make Odoo Knowledge function as the documentation half of the software-delivery
workspace.

Potential project relationship:

```python
knowledge_root_article_id
```

Suggested hierarchy:

```text
Project Name
│
├── Product
│   ├── Product Vision
│   ├── Roadmap
│   └── Personas
│
├── Engineering
│   ├── Architecture
│   ├── Development Environment
│   ├── Coding Standards
│   └── Deployment
│
├── ADRs
│
├── Agile
│   ├── Definition of Ready
│   ├── Definition of Done
│   └── Working Agreement
│
├── Releases
│
└── Retrospectives
```

Do not duplicate functionality already provided by Knowledge.

Our responsibility is:

```text
relationships
templates
navigation
conventions
automation
```

not wiki implementation.

---

## Knowledge Relationships

Investigate clean support for:

```text
Project
  ↔ Knowledge root

Task
  ↔ related articles

Sprint
  ↔ retrospective

Release
  ↔ release notes
```

Potential smart buttons:

```text
PROJECT
[Backlog] [Sprints] [Releases] [Repository] [Knowledge]

TASK
[Parent] [Children] [Dependencies] [Git] [Knowledge]

SPRINT
[Backlog] [Burndown] [Retrospective]
```

---

## Initial Knowledge Templates

Prepare:

### ADR

```text
Status
Context
Decision
Alternatives Considered
Consequences
Related Work Items
```

### Sprint Retrospective

```text
Sprint Goal
Outcome
What Went Well
What Did Not Go Well
Experiments / Actions
Owners
```

### Runbook

```text
Purpose
Dependencies
Procedure
Validation
Rollback
Escalation
```

### Release Notes

```text
Version
Release Date
Highlights
Features
Bug Fixes
Breaking Changes
Upgrade Notes
Known Issues
```

---

# 12. Git Integration Research Spike

Do **not** start by writing a new webhook stack.

First investigate current OCA work around:

```text
project_git
project_github
project_gitlab
```

Specifically evaluate the architecture proposed by OCA Project PR #1792.

Questions to answer:

1. What generic models does it introduce?
2. Which parts are provider-neutral?
3. Which parts are GitHub/GitLab-specific?
4. How are tasks matched using issue/task keys?
5. How are webhooks authenticated?
6. How are duplicate events handled?
7. What CI state is normalized?
8. What dependencies would be required to forward-port it to Odoo 19?
9. Is there meaningful upstream activity?
10. Would contributing a 19.0 port be preferable to creating a local implementation?

Produce a short ADR/research report.

Do not block `project_agile` or `project_scrum` work on this spike.

---

# 13. Target Git Architecture

Unless research demonstrates a better design, maintain this conceptual separation:

```text
Git Provider
    │
    ▼
Provider Connector
    │
    ▼
Normalized Git Models
    │
    ▼
Task Association
    │
    ▼
Agile Automation Rules
```

Potential normalized concepts:

```text
Repository
Branch
Commit
Pull Request
Pipeline / Check
Event
```

The connector records facts.

Automation decides workflow meaning.

---

# 14. Git Association

Primary matching mechanism:

```text
ENG-142
```

Support conventional strings such as:

```text
ENG-142-add-oauth
feature/ENG-142-oauth
ENG-142: Add OAuth callback support
[ENG-142] Add OAuth callback support
```

Potential sources:

```text
branch name
PR title
PR body
commit message
```

Explicit task references must win over heuristics.

---

# 15. Git Automation

Do not hardcode:

```text
PR merged = task Done
```

Instead target configurable rules conceptually like:

```text
WHEN
    Pull Request merged
AND
    target branch = main
AND
    CI = success

THEN
    move task to Ready for QA
```

Another project may configure:

```text
PR merged → Done
```

Workflow policy belongs to the Project configuration.

---

# 16. Webhook Requirements

If custom webhook infrastructure becomes necessary, require:

```text
signature/token validation
idempotency
event persistence
asynchronous processing
retry handling
failure visibility
```

Desired flow:

```text
Request
  ↓
Verify
  ↓
Persist Event
  ↓
Return 2xx
  ↓
Async Processing
  ↓
Normalize Git Data
  ↓
Associate Tasks
  ↓
Run Automation
```

Do not perform the entire workflow synchronously in the HTTP controller.

Evaluate OCA `queue_job` before inventing a worker system.

---

# 17. Phase 5 — Advanced Agile UI

Only after backend contracts stabilize should we implement:

```text
project_agile_ui
```

Potential planning experience:

```text
┌──────────────────────────┬─────────────────────────────┐
│ SPRINTS                  │ PRODUCT BACKLOG             │
│                          │                             │
│ Sprint 24                │ ENG-142 OAuth callback   5 │
│ 24 / 31 pts              │ ENG-151 Retry worker     3 │
│                          │ ENG-165 CSV import        8 │
│ Sprint 25                │                             │
│ 12 / 34 pts              │                             │
└──────────────────────────┴─────────────────────────────┘
```

Potential capabilities:

```text
drag task → Sprint
drag Sprint item → Backlog
capacity feedback
Epic context
Git status indicators
Sprint goal display
```

This must be an additive view.

Do not replace ordinary Project Kanban globally.

---

# 18. Jira Migration

Defer runtime implementation.

Potential future module:

```text
project_agile_jira_import
```

Mapping target:

```text
Jira Project      → project.project
Jira Epic         → project.task
Jira Story        → project.task
Jira Task         → project.task
Jira Bug          → project.task
Jira Sub-task     → project.task
Jira Sprint       → project.sprint
Jira Fix Version  → project.version
Jira Block Link   → native dependencies
Other Links       → semantic relationships
Comments          → chatter
Attachments       → attachments
```

Migration logic adapts Jira to the Odoo model.

Do not alter the Odoo runtime architecture merely to make Jira import easier.

---

# 19. Agent Responsibilities

## Faolan — Technical Coordinator

Own:

- decomposition;
- task routing;
- decision log;
- sequencing;
- conflict resolution;
- keeping the implementation aligned with this brief.

Faolan should prevent agents from independently inventing overlapping architecture.

Maintain a short ADR for any significant deviation.

---

## k3rn3l — Primary Builder

Own:

```text
project_agile
project_scrum
tests
views
security
demo data
```

Initial emphasis:

1. clean models;
2. constraints;
3. tests;
4. ordinary Odoo views.

Avoid early OWL work.

---

## Gilfoyle — Reviewer / Architecture Gate

Review:

- Odoo-native design;
- unnecessary custom models;
- unnecessary OCA dependencies;
- ORM correctness;
- stored computed fields;
- SQL constraints;
- security;
- performance;
- migration/upgrade risk.

Gilfoyle should specifically challenge anything that looks like:

> "We built this because Jira has one."

---

## Elara — Ecosystem Scout

Investigate:

- Odoo 19 capabilities relevant to each phase;
- OCA modules that may eliminate custom work;
- existing Agile/Scrum modules worth learning from;
- Knowledge extension patterns;
- release/version implementations.

Return concrete opportunities rather than broad idea dumps.

---

## tr4c3 — External Technical Research

Own the focused Git/OCA research spike.

Investigate:

```text
OCA project_git
project_github
project_gitlab
queue_job
project/version-related modules
```

Prefer primary sources:

```text
Odoo source
Odoo documentation
OCA repositories
OCA PRs/issues
```

Clearly distinguish:

```text
stable
migrated
draft
abandoned
experimental
```

---

## c1ph3r — Security Review

Join when webhook/provider work begins.

Threat-model:

- webhook authentication;
- replay attacks;
- duplicate deliveries;
- leaked secrets;
- forged task associations;
- malicious Git payloads;
- privilege escalation through automated task writes;
- cross-project repository access.

Do not block Phase 1 Agile domain work.

---

# 20. First Engineering Milestone

Do not attempt the whole suite immediately.

## Milestone 1: Agile Core Skeleton

Deliver a working installable:

```text
project_agile
```

containing:

### Models

```text
project.agile.item.type
extensions to project.project
extensions to project.task
```

### Functionality

```text
Agile enable/disable per project
Project Agile key
Generated task keys
Configurable work-item types
Story points
Acceptance criteria
Backlog ordering
Hierarchy validation
```

### Views

```text
Agile configuration on Project
Agile fields on Task
Item Type configuration
Backlog list
Backlog Kanban or existing Kanban filter
Agile search filters
```

### Security

Appropriate access rights for configuration models.

### Tests

At minimum:

```text
task key generation
task key uniqueness
non-Agile project behavior
item-type parent validation
item-type child validation
cycle handling relies safely on Odoo
story-point constraints if any
project isolation
```

---

# 21. Milestone 1 Acceptance Criteria

Milestone 1 is complete when:

1. the module installs cleanly on Odoo 19;
2. an ordinary Project can exist without Agile behavior;
3. Agile can be enabled for one Project without affecting another;
4. Agile work-item types can be configured without code changes;
5. a new Agile task receives a stable key such as `ENG-1`;
6. tasks may be nested using native Odoo hierarchy;
7. configured hierarchy rules prevent invalid relationships;
8. Story Points can be recorded;
9. Acceptance Criteria can be recorded;
10. unscheduled work can be viewed as a Product Backlog;
11. automated tests cover the key model constraints;
12. there is no custom JavaScript requirement.

---

# 22. Milestone 2: Scrum Foundation

After Milestone 1 approval, implement:

```text
project_scrum
```

Deliver:

```text
project.sprint
Draft / Active / Closed lifecycle
Sprint goal
Sprint task assignment
Product Backlog
Sprint Backlog
commitment snapshot
scope event history
start Sprint
close Sprint
unfinished-work handling
```

Do not start analytics until scope history is trustworthy.

---

# 23. Milestone 3: Scrum Analytics

Deliver:

```text
Velocity
Burndown
Burnup
Scope Change
Commitment vs Completion
```

Verify analytics against explicit test scenarios involving:

```text
scope added mid-Sprint
scope removed mid-Sprint
completed tasks
reopened tasks
unfinished work
carry-over
```

Historical numbers must remain unchanged after a Sprint is closed.

---

# 24. Required ADRs / Research Notes

Before or during implementation, produce short decisions for:

```text
ADR-001 Work-Item Key Generation
ADR-002 Configurable Item-Type Hierarchy
ADR-003 Sprint Scope History Strategy
ADR-004 Agile Team / Multiple Active Sprint Model
ADR-005 Release / Version Model
ADR-006 Knowledge Relationship Model
ADR-007 OCA project_git Adoption Strategy
ADR-008 Git Automation Model
```

Keep ADRs concise.

Each should record:

```text
Context
Decision
Alternatives
Consequences
Open Questions
```

---

# 25. Definition of Done for Each Module

A module is not complete because the UI works.

Require:

```text
✓ installable on clean Odoo 19 database
✓ upgrade-safe model design
✓ access controls defined
✓ model constraints tested
✓ meaningful unit/integration tests
✓ no global Project behavior regression
✓ README documents purpose and dependencies
✓ demo/test data where useful
✓ no undocumented hard OCA dependency
✓ reviewer approval
```

---

# 26. Explicit Non-Goals for Initial Development

Do not build yet:

```text
full Jira clone
custom wiki
custom Git hosting
custom CI/CD system
custom authentication
Jira migration engine
rich OWL planning board
GitHub connector from scratch
GitLab connector from scratch
Bitbucket connector
AI-generated Sprint planning
resource-capacity optimizer
advanced portfolio management
```

These may become future work.

The immediate goal is a clean domain foundation.

---

# 27. First Assignments

## Faolan

Create the initial project board/work breakdown from this brief.

Prioritize:

```text
Milestone 1
OCA/Git research spike
required ADRs
```

Do not schedule later UI work yet.

---

## Elara + tr4c3

Perform a short Odoo 19/OCA dependency audit.

Return a table:

```text
Capability
Native Odoo 19?
OCA option?
19.0 available?
Stable?
Recommendation
```

Focus specifically on:

```text
task hierarchy
task dependencies
task/project roles
task keys
versions/releases
Knowledge integration helpers
Git integrations
queue_job
```

---

## k3rn3l

Start a technical design for:

```text
project_agile
```

Produce:

```text
module tree
manifest dependencies
model definitions
constraints
sequence strategy
security model
initial views
test plan
```

Do not begin OWL components.

---

## Gilfoyle

Review k3rn3l's design before substantial implementation.

Challenge:

```text
model proliferation
stored computed fields
hardcoded Jira assumptions
unnecessary OCA dependencies
global Project overrides
upgrade-sensitive patterns
```

---

# 28. Initial Decision Gate

Before Milestone 1 implementation proceeds beyond the skeleton, the team should be able
to answer:

```text
1. Are all hard dependencies actually required?
2. Does project_agile work without Scrum?
3. Does an ordinary Project remain unchanged?
4. Are work-item types configurable?
5. Is task hierarchy native?
6. Are task keys stable and safe?
7. Is Sprint functionality isolated from Milestones?
8. Can historical Sprint scope eventually be reconstructed?
9. Does the design leave a clean integration point for Knowledge?
10. Does the design leave a clean integration point for provider-neutral Git?
```

If the answer to any of these is "no," resolve it before expanding scope.

---

# Final Direction

Build from the center outward:

```text
                   ┌─────────────┐
                   │ Agile Core  │
                   └──────┬──────┘
                          │
               ┌──────────┴──────────┐
               │                     │
            Scrum                 Knowledge
               │                     │
          Analytics                  │
               │                     │
               └──────────┬──────────┘
                          │
                         Git
                          │
                    Advanced UI
                          │
                       Migration
```

The order matters.

If the Agile domain model is clean, the later pieces become integrations.

If the Agile domain model is designed around Jira, GitHub, or a particular customer
workflow, every later phase becomes a workaround.

**Start with `project_agile`. Make the domain boring, native, testable, and extensible.
Then build outward.**
