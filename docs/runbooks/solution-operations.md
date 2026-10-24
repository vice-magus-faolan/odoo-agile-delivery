# Solution history, access and recovery

Use the [Solution guide](../../addons/project_agile_solution/README.rst) for setup,
document review and acceptance actions. Use the optional
[Scrum bridge guide](../../addons/project_agile_solution_scrum/README.rst) for Sprint
history. [ADR-013](../adrs/013-solution-definition-contract.md) defines the technical
contract.

## Protect access and customer copies

Never assign `project_agile_solution.group_snapshot_storage` to a user or imply it from
another group. Technical Features is enabled by browser debug mode; it is not a deny-all
permission boundary.

If a historical document refuses to open, check the reader's current Project, document,
requirement, referenced SOW and discovery Task access. Restore only the access the
reader should have. Do not bypass the refusal with privileged exports or remove access
rules during an upgrade.

Generate customer output as an authorized internal user and review the redacted copy
before sharing it. Do not distribute native report URLs as customer access. Keep secrets
out of narratives and evidence. Restrict distribution and retention of exported files,
because later permission changes cannot revoke copies already shared.

For portal clients, check the exact Project invitation, current company access, Client
Signer and explicit publication. Native commercial visibility alone does not grant
publication access. After correcting a revoked grant, issue a new publication from the
approved revision. Review internal approval, client document decision and Internal proxy
requirement history separately. Revoke an issued publication through its document when
it should no longer be available.

## Handle previews and corrections

Preview collections stop above 1,000 rows. Split the initiative instead of bypassing the
limit. Select a baseline comparison when you need a change report.

If a preview is stale, preview again before confirming Task creation. If contention
exhausts a request's retries, reload the current records before trying the action again.
Correct sealed content through a successor revision. Use rejection or withdrawal to
correct an acceptance decision. Have the approver of the exact specification baseline
record acceptance with criteria and evidence, following the Solution guide.

## Back up, restore and uninstall

Back up both the database and filestore before an upgrade or uninstall. Record the
matching source, addon, image and configuration versions. Test restoration in isolation
before proceeding. Archive used records when their traceability must remain available.

After restoration, check frozen content and references, Project and company access,
Sprint capture status and the Tasks already created from confirmed previews before
allowing new creation. Check import error messages and returned record IDs before
treating an import as successful. If an upgrade fails, restore matching source, database
and filestore together. Do not run old code against an unverified newer schema. Do not
regenerate Tasks or backfill old Sprint context from current links.

Uninstall deletes Solution traceability. Surviving native Tasks and Sprint history
cannot reconstruct it. Reinstalling the Scrum bridge leaves old events **Not Available /
Predates Bridge** rather than capturing history retrospectively. Restore a verified
consistent backup to recover lost history.
