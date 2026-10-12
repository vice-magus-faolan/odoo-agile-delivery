# M8 synthetic fixture and adversarial acceptance contract

## Provenance and execution boundary

All names/data/references are explicitly SYNTHETIC. Public FAR/NASA guidance informed
outcomes, boundaries, requirement identity/rationale and verifiable expectations; see
[m8-solution-alternatives.md](m8-solution-alternatives.md). This is no customer SOW,
legal template, verified external API or observed customer acceptance. `synthetic://`
references are acceptance-input labels, not actual evidence URLs. No network fetch,
customer portal route, account/group creation or financial logic is implemented.

Exact input data:
`addons/project_agile_solution/tests/fixtures/synthetic_scenarios.json`, schema
version 1. Its `warning` and event status `expected_fixture_event_not_executed` are part
of the contract. Keys such as FR1@1/T1/D1 are fixture-local aliases; downstream helpers
map them to actually allocated native/model IDs and returned requirement keys, never
force sequences or fabricate IDs. Role strings describe design roles; explicit internal
test users must be assigned separately with the least required native groups.

Root imports `tests/test_solution_lineage.py`, consumes all three scenarios and actually
creates native Agile Projects, solution lineage and ordinary Tasks, preserving manually
authored descriptions/default Task state/zero estimates. It proves the lineage action
exists, not browser delivery. Static contract tests check JSON keys and revision/Task
references. Requirement/context/approval/link/Sprint/acceptance fields are NOT root
models; data describing them is prospective executable acceptance input. Later seeded
cards progressively bind those expectations to real boundaries. Do not convert expected
events into observed successes or claim full M8 from the root seeds.

## Scenario A: customer-funded service-request design

Purpose: propose requester self-submission and own-request tracking. Optional SOW and
spec share lineage but distinct approvals. D1 depends on FR1 submission, FR2 tracking,
NFR1 project/company/metadata isolation. T1 addresses FR1@1/NFR1@1, T2 addresses
FR2@1/NFR1@1: many-to-many edges demonstrate the cross-cutting NFR. Requester/triage are
business vocabulary, not automatically Odoo security roles.

Q1 asks who may submit for another requester; its scope owner records that delegation
remains undiscovered and excluded initially. DEC1 retains context/choice/consequences;
the exclusion cannot silently become an included capability through spec editing.
Expected trace is D1 -> FR1@1 -> existing T1 -> named synthetic verification reference
-> explicit named authority acceptance of FR1@1. Task Done/PR merge is not acceptance.
The later real fixture records that event only after implementing the boundary and
checking approved revision/evidence/authority; it does not deploy the portal design.

Weaknesses: actual own-request/delegation authority is unknown; native portal sharing is
not isolation proof. Customer output excludes internal Q1 without leaking its title,
count or owner; internal baseline rendering refuses inaccessible closure. A later FR1@2
does not inherit v1 acceptance or overwrite authored Task description/criteria.

## Scenario B: discovery-led API integration

No actual schema/authentication/rate/replay guarantees are supplied. FR1@1 describes
proposed direction as pending; NFR1@1 requires duplicate-effect protection but its
verification is explicitly unresolved. Q1 belongs to the external evidence owner with an
internally responsible user; it blocks delivery and motivates existing Spike T1. DEC1
says discover before commitment, not invent integration APIs/estimates.

The `reviewed_scope_revision` is a hypothetical branch: after synthetic discovery input,
propose inbound-only FR1@2 with DEC2 context/consequences. A downstream helper creates
real successor content and separate SOW/spec approval actions. Old Spike link retains
FR1@1, mutable working context cannot rewrite the approved v1 baseline, and an approved
spec cannot silently expand its SOW scope. No discovery result is asserted as actual
behavior of an external service.

## Scenario C: internal initiative without SOW

Begin with a solution brief/spec; SOW absence does not waive spec approval. FR1@1
requests authorized operations status; NFR1@1 covers company/Project view/export
isolation and spans T1/T2. T3 intentionally has no requirements and a meaningful
maintenance reason. Coverage distinguishes maintenance from unexplained missing links.

Q1 asks which existing Sprint will deliberately take a slice; DEC1 keeps planning
manual. With optional Scrum bridge, start/add captures actual exact v1 links and status;
a later NFR1@2/current Task-link change leaves the old scope event untouched. Without
Scrum, the core still installs/operates. Installing later cannot backfill historic
context from current links; `not_available` differs from observed `empty` capture.

## Minimal conversion conventions

JSON planning labels are descriptive acceptance inputs. Convert `blocks_delegation_only`
and `blocks_delivery` to contract `blocking`, `planning_only` to `planning`, preserving
scope-specific significance narrative. Resolve named roles to explicit synthetic users
or external-owner narrative, not groups. Resolve fixture-local alias sets to exact
returned revision IDs in the same Project/company. All expected events need real native
method calls, not direct state writes, fake acceptance records or source assertions.
Keep fixture warning and expected status until an actual test separately reports proof.

## Adversarial acceptance matrix and owner

| Boundary/example                      | Required positive and negative proof                                                                                                                                                       | Seeded owner                                                                                                 |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| Root optional installation            | Actual installed module/model/XML plus imported tests without Scrum/Git/Sales/docs; ignored-addon/zero-test is failure                                                                     | Root t_f1a8ee89                                                                                              |
| Least privilege / current visibility  | Readable user's visible lineage; private/foreign/custom-denied Project absent in search/count/group/name/export and direct read; permitted export first; portal/no-group denied            | Root, then security t_4841a335                                                                               |
| Root authority / forged scope         | Manager must have concrete Project write; default/context IDs do not grant authority; bool/string/missing/foreign IDs rejected, company assignment rejected; archive retains identity      | Root                                                                                                         |
| Atomic multi-create                   | Mixed valid/invalid inputs create no partial lineage; later action failure leaves no children/results                                                                                      | Root, verification t_1f505e56                                                                                |
| Document baseline / separate approval | v1 actual content/ordered closure reproducible after rename/archive; direct ORM/RPC/x2many/context/sudo writes rejected; SOW approval does not approve spec/v2                             | Baseline t_19c877cb                                                                                          |
| Approval concurrency / stale edits    | Separate connections race review/approval/successor allocation; one valid current result; immutable submitted content and explicit rejection                                               | Baseline, verification                                                                                       |
| Requirements/context/templates        | Stable keys survive archive, duplicate identity rejected; FR/NFR rationale/verification; owned Q/Spike/DEC relations; template copy has provenance/no propagation                          | Requirements t_913965f7                                                                                      |
| Hidden/foreign/inverse references     | Direct IDs, inverse x2many edits, caller companies, relation traversal/import cannot cross scope; archive history preserved without reauthorization loophole                               | Baseline, requirements, security                                                                             |
| Task links and no overwrite           | One NFR across Tasks and one Task across requirements; exact revisions; hidden/foreign/inactive Tasks rejected; no changes to authored descriptions/criteria/stages/estimates/Sprint/order | Traceability t_2bedc90a                                                                                      |
| Durable preview/confirm               | Preview no Task; duplicate independent-process confirm returns same authorized result; stale/forged payload rejects; injected failure rolls back Task/link/result atomically               | Traceability, verification                                                                                   |
| Frozen Sprint context                 | Start/add/close/carry-over and relink races retain actual v1 content/status; current v2 cannot rewrite historic event or analytics; old unknown != empty                                   | Traceability optional bridge, verification                                                                   |
| Audience and completeness             | Direct HTML/report/export/PDF/attachment paths enforce caller/audience; internal text/hidden metadata/counts absent; exact full closure refuses inaccessible reference; injection escaped  | Rendering t_a7974c61, security                                                                               |
| Coverage/change impact                | Changed/current/older/archived/unlinked/question/maintenance categories truthful; unavailable closure cannot claim completeness; no aggregate invented completion %                        | Rendering                                                                                                    |
| Explicit acceptance                   | Exact approved revision + named authority + nonempty criteria/evidence; unauthorized/foreign/unapproved denies; Done/merge does not accept; v2 distinct; withdrawal append-only            | Rendering, verification                                                                                      |
| Lifecycle and recovery                | Core isolated install, aggregate install/update/reverse uninstall/reinstall; existing M1-M7/browser/concurrency retained; normal sudo/context not recovery bypass                          | Every schema/security slice, verification                                                                    |
| Whole approved scope and effects      | Exact reviewed cumulative SHA/contract matrix, independent security; guarded local delivery not publication; exact human publication latch                                                 | Security t_4841a335, cumulative t_f0b10ab9, delivery t_002ae0a4, approval t_c009385c, publication t_bcedc3b0 |

Final verification card promotes the three scenarios end-to-end through imported real
Odoo helpers; security independently attacks them and cumulative checks every approved
scope row. Native browser flows/reports/independent-process concurrency are required at
the owning phase, not claimed by JSON validation or admin-only success. Odoo.sh/customer
validation remains separate. New ambiguity cannot be resolved by silently reducing
scope.
