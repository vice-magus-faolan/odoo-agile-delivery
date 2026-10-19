Optional Odoo 19 Community bridge linking Sprints to retrospective pages in
OCA Document Page. It depends on `project_scrum` and `document_page_project`;
the latter requires `document_page` and `document_knowledge`. The bridge and
these OCA modules declare AGPL-3 licenses. Base Scrum remains usable without
them.

Retrospectives use native OCA content, editing and page history. The addon seeds
category templates for ADRs, Sprint retrospectives, runbooks and release notes.
It does not provide a Task-page connector or an Enterprise Knowledge backend.
