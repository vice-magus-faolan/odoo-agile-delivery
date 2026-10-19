First configure the repository using the
[Git Facts guide](https://github.com/vice-magus-faolan/odoo-agile-delivery/tree/main/addons/project_agile_git#configuration).
Repository configuration and delivery recovery require **Administrator** under
**Project** in the user access rights, called Project administrator below.
The person setting **Webhook Secret** must also have System Administrator access.
GitHub webhook setup requires permission to administer that repository webhook.

1. In **Project > Tasks > Git Repositories**, select the repository.
   Set **Provider** to **GitHub**, check **Project** and **Company**, and run
   `gh api repos/OWNER/REPO --jq .id`. Enter the returned number in
   **Provider Repository Id**. Keep the repository active and set
   **Canonical Url** to its `https://github.com/` repository URL.
2. Select **Redacted Excerpt** in **Retention Policy** before sending events.
   **Digest Only** saves delivery metadata but leaves no payload for scheduled
   processing or later reprocessing. Changing the setting does not repair
   earlier deliveries or an exact redelivery of the same delivery ID.
3. Set **Webhook Secret** and save. In GitHub, configure the same secret,
   select `application/json`, and use your externally reachable HTTPS Odoo URL
   followed by `/project_agile_git_github/webhook`. Choose **Let me select
   individual events**, then **Pushes**, **Pull requests** and **Check runs**.
4. Odoo.sh runs scheduled actions for you, on a best-effort schedule no more
   often than every five minutes. Self-hosted Odoo needs `max_cron_threads`
   above 0. **Normalize Agile GitHub Deliveries** is configured every minute,
   processing at most 20 deliveries per invocation.
   **Purge Expired Agile GitHub Payload Excerpts** is configured daily,
   removing at most 100 expired payloads per invocation.

Requests require `X-GitHub-Event`, `X-GitHub-Delivery` and an exact-body
`X-Hub-Signature-256` HMAC SHA-256 signature. Bodies larger than 256 KiB receive
HTTP 413 and create no delivery row. A 202 means Odoo saved the delivery. Check
its **State** to see whether it was processed. An exact duplicate uses the same
delivery. A reused delivery ID with different event type, body digest or size
returns HTTP 409.

Redacted Excerpt retains supported fields for facts and task links, not the full
GitHub body. Keys anywhere in complete commit messages and PR bodies can link
tasks; a commit display excerpt is shortened to 255 characters. Excessive keys
produce a rejected association decision. Malformed or oversized required fields
produce a **Failed** delivery with a diagnostic and no retained payload.

Pushes retain the first 100 commits. For larger pushes, **Omitted Commit Count**
and **Commit Omission Reason** identify skipped commits, even after successful
processing or payload cleanup; the branch head still updates subject to source
ordering. See [ADR-011](https://github.com/vice-magus-faolan/odoo-agile-delivery/blob/main/docs/adrs/011-git-facts-and-visibility-contract.md)
for technical retention bounds.

Redaction removes recognized credentials but may leave sensitive text or unknown
credential formats. Keep such content out of webhook fields and do not copy
payloads or secrets into chatter, tickets or routine exports. Secret and retained
payload access is restricted to System Administrators.
