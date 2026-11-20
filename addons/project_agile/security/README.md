# Security boundary

The module installs ACLs for `project.agile.item.type`, `project.agile.environment` and
`project.task.environment.status`. Project users can read item types; Project
administrators configure them and Project environments. Task environment statuses follow
current task access. Record rules on environments and status lines enforce native record
visibility and company access. These permissions do not widen native Project or Task
record visibility.
