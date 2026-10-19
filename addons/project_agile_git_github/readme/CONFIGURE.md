First configure the repository using the
[Git Facts guide](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/main/addons/project_agile_git#configuration).
Repository configuration and delivery recovery require **Administrator** under
**Project** in the user access rights, called Project administrator below.
The person setting **Webhook Secret** must also have System Administrator access.
GitHub webhook setup requires permission to administer that repository webhook.

1. In **Project > Tasks > Git Repositories**, select the intended repository.
   Set **Provider** to **GitHub**, check **Project** and **Company**, and verify
   **Provider Repository Id** matches GitHub `repository.id`. Keep the
   repository active and set **Canonical Url** to its `https://github.com/`
   repository URL.
2. Select **Redacted Excerpt** in **Retention Policy** before sending events.
   **Digest Only** records receipt metadata but leaves no payload for scheduled
   normalization or later reprocessing. Changing the setting does not repair
   earlier receipts or an exact redelivery of the same delivery ID.
3. As a System Administrator with the Project access above, set **Webhook
   Secret** and save. In GitHub, configure the same secret, select
   `application/json`, and use your externally reachable HTTPS Odoo URL followed
   by `/project_agile_git_github/webhook`. Select `push`, `pull_request` and
   `check_run` events as required, with the necessary GitHub permissions.
4. Ensure native Odoo scheduled actions are running. **Normalize Agile GitHub
   Deliveries** is configured every minute, processing at most 20 deliveries per
   invocation. Actual latency depends on scheduler availability and backlog.
   **Purge Expired Agile GitHub Payload Excerpts** is configured daily.

Ingress requires `X-GitHub-Event`, `X-GitHub-Delivery` and an exact-body
`X-Hub-Signature-256` HMAC SHA-256 signature. Requests are limited to 256 KiB.
An accepted receipt returns HTTP 202; this confirms ledger receipt, not successful
normalization. An exact duplicate uses the same ledger row. A reused delivery ID
with different event type, body digest or size returns HTTP 409.

A retained redacted JSON excerpt must fit within 4,096 characters; an oversized
excerpt produces a **Failed** delivery with a diagnostic and no retained payload.
Redaction removes recognized credentials but may leave sensitive text or unknown
credential formats. Keep such content out of webhook fields and do not copy
payloads or secrets into chatter, tickets or routine exports. Secret and retained
payload access is restricted to System Administrators.
