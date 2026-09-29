# Agile GitHub Delivery Ingress

`project_agile_git_github` is the narrow GitHub adapter for `project_agile_git`.
It accepts only bounded `application/json` GitHub deliveries with an exact-body
`X-Hub-Signature-256` HMAC SHA-256, an event header, and a delivery ID. The
adapter derives repository scope only from the signed payload's GitHub repository
ID; it ignores payload project/company fields and performs no task, fact, chatter,
or workflow mutation in the request transaction.

A valid delivery creates at most one `project.git.delivery`, using the core
`(repository_id, provider_delivery_id)` database constraint for replay and
concurrent-delivery safety. It responds `202` for both a first receipt and an
already-recorded delivery. GitHub secrets remain system-administrator-only core
configuration and are neither returned nor stored in delivery data.

Raw payloads are never logged. Default core retention is digest-only. A repository
that explicitly selects `redacted_excerpt` retains a scrubbed, 4 KiB excerpt for
30 days; common credential-shaped keys are replaced before storage. Normalization,
retry processing, associations, and all workflow policy remain outside this addon.
