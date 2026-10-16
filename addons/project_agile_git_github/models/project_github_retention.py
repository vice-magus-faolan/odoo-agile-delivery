"""Bounded, auditable retention cleanup for authenticated GitHub deliveries."""

from odoo import api, fields, models

RETENTION_CLEANUP_BATCH_SIZE = 100
_PURGEABLE_STATES = ("processed", "discarded")


# Retention remains separate from authenticated ingress and normalization.
class ProjectGitDelivery(models.Model):
    """Purge only expired terminal payload excerpts while preserving delivery
    evidence.
    """

    # pylint: disable-next=consider-merging-classes-inherited
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
        domain = self._expired_github_payload_domain(now)
        # Only this private maintenance boundary purges across companies.
        deliveries = self.sudo().search(
            domain,
            order="retained_until, id",
            limit=RETENTION_CLEANUP_BATCH_SIZE,
        )
        purged = 0
        for delivery in deliveries:
            # Recheck even a stale candidate before writing. A concurrent state
            # change conflicts with the ORM update under repeatable read, leaving
            # the scheduled action to retry with a fresh transaction.
            if delivery.filtered_domain(domain):
                delivery.write(
                    {
                        "retained_payload": False,
                        "retained_until": False,
                        "retained_payload_purged_at": now,
                    }
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
