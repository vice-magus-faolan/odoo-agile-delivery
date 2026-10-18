1. As a Project administrator (`project.group_project_manager`), open the intended
   Project form and its **Settings** tab. In **Agile**, enable **Agile Enabled**.
2. Set **Agile Key** to a globally unique prefix such as `ENG`. It must start with
   an uppercase letter and contain only uppercase letters and digits. Save the
   Project before creating its work items.
3. Choose **Default Agile Item Type**, for example Story, and **Estimation Method**.
   **None** accepts only zero story points. **Fibonacci** accepts
   `0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89`.
4. Under Project **Configuration > Agile Item Types**, review the seeded Epic,
   Feature, Story, Bug, Task, Spike and Subtask types. Open a type to configure
   **Allowed Child Item Types**. For example, Story initially allows Task and
   Subtask children. These are shared type definitions, not per-Project settings;
   changing a policy must remain compatible with existing task hierarchies.

Project users can read item types; Project administrators can manage them.
Ordinary task operations still use native Project permissions. Grant only the
Project and company access each user needs.

Choose the key before creating work: new tasks created in an enabled Project get
sequence-generated keys such as `ENG-1` and the active default item type when no
type is supplied. Enabling Agile does not backfill keys or item types on existing
tasks. An assigned task key cannot change, and a keyed task cannot move to another
Project; copy it into the target Project instead. The Project prefix cannot change
after task keys have been assigned. Seeded item types preserve administrator
customizations on module updates.
