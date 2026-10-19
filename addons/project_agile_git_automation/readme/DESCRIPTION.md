Optional Odoo 19 Community-compatible Git workflow policies, depending only on
`project_agile_git`. The addon is LGPL-3 and uses native Odoo scheduled actions;
GitHub, Scrum, an external queue runner and outbound provider calls are not
required. A separately configured ingress adapter supplies authenticated facts.

Projects start disabled and in dry-run mode. Rules describe a merged pull
request on an exact branch, allowed source stages, one target stage and optional
named checks. Two different authorized people must author and approve a revision.
Dry runs record informational decisions and never move tasks. Separately enabled
Apply mode can move only the approved task stage under the approved execution
user; it cannot mark native completion, change Sprint scope or edit estimates.
