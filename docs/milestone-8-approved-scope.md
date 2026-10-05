# Milestone 8 — Solution Definition and Requirements Traceability

## Status and authorization

Approved product direction and implementation release. On October 1, 2026 Jimmy explicitly directed: "Alright let's push milestone 7 and get milestone 8 going". Milestone 7 publication task `t_d632ae54` is complete; independent GitHub/local/tracking readback confirms clean published baseline `5376f2d2c2ada5c7e18e73b673076343671992ca` with numeric ahead/behind `0/0`. This authorizes deliberate full-graph seeding, a task-associated feature lane, reviewed M8 implementation and guarded local delivery, not M8 publication or runtime activation. The original scope tracker must not be auto-specified/decomposed; preserve it as the historical approval record and use a verified dependency-preserving one-shot release after the full graph/lane is constructed. This changes execution authorization only; the accepted product scope below is unchanged.

This file and the backlog card are scope records, not a claim that APIs, module dependencies, security, customer demand, or a full implementation plan have been validated. No real customer SOW is available. All fixtures must be clearly synthetic, not plausible-looking representations of confidential customer data or proof of market fit.

## Outcome and problem evidence

Beneficiary: software-delivery teams needing to explain why work exists, what was agreed, what remains uncertain, and how implementation covers the proposed solution. Evidence is one prospective user's request for structured models rendering a solution spec and filling an SOW skeleton. Existing delivery supplies native Agile work items, Scrum/history/analytics, optional documentation/planning, and Git facts/policy. It does not supply structured requirement identity, approved specification baselines, requirement-to-task coverage or change-impact semantics. This is an upstream extension, not a replacement task system or a retroactive expansion of M4/M7.

Desired flow: objectives or optional SOW -> solution understanding -> requirements/questions/decisions -> reviewed work-item decomposition -> existing backlog/Sprint planning -> implementation evidence -> explicit acceptance. Feedback may refine later slices; do not impose waterfall or require all detail upfront.

## Agreed first-release scope

1. **Optional solution specification:** project-associated draft/review/approved/superseded lifecycle, stable identities and immutable approved baselines. A mutable working revision must not rewrite an approved SOW/specification or historical Sprint commitments. Baseline structure/references must be reproducible even after later linked records change/archive; model actual revision links, not today's text. SOW is optional: an internal product team may start from a solution brief.
2. **Structured requirements:** FR/NFR type, stable project-scoped identifier, rationale, priority, and verifiable acceptance expectations. A requirement is delivery intent, not a duplicate `project.task`. Keep requirement acceptance distinct from Task Done or PR merge.
3. **Supporting context:** ordered narrative sections, questions/resolutions, decisions/consequences, business actors/roles and domain areas. Actor/role vocabulary describes the solution being designed, not automatically Odoo accounts/security groups. Keep the first model vocabulary small; justify separate models by identity, lifecycle, reuse or traceability rather than every noun.
4. **Explicit existing-task links:** many-to-many requirements <-> native Agile Tasks, with references to the requirement revisions addressed. One NFR may span several capabilities; one Task may address several requirements. Previewed, deliberate, authorized task creation only; retries must not duplicate Tasks. Do not overwrite manual task descriptions, workflow state, estimates, Sprint assignment/history or existing acceptance criteria on specification edits. No automatic backlog regeneration or Sprint allocation.
5. **Readable rendering:** current draft and exact approved revision can render to a meaningful solution/SOW view using native Odoo mechanisms. Rendering is a projection of structured authoritative records, not an independently editable competing master. Scope/audience rules must protect internal questions/decisions and inaccessible records in rendering/export. Do not silently omit inaccessible material and label the result a complete approved baseline. No custom wiki/editor/page-history replacement or mandatory OCA/Enterprise document backend.
6. **Coverage and change impact:** expose unlinked requirements, legitimately unlinked maintenance work, unresolved questions affecting planned work, requirements changed since a baseline, work linked to older revisions, and accepted requirements with recorded evidence. Prefer honest categories over misleading aggregate completion percentages. Manual evidence/reference recording is sufficient initially; no full test-management engine or automated acceptance inference.

## Representative SOW skeleton (chosen starting template, not an industry standard)

- Purpose, beneficiaries and expected outcomes.
- Included capabilities, excluded scope and boundaries.
- Deliverables and their evaluation expectations.
- Discovery/delivery/verification/handover approach and checkpoints.
- Customer and delivery-team responsibilities.
- Assumptions, dependencies and constraints.
- Acceptance authority, criteria and evidence.
- Proposed changes and explicit approval history.
- Optional commercial references/pricing arrangement/payment checkpoints as narrative or external references, not financial/billing logic or legal defaults.
- Approval and revision history.

Templates must be editable/project-specific rather than universally required. The SOW provides a scope skeleton; the living solution spec enriches it without silently expanding approved scope. Public examples and requirements guidance informed the discussion; the root discovery must recheck primary sources and actual Odoo 19/native/OCA alternatives before selecting APIs or dependencies. No claim of legal sufficiency or universal contract suitability.

## Synthetic acceptance fixtures

- **Customer-funded service-request portal:** defined deliverables, requester/triage roles, submission/tracking FRs, isolation/access NFR, delegation question, and a decision excluding delegation from initial scope. Trace one deliverable through explicit existing Tasks and verification/acceptance evidence.
- **Discovery-led API integration:** unresolved external-interface assumptions, dependency questions, a discovery Spike, decision changes and a reviewed scope revision. Show uncertainty as uncertainty, not invented implementation certainty.
- **Internal product initiative:** no customer SOW, company/project isolation, a solution brief, cross-cutting NFRs, maintenance work without requirement links, and deliberate planning using the current Agile/Scrum surfaces.

Include adversarial baseline immutability, revisions changed while planning, archived references, duplicate task-generation intent, hidden Project/Task/requirement IDs, multi-company/multi-project users, forged context, internal-vs-customer rendering, and rollback/no-partial-write cases. Synthetic test success proves implementation behavior, not customer validation.

## Architecture constraints and deferred scope

Provisional addon name `project_agile_solution`; finalize it in the reviewed M8 root contract. Prefer a minimal optional dependency on existing Agile/native Project; Scrum, Git, Sales and documentation remain optional bridges. Odoo.sh-first, portable to controlled self-hosting. Preserve existing license choices; review any actual new dependency/license rather than blanket-relicense. Investigate native/OCA alternatives before inventing generic components; the unrelated official OCA Task-document connector remains a standing optional blocker, not an M8 core parent.

Not included: contracts/e-signature/quoting/billing engine, mandatory Sales, custom wiki, parallel task system, full test management, AI-generated/automatic backlog or Sprint planning, automatic requirement acceptance from Task state or Git events, provider expansion, Jira migration, release management, customer portal/public service exposure or production deployment.

## Ownership, gates and delivery meaning

Faolan owns later outcome/graph shaping; k3rn3l implements a contract-and-fixture first slice; Gilfoyle exact-SHA review is required on native same-card runs; c1ph3r assesses focused authority/privacy boundaries; cumulative review precedes guarded local delivery. Publication requires a distinct exact human-approval latch. Local integration, GitHub publication, runtime deployment and live activation are separate effects.

When M7 is reconciled and published, read canonical brief/ADRs/current source/verifier, the actual target SHA, this accepted scope and existing cards before seeding. Construct the complete bounded serial DAG behind an inert gate with semantic idempotency keys. Provision a task-ID-associated remote lane from that verified baseline and record literal branch/worktree/full-SHA coordinates before code release. Do not precreate an M8 lane from today's M6 main or a rejected M7 candidate.

The first runnable M8 card must commit the accepted domain/authority/revision/rendering/traceability contract, explicit gap map, bite-sized implementation plan, synthetic fixtures, and smallest installable optional skeleton. Later cards deliver baseline/model work, requirement/context records, task traceability, native rendering/coverage, hardening/security, cumulative acceptance, guarded local delivery and separately approved publication. Canonical verification must discover the new optional module and preserve existing regressions; schema/security changes need independent install, targeted upgrade and dependency-safe uninstall/reinstall with real nonadmin and multi-company identities and browser coverage where meaningful.

## Discussion-recovery clarifications — October 1, 2026

Read against the original prospective-user idea and accepted recommendation (session `20260929_131959_e8de3165`, messages `79625`, `79641`, `79693`, `79721`, `79722`), not merely the compacted summary. These clarify the already-discussed intent; they do not release work or expand this into another product.

- **Shared lineage, separate approvals:** the optional SOW and detailed solution specification share lineage, but approval of one must not silently approve later detail, a working revision, or a scope change. Discovering additional work is not authorization to expand agreed scope.
- **Reusable narrative:** reusable section templates and project-specific narrative can describe user journeys, personas and domain concepts alongside the structured FR/NFR records. This does not require a separate model for every narrative concept.
- **Question traceability:** preserve a question's owner, affected requirements, planning/blocking significance and resolution; a question may motivate a discovery Spike linked to existing work.
- **Decision traceability:** preserve decision context, choice, consequences and affected requirements, so a team can explain which decision supports a design and what a change would affect.

## Effect boundary of this tracker

Allowed by the October 1 direction: full approved-scope graph shaping and release, isolated M8 branch/worktree creation from the verified published M7 baseline, reviewed source implementation, disposable tests and exact-SHA review, plus guarded local integration owned by the explicitly shaped delivery card. Every code worker remains bounded to its feature lane and native same-card review. M8 push/PR/tag/release, deployment/restart, live provider/policy/customer configuration, credentials/settings changes, external customer contact, destructive cleanup or persistent-data deletion remain unauthorized unless separately approved. The original M7 publication approval does not authorize M8 publication. The historical tracker is archived only after a one-shot release owns the dependency gate and all full-graph/lane invariants are verified; original approval/audit history is retained.
