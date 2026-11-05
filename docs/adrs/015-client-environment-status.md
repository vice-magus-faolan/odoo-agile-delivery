# ADR-015: Manual per-client environment status

Each Agile Project owns its ordered environments; no shared environment names or
production order are imposed. Configuration and Data import opt in through the shared
item type's Tracks Environments flag. The native task remains the work item. There is no
import-run, deployment or Git state in this feature.

A native status model has a unique task/environment pair. Both links are immutable and
must refer to the same Project and company. Ordinary Task writers may update status
without Project configuration authority. Environment configuration requires a Project
administrator and native Project write access. Global rules use explicit caller-bound
ORM subqueries, following the existing solution-access pattern, because Odoo compiles
record rules under sudo. They preserve native Task/Project rules and company
restrictions; mutations also check the current caller's Task authority.

Status writes assign protected actor/time fields from the current server environment;
unrelated chatter writes must not change who set a status. They cannot be supplied
through status input or context defaults. Native mail tracking retains transitions; the
environment history action exposes inactive lines and each line's chatter. Archiving an
environment, disabling tracking or converting work to a template hides applicability
without deleting recorded statuses. Reactivation reuses the pair. Production may be
marked done before UAT. Verified counts as done in gap searches; all predicates pair
environment and status on the same line using `any`, rather than combining independent
relational conditions.

Task create, eligibility changes, template restoration and Project activation
synchronize missing lines. Adding/reactivating an environment or enabling a shared type
reaches open active work. Search as superuser to include tasks the caller cannot see,
then check write access as the caller before creating their lines. If two transactions
try to create the same Task/environment pair, the unique constraint rejects the
duplicate and the affected administrator saves again.

Typed names match the environments the caller can see. The native search view uses
`=ilike` for typed names, matching the whole name ignoring case: Production does not
include Pre-Production. Selecting a suggestion uses its exact environment ID instead.
The view's `filter_domain` distinguishes the typed string from a selected numeric ID; an
`operator` attribute alone would also apply the text operator to selected IDs. Explicit
advanced ORM `like` and `ilike` searches keep their native pattern semantics. Not like
and not ilike flip done and not done for the matching environments.

Only tracking tasks whose Project has a matching active environment count as not done.
An existing applicable To do line remains pending, even on Done or Canceled work. A
missing line counts as pending only on active tasks outside those two closed states, the
same work reached by open-task backfill. Closed tasks with missing lines are excluded;
reopening synchronizes their missing lines without changing recorded history. Waiting
for Production applies this same pending rule and requires completion somewhere
applicable and no completion in any active environment flagged Production in the same
Project. A Project with no active flagged environment is excluded.

Project duplication and native creation from a Project template copy environment starter
names, ordering, Active and Production flags, including archived starters, into fresh
destination-owned rows. Explicit copy defaults override these settings; opting out of
Agile omits the starter list unless explicitly supplied. Task status lines and chatter
history are never copied: eligible destination tasks start with fresh To do lines for
active destination environments only. Source settings and history remain unchanged. The
versioned migration initializes tracking on the existing noupdate Configuration/Data
import seeds once. Later user choices survive updates. No environment list is inferred
for an existing client.

The implementation extends native create/write/template state at the pinned
[Odoo 19 Community revision](https://github.com/odoo/odoo/tree/8da213dc6785e097f2558dc2d648b588957786a1),
without overriding native copy workflows or introducing a custom frontend.
