"""Bounded, auditable retention cleanup for authenticated GitHub deliveries."""

from odoo import api, fields, models
from odoo.tools import SQL


RETENTION_CLEANUP_BATCH_SIZE = 100
_PURGEABLE_STATES = ("processed", "discarded")


class ProjectGitDelivery(models.Model):
    """Purge only expired terminal payload excerpts while preserving delivery evidence."""

    _inherit = "project.git.delivery"

    retained_payload_purged_at = fields.Datetime(readonly=True, copy=False, index=True)

    @api.model
    def _expired_github_payload_domain(self, now):
        """Return payloads eligible for safe retention cleanup at ``now``."""

        return [
            ("provider", "=", "github"),
            ("state", "in", _PURGEABLE_STATES),
            ("retained_payload", "!=", False),
            ("retained_until", "!=", False),
            ("retained_until", "<=", now),
        ]

    @api.model
    def _purge_expired_github_payloads(self, now=None):
        """Purge a bounded batch with a state recheck at the write boundary."""

        now = now or fields.Datetime.now()
        deliveries = self.sudo().search(
            self._expired_github_payload_domain(now),
            order="retained_until, id",
            limit=RETENTION_CLEANUP_BATCH_SIZE,
        )
        purged = 0
        for delivery in deliveries:
            self.env.cr.execute(
                SQL(
                    """
                    UPDATE project_git_delivery
                       SET retained_payload = NULL,
                           retained_until = NULL,
                           retained_payload_purged_at = %s
                     WHERE id = %s
                       AND provider = 'github'
                       AND state IN ('processed', 'discarded')
                       AND retained_payload IS NOT NULL
                       AND retained_until <= %s
                    """,
                    now,
                    delivery.id,
                    now,
                )
            )
            if self.env.cr.rowcount:
                delivery.invalidate_recordset(
                    ["retained_payload", "retained_until", "retained_payload_purged_at"]
                )
                purged += 1
        return purged

    @api.model
    def _cron_purge_expired_github_payloads(self):
        """Commit one bounded cleanup batch through Odoo's scheduled-action contract."""

        now = fields.Datetime.now()
        domain = self._expired_github_payload_domain(now)
        remaining = self.sudo().search_count(domain)
        purged = self._purge_expired_github_payloads(now)
        self.env["ir.cron"]._commit_progress(
            remaining=max(remaining - purged, 0), processed=purged
        )
        return purged
