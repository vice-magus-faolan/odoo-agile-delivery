"""Fail closed on unreviewed Task inheritance and runtime write monkeypatches.

These exact file fingerprints are a compatibility gate, not a signature against
trusted server/DB administrators. Updating Odoo or installing another Task addon
requires source review and explicit profile/tests, never a context override.
"""
import hashlib
import inspect
from pathlib import Path

SOURCES = {
    "orm/models.py": "68b2f57f19dbff2d0a54fc0e0ac14446233cf5b254499fe2004c642cd6e09d6d",
    "addons/project/models/project_task.py": "95f4f20c26bcf97f3c147b141b7411c5c0c9c31aec578e68a24f9869996aecb4",
    "addons/project_sms/models/project_task.py": "7fb21f9882dc45c110b303f612818ad6db88115a4e2fabdb6d661c59ed1d54b2",
    "addons/mail/models/mail_thread.py": "d884afc1028baaf1423c4b7643a9854b13fa45bad8909ea8f7b84855c4f36a95",
    "addons/project_agile/models/project_task.py": "962767eb1563943f2c4a8e6c7f47c832a69a68a51a10e90b3e61a4a773d15706",
    "addons/project_scrum/models/project_task.py": "976e8c7a62119db686b258267cf4665e86ff4f58e5028809bcb3de27f0447162",
    "addons/project_agile_git_automation/models/project_task.py": "919c7b5fda920fb103cdba24e787225a1ce95497d6a32dab638852be25d2f961",
    # Optional M8 guard rejects inverse discovery edits; stage writes delegate
    # unchanged through super. Keep this exact source pin, never a wildcard.
    "addons/project_agile_solution/models/solution_revision_content.py": "2de129972395f82f562924675b4a5ca4fc19cdce38fc2b4ad089d019b92f1867",
    "addons/project_agile_git/models/project_git_visibility.py": "a7b25bd6aed5966f018334da300a2e8ca3086a47fa948bc65bb692cbe181b168",
    "addons/project_todo/models/project_task.py": "a6922427c429e07cfbc459d80edba5be03373281fa991fee5466f8210e08099b",
    "addons/portal/models/portal_mixin.py": "09bb21f1fdf2682ab558e3c0fce4f979a33e33ad85b0147f3f98c4c6a48fb582",
    "addons/mail/models/mail_thread_cc.py": "f2e3780e79f485cb693d376d1c22996420192d51fa52bb367af491a2acedc1cc",
    "addons/mail/models/mail_activity_mixin.py": "48c8c12f2468db135b5180a50a8ffd31c5128b4a8de8ad150facddf9ef13c349",
    "addons/rating/models/rating_mixin.py": "25e0fd486b096e04b868cfc72bfb811c9da3113c139feb66d0599f890466f6f8",
    "addons/mail/models/mail_tracking_duration_mixin.py": "109f3f3be470ff31b1068d8fb40e3fd1831143fbc5ccf63e257b9433e980ba9f",
    "addons/snailmail/models/mail_thread.py": "aa81fe06578e3b821d07892f34f90319394e3466131fca49c7422fd73ce5affa",
    "addons/sms/models/mail_thread.py": "a57cdd8aa198049cc94d1f5286c0f210b06cd60d0e864f1156aeda3380d80215",
    "addons/portal/models/mail_thread.py": "de2ac54e867f8575b38d551b5baced668bc646e7ced1ad20b30b86135d324dc0",
    "addons/rating/models/mail_thread.py": "34a51ed02d4c6ce0c57928a08689ba91bc369724a86e50beaa918d537e65ad9b",
    "addons/html_editor/models/html_field_history_mixin.py": "214527207183325b53f6204176215d640ba87fdac92af20ad36a1aa898b595ca",
    "addons/sms/models/models.py": "465a00f4112366759b88f3644fbeef997a34971452d6f87f3ec070142db1f9c4",
    "addons/phone_validation/models/models.py": "dbea3eeb3a9f3a254c16280252a15b8da2bb2b6eb5eb913a2dbd3c53bfb230e9",
    "addons/mail/models/models.py": "e49d05a0bd8965dd05bbfb9ca308cb422e87075915d6a7cc61d27b5d0c624f0d",
    "addons/html_editor/models/models.py": "02a3fd2a4376a5b29e47925629d3dabe3a59207707ed66adfc5bfabfac69ce7e",
    "addons/base_import/models/base_import.py": "71127aadeb41f94e7856386e5db0525bda620a2236b961b0b516bd944b6c7ecf",
    "addons/web/models/models.py": "4ff14886e7ff8bbb41ecaa80560f000bd85cc1a39d191146df8bf0ca576be9a2",
    "addons/base/models/ir_ui_view.py": "bf67ea6ea7b748edf451d6bf81d661049ab97de74e8d9e97b072ed9ceaaeb5fd",
    "addons/base/models/ir_model.py": "db531d199c77be7feacda1fc3b712ab82224e17ab4fd02c6ac679c36a505e61d",
}


def _supported_file(value):
    try:
        filename = inspect.getsourcefile(value)
        if not filename:
            return False
        path = Path(filename)
        matches = [digest for name, digest in SOURCES.items() if path.as_posix().endswith('/' + name)]
        # Custom addons use /mnt/extra-addons/<module>, not Odoo's addons root.
        if not matches:
            matches = [digest for name, digest in SOURCES.items() if name.startswith('addons/')
                       and path.as_posix().endswith('/' + name.removeprefix('addons/'))]
        return len(matches) == 1 and hashlib.sha256(path.read_bytes()).hexdigest() == matches[0]
    except (OSError, TypeError):
        return False


def check_write_profile(task):
    """Installed native/custom Task extension classes and write functions are finite."""
    for cls in type(task).__mro__:
        if cls.__module__ == "builtins":
            continue
        if not _supported_file(cls):
            return False
        for name in ("write", "_write", "_compute_state"):
            method = cls.__dict__.get(name)
            if method is not None and not _supported_file(method):
                return False
    return True
