# Bounded Git-policy authority support

Target: the pinned Odoo 19 Community image and the suite's native `project_agile_git` repository rules. This is a support classifier, not an expression engine or alternative permission evaluator. Odoo evaluates actual ACLs and record rules under each persisted non-superuser identity.

## Approved amendment

Jimmy authorized the bounded revoke-only Task observer on September 30, 2026, on task `t_0ef017bf`, starting from rejected commit `933ac40da92a81a1c48503a2ab80078ebf2db77a`. This amends the rules phase only: no evaluator, scheduler, policy-initiated Task write, trusted-context bypass, or early concurrency-fence field. No publication, deployment or live activation is authorized.

## Exact supported native profile

The checked-in `models/policy_authority_profile.py::NATIVE_RULES` is the authoritative allowlist. It records each exact XML identity, model, SHA-256 of its unevaluated normalized Python AST, complete applicable groups, and read/write/create/unlink permissions. All listed definitions must be installed, active and unchanged, including definitions not currently selected by one actor's groups. Whitespace/comments do not change an AST; identifiers, operators and literal values do. Live `ir.model.data` queries resolve identities rather than stale XML-ID lookup caches. Native XML-ID mappings, rules, ACLs and group edits revoke epochs.

Runtime baseline evidence was read from a fresh standalone disposable database, not inferred from another Odoo version. The native Project security source hash remains `34698c4ee327698a9056e7e6ee0e7beec9bc2a0d7c4c89eb4919fe50e9441cb8`; base security is `9d63f5ec1fbd084b036b8f94a3d7a258055f57a605a1d3135a42446d042363db`. The baseline includes auto-installed `project_todo.task_edition_rule_internal`. The run's authority-metadata evidence retains exact domain text, normalized AST, fingerprints, group identities and permission flags. Approval/current validation repeat the checked-in definitions against the actual installed database.

Supported native dependencies and observers:

| Native rule family | Mutable inputs | Revoke-only observer |
| --- | --- | --- |
| Project, Task and repository company rules | Task/project/company scope; identity company membership | Project/Task/repository/user edits; Task descendant old/new scope enumeration |
| Project/repository internal-user follower visibility | Project privacy, Project followers, actor partner identity | Project edits, follower removal/reassignment, user partner edits |
| Task employee/Project-user visibility | Task project, Project privacy/followers, Task followers/assignees, actor identity | Project/Task edits, follower hooks, user/group hooks; native personal-stage table alias create/write/unlink and Task.personal_stage_type_ids |
| Task manager, private-task and project_todo rules | Task project, parent, assignees; actor groups | Task create/write/unlink and native parent descendant propagation; user/group hooks |
| Stage manager/personal visibility | Stage user, project relations, actor groups | Stage edits, both Stage.project_ids and Project.type_ids directions (including new Project creation with shared stages), user/group hooks |
| Native identity company/share rule | User share and company membership; effective groups | User and inverse company/group membership hooks; company archival |
| Computed Project company | Analytic account or partner company | Project account/partner edits and native analytic-account/partner company edits/deletion |

The checked-in `FIELD_PROFILE` also requires exact field types, storage, compute method and declared dependencies. Unknown related, company-dependent or context-dependent behavior is rejected. Direct stored Task `name` and `active` were verified in the actual registry. Computed Task project/company, display-in-project and native follower dependencies are explicit; parent edits capture descendant projects before and after native recomputation rather than presuming each descendant receives a public write.

Native `project.task.stage.personal` aliases the `project_task_user_rel` assignment table. Its create/write/unlink paths can alter Task assignees without Task.write, and native alias mutations may leave a previously cached Task.user_ids value stale. Fixed revoke-only alias hooks observe those paths; tests explicitly invalidate that cache before verifying actual assignment removal. Task.personal_stage_type_ids edits are conservatively observed too. Exact installed `addons/project/models/project_task_stage_personal.py` SHA-256: `c16d187608ae206cd530f93ff43a6515fedfb562f7d64a984c587ff0fc48b034`. A matching table alias/registry profile is not an access grant or evidence of a completed apply concurrency proof.

## Only supported custom extension

Additional applicable Task read/write rules may use only direct native stored `name` and `active`, `=`, `!=`, `in`, `not in`, literal field-appropriate values, and prefix `&`, `|`, `!` or ordinary implicit AND. Limits: 8192 source characters, 127 tokens, 64 leaves, 64 values per membership list, 255 characters per name literal, and 128 active relevant read/write rules across the supported models. This parses existing installed administrator rules as data; it adds no configurable expression field or public evaluator.

Dotted paths, other Task fields (including stage/state), computed/related fields, user/context/time references, calls, wildcard operators, malformed boolean trees and unclassified rules fail closed. Custom Project/repository/stage/identity rules are initially unsupported. Portal profiles are never eligible; a portal rule made applicable to an internal actor fails classification. Unknown dependencies require a reviewed profile extension, not an operator toggle or a caller context flag.

Owner, distinct approver and executor all receive native repository/Project checks and concrete Task read/write checks at activation and current validation. Unknown profiles prevent approval before approval timestamps/pointers are written. Existing native permissions are still honored on ordinary configuration/read boundaries; refusal to activate does not widen those permissions.

## Terminal invalidation and availability tradeoff

Successful native Task creation/deletion and supported authority-input edits conservatively revoke old/new affected Project epochs even when access did not decrease. Bulk edits preserve native recordset behavior. Ordinary name/active edit then restoration requires a successor revision and fresh approval/cutoff; validation need not run during the denied interval. A denied mutation or enclosing rollback commits no tombstone or partial business state. Hooks run within normal ORM transactions and preserve `super()`; caller context cannot skip them.

Security/XML-ID edits, inverse company/group membership changes, company archival and native partner/analytic-company changes conservatively revoke all epochs. These uncommon global dependency edits deliberately trade availability for complete coverage; they never grant access. Project stage-relation edits similarly invalidate the whole Project rather than trying to retain unrelated approvals. Normal stage/state writes are not covered by custom stage/state-based rules, since those rules are unsupported; there is no blanket trusted policy-write bypass.

The Task observer fences old/requested Project controls before native Task row mutation in sorted ID order. Requested IDs/defaults affect only lock coverage; they never grant permission and normal `super()` record/company checks remain authoritative. Nested child commands conservatively fence existing policy Projects to avoid child/control lock inversion. Schema-only installation/uninstallation checks protect the optional table boundary; no context key can disable the observer.

Native Agile keyed Tasks still cannot move between Projects. Tests preserve that invariant and use native unkeyed Tasks for successful old/new scope and descendant propagation checks. The classifier does not turn a denied native business operation into a permitted one.

## Recovery and later phases

Retain tombstones; restore native configuration/access, create a successor and obtain fresh distinct-user approval. A restored current fingerprint is never evidence that temporary historical loss was observed. Trusted server code and direct database administration remain the trust root; hot monkey patches or new business/access override code require separate exact-source review, not just a matching domain hash.

The later evaluator/apply phases must revalidate this supported profile, concrete access and revocation under ADR-012's control locks. Independent-connection apply/manual-edit/disable race and lock-fence proofs belong to the later apply slice; this rules-phase observer is not a completed concurrency executor. If a later effect touches a supported authority input, reconcile its terminal revocation and lock order without a context bypass. No scheduler/effect is implemented or activated here.
