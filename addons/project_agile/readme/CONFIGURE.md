As a Settings administrator, open **Settings > Users & Companies > Users**
and select an existing internal user. On **Access Rights**, in **Services**,
select **Agile member** in **Project** for ordinary typed work and estimates.
It includes the native Project User role, not Administrator.

With the optional addons installed, select **Business analyst** in **Agile
Solution** for authoring, and **Scrum master** in **Agile Scrum** for team and
Sprint management. These are separate controls alongside **Project**; select
both for one person who performs both jobs. Both imply Agile member without
granting Administrator. Save the user. Keep **Administrator** in **Project**
only for users authorized to configure and approve; adding Agile roles does
not remove that existing access.

For the following setup, assign **Administrator** under **Project**. Agile
configuration and shared item types remain Project administrator operations.
Native Project visibility, task permissions and company access still apply.

1. As a Project administrator, open the Project form and its **Settings** tab.
   In **Agile**, enable **Agile Enabled**.
2. Set **Agile Key** to a unique prefix such as `ENG`, starting with an uppercase
   letter and containing only uppercase letters and digits. Save the Project.
3. Choose **Default Agile Item Type** and **Estimation Method**. Enabling Agile
   defaults a missing choice to active Task; an administrator can choose another type or none.
   For point-using types, **None** accepts only zero story points; **Fibonacci** accepts
   `0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89`.
4. Open Project **Configuration > Agile Item Types** to review Epic, Feature,
   Story, Bug, Task, Spike, Subtask, Configuration and Data import. Configure
   **Allowed Child Item Types**;
   Story initially allows Task and Subtask. Types are shared across Projects.
   Odoo rejects a policy change that breaks an existing parent/child pair.
5. Set **Uses Story Points** per item type. Configuration and Data import start
   unchecked and are Sprint-eligible when Scrum is installed. The Project estimation
   method applies only to point-using types.
6. Enable developer mode to open Project **Configuration > Task Stages**.
   Set optional **Agile Item Types**.
   Empty means unrestricted. Stage restrictions do not affect ordinary non-Agile
   or explicitly untyped tasks. Move existing incompatible work before restricting
   a stage; Odoo refuses invalidating active or archived work.

Project users can read item types; Project administrators can manage them.
For each client's Agile Project, open **Settings > Agile > Environments**.
Add named rows in the required order, for example E2E, UAT, Pre-Production and Production for one
client and Staging and Production for another. Drag the sequence handle to reorder
them and check **Production** on the production environment. Lists start empty;
new and copied Projects need their own client configuration.

In **Configuration > Agile Item Types**, enable **Tracks Environments** on types
that need per-environment work. Configuration and Data import start enabled.
Adding or reactivating an environment adds To do lines to open active tasks of
tracking types. The operation is refused if you cannot update every affected task.
Done and Canceled tasks keep their existing lines; missing lines are added when
the task is reopened. Missing lines on closed tasks do not count as pending in
**Not done in environment** or **Waiting for Production**.
Uncheck **Active** on an environment to hide its status lines while retaining
history. Reactivating it restores the recorded statuses rather than resetting them.

New tasks in an enabled Project receive keys such as `ENG-1` and the default item
type when omitted. Explicit choices, including none, are preserved. An archived
default is not assigned to new work. Enabling Agile does not backfill existing tasks.
An assigned task key and its Project cannot change; copy the task to move work to
another Project. The Project prefix cannot change after keys have been assigned.
Seeded item types preserve administrator customizations on module updates.

Open an item type form under **Configuration > Agile Item Types** to edit or clear
**New Description Template**. Story starts with As a / I want / so that; Task
starts empty. These starting descriptions apply only to newly created Agile
work. Explicit descriptions, existing work and later module updates preserve
your choices, including a cleared template.
