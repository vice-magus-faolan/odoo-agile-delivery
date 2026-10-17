# M8 Task traceability and optional Scrum capture

Odoo 19 Community, tested image 19.0-20260908; exact upstream revision
8da213dc6785e097f2558dc2d648b588957786a1. Native create/defaults, current check_access,
Domain subqueries, repeatable-read and existing in-repository Scrum event producers were
inspected. This is Odoo-compatible, not an OCA conformity claim. Core remains
LGPL-3/project_agile-only. The LGPL-3 optional project_agile_solution_scrum bridge
depends only on project_agile_solution and project_scrum (existing compatible LGPL-3
Community dependencies).

A durable edge names Task + exact requirement revision + optional exact spec. Creation
seals actual requirement content. One NFR may span many Tasks and one Task many
requirements. Explicit retirement retains the old edge/reason/actor; reactivation is
intentionally not offered. Link edits publish a private reference on the Task without
changing its business fields. Existing task selection and every confirmation resolve
current caller Project, company, Task, requirement and exact specification access.
Context is never permission. Search/read/group/export use current-reference closure, not
today's privileged metadata. Archive preserves history; new links reject archives and
templates. Maintenance reason is explanatory text, not inferred acceptance.

Preview is a durable creator-owned intent, not a Task. It records a bounded finite
proposal and exact source fingerprint; confirmation is a separate native wizard/action.
Source freshness is revalidated after locks. Changed draft content, new requirement
revision or changed document head invalidates pending preview. Consumption returns the
same authorized Task on retries, even after requirements have successors; archive cannot
renew creation eligibility. Finite Task create values run with default\_\* context
stripped, normal caller ORM, no privileged creation. Native Task defaults and normal
creation effects remain native; this addon never supplies stages, estimates, criteria,
parent/dependencies, ordering, Sprint allocation, or history. Confirmation and all
links/seals/consumption share one savepoint, including direct Python callers. The
transient confirmation must resolve a literal creator-owned currently visible intent
before creation. Its related projections run without sudo; a current-intent rule closes
search/name lookup/counts, and read/export re-query reference closure after rule
changes. Confirmation selection and projected fields cannot be rewritten by RPC.

Concurrency: a nonblocking native ORM claim orders confirmations on their durable
intent; contention asks Odoo to retry the complete transaction. Consumption itself
writes the intent, making old snapshots fail rather than create duplicate work. Link
creation/retirement publishes the actual edge on the Task; discovery references publish
their actual question revision. Task scope/deletion guards and Sprint capture claim that
same Task before reading links. Capture needs no Solution-wide write: requirement
content is already sealed. Revision allocation publishes on its stable identity, so
pending confirmations cannot miss a concurrent new head. Exact specification claims also
protect a preview from concurrent specification edits and approval. See the
[concurrency runbook](../runbooks/solution-document-baselines.md#concurrency-and-atomicity)
for whole-transaction retry and exhaustion behavior. Task unlink claims also exclude
concurrent foreign-key references to the Task being deleted.

Bridge captures all exact active links at every native event, including empty coverage.
Existing producer delegates via super; native event return is extended to return its
created recordset without changing values/lifecycle/analytics. Scope markers distinguish
captured/empty/not_available; old events remain not_available and are never backfilled.
Edges snapshot sealed requirement content and document state/number at capture. Current
restrictions protect old history; changing/retiring links, archiving identities or
approving new documents cannot rewrite old events. Scrum commitment is not specification
or requirement approval. During a dependency-ordered upgrade, the already-stored event
rule denies all ordinary event reads until the optional extension's search field is
registered; it never falls back to privileged or incomplete-looking history. Once the
full registry is loaded, the same current Task/Sprint/exact-reference closure applies.
This preserves optional module layering and is exercised by the canonical native Scrum
upgrade regression, without skipping tests or adding a core dependency.

No external contact, push/publication, deployment, shared service restart,
provider/configuration changes, generic model/method dispatch, autonomous planning or
legal/customer/production validation occurs. Dedicated M8 rendering/browser, acceptance
evidence and final security/cumulative gates remain downstream.
