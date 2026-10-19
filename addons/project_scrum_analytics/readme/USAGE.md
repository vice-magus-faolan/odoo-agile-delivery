1. Open **Project > Tasks > Scrum Analytics**. The initial **Active Sprints**
   filter shows live replay. Search by Sprint, Project or team, or group by
   Project, Team, Sprint Status or Sprint End Date.
2. Remove **Active Sprints** and select **Closed Sprints** to review completed
   Sprints. **Trusted Closed Replay** selects closed Sprints with a close
   timestamp. Their metrics stop at that boundary: later task edits do not
   rewrite the closed report. Draft or legacy reports without that boundary
   are not trusted closed replay.
3. Open a report to compare **Original Commitment (Story Points)**, completed
   commitment and final scope. Choose **Open Sprint** for the Sprint form or
   **Open Burndown & Burnup Timeline** for its event history.
4. In the timeline, open a point to see the scope event and values after it;
   **Open Task** drills down to the task when access permits. You can also open
   **Project > Tasks > Scrum Analytics > Burndown & Burnup Timeline** and filter
   by Sprint, Project, task or event type.
5. Switch to pivot or graph views and select the measures needed. Event
   timestamps are UTC; date-chart buckets use your Odoo timezone. Timeline
   values are snapshots after each event, not daily increments: summing them
   does not give a Sprint total. Use the Sprint report for totals.

As a Project administrator, start and close Sprints through their normal actions.
Actual native Done transitions record **Completed** events; a stage called Done
alone is insufficient. If a report seems empty, check filters, Sprint scope
history, Project visibility and available companies before comparing metrics.
