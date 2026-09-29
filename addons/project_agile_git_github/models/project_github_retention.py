"""Bounded, auditable retention cleanup for authenticated GitHub deliveries."""

from odoo import api, fields, models


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
        """Purge one bounded batch atomically, preserving every delivery and fact record."""

        now = now or fields.Datetime.now()
        deliveries = self.sudo().search(
            self._expired_github_payload_domain(now),
            order="retained_until, id",
            limit=RETENTION_CLEANUP_BATCH_SIZE,
        )
        for delivery in deliveries:
            cleanup_delivery = delivery.sudo()
            if delivery.company_id:
                cleanup_delivery = cleanup_delivery.with_company(delivery.company_id)
            cleanup_delivery.write(
                {
                    "retained_payload": False,
                    "retained_until": False,
                    "retained_payload_purged_at": now,
                }
            )
        return len(deliveries)

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
