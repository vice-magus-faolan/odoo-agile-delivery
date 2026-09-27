# Agile Project Document Page

`project_agile_document_page` is an optional AGPL-3 bridge for an Agile Project's one designated OCA Document Page root. It depends on `project_agile` and OCA `document_page_project`; it does not duplicate OCA page content, editor, history, hierarchy, ACLs, or Project Wiki relation.

Users explicitly create or link an active content page already assigned to the same Project, open it through native Document Page navigation, or clear the designation. Clearing only removes this bridge relation; it never deletes or reparents the OCA page. The bridge is unavailable to ordinary Projects and validates caller access, page state, native Project relation, and company alignment server-side.

The AGPL-3 dependency is a release gate for any public or production deployment: maintainers must review the combined deployment's corresponding-source obligations before release.
