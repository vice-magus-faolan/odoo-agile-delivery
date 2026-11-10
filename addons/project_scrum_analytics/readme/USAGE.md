The **Project > Tasks > Scrum Analytics** parent menu currently does not open its
report action; this navigation defect is tracked in
[#53](https://github.com/vice-magus-faolan/odoo-agile-delivery/issues/53).
The **Burndown & Burnup Timeline** submenu is reachable. The steps below describe
the Sprint report when opened, rather than a working parent-menu launch path.

1. The initial **Active Sprints** filter shows numbers from the Sprint history
   so far. Search by Sprint, Project or team, or group by Project, Team,
   Sprint Status or Sprint End Date.
2. Remove **Active Sprints** and select **Closed Sprints** to review completed
   Sprints. The current **Trusted Closed Replay** filter selects closed Sprints
   with a recorded close time. Their metrics stop there; later task edits do
   not rewrite them. Do not use a draft report or an older closed Sprint without
   a close time as a final historical total.
3. Open a report to compare **Original Commitment (Story Points)**, completed
   commitment and final scope. Choose **Open Sprint** for the Sprint form or
   **Open Burndown & Burnup Timeline** for its event history.
4. In the timeline, open a point to see the scope event and values after it;
   **Open Task** opens the task when access permits. You can also open
   **Project > Tasks > Scrum Analytics > Burndown & Burnup Timeline** and filter
   by Sprint, Project, task or event type.
5. Switch to pivot or graph views and select the measures needed. Event
   timestamps are UTC; date-chart buckets use your Odoo timezone. Timeline
   values are snapshots after each event, not daily increments: summing them
   does not give a Sprint total. Use the Sprint report for totals.

As a Project administrator, start and close Sprints through their normal actions.
Follow the [Scrum completion instructions](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/19.0/addons/project_scrum#start-and-work)
when recording completed work. If a report seems empty, check filters, Sprint
scope history, Project visibility and available companies before comparing metrics.
