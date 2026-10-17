"""Shared native record claims for Agile domain transitions."""

from odoo.exceptions import ConcurrencyError


def claim_records(records, *, allow_referencing=False):
    """Claim every row or restart the transaction through native request retry."""
    if records.try_lock_for_update(allow_referencing=allow_referencing) != records:
        raise ConcurrencyError("Records are being changed concurrently.")
