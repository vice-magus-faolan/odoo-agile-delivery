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
3. Choose **Default Agile Item Type** and **Estimation Method**. **None** accepts
   only zero story points; **Fibonacci** accepts
   `0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89`.
4. Open Project **Configuration > Agile Item Types** to review Epic, Feature,
   Story, Bug, Task, Spike and Subtask. Configure **Allowed Child Item Types**;
   Story initially allows Task and Subtask. Types are shared across Projects.
   Odoo rejects a policy change that breaks an existing parent/child pair.

Project users can read item types; Project administrators can manage them.
New tasks in an enabled Project receive keys such as `ENG-1` and the default item
type when none is supplied. Enabling Agile does not backfill existing tasks.
An assigned task key and its Project cannot change; copy the task to move work to
another Project. The Project prefix cannot change after keys have been assigned.
Seeded item types preserve administrator customizations on module updates.
