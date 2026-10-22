from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain

_FIBONACCI_STORY_POINTS = {0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89}


class ProjectTask(models.Model):
    _inherit = "project.task"
    _rec_names_search = ["agile_key", "name"]

    agile_is_product_backlog = fields.Boolean(
        compute="_compute_agile_is_product_backlog",
        search="_search_agile_is_product_backlog",
        string="Product Backlog",
    )

    @api.model
    def _product_backlog_domain(self):
        return [
            ("project_id.agile_enabled", "=", True),
            ("project_id.active", "=", True),
            ("active", "=", True),
            ("state", "not in", ["1_done", "1_canceled"]),
            ("has_template_ancestor", "=", False),
            ("has_project_template", "=", False),
        ]

    @api.depends(
        "project_id.agile_enabled",
        "project_id.active",
        "active",
        "state",
        "has_template_ancestor",
        "has_project_template",
    )
    def _compute_agile_is_product_backlog(self):
        backlog = self.filtered_domain(self._product_backlog_domain())
        for task in self:
            task.agile_is_product_backlog = task in backlog

    @api.model
    def _search_agile_is_product_backlog(self, operator, value):
        if operator not in {"in", "not in"}:
            return NotImplemented
        domain = Domain(self._product_backlog_domain())
        matches = Domain.OR(domain if flag else ~domain for flag in value)
        return matches if operator == "in" else ~matches

    agile_project_enabled = fields.Boolean(
        related="project_id.agile_enabled",
        string="Agile Project Enabled",
        readonly=True,
    )
    # Preserve explicit source labels/translation keys, not an implicit fallback.
    # pylint: disable-next=attribute-string-redundant
    agile_item_type_id = fields.Many2one(
        "project.agile.item.type", string="Agile Item Type", ondelete="restrict"
    )
    # pylint: disable-next=attribute-string-redundant
    agile_key = fields.Char(string="Agile Key", copy=False, readonly=True, index=True)
    agile_story_points = fields.Float(string="Story Points")
    agile_effective_story_points = fields.Float(
        compute="_compute_agile_effective_story_points",
        store=True,
        help=(
            "Story points used for planning. Retained estimates on hour-based "
            "work contribute zero."
        ),
    )
    agile_uses_story_points = fields.Boolean(
        related="agile_item_type_id.uses_story_points",
        string="Uses Story Points",
        store=True,
    )
    agile_acceptance_criteria = fields.Html(string="Acceptance Criteria")
    # Preserve the existing explicit field label.
    # pylint: disable-next=attribute-string-redundant
    agile_backlog_sequence = fields.Integer(
        string="Agile Backlog Sequence", default=10, index=True
    )
    agile_tracks_environments = fields.Boolean(
        compute="_compute_agile_tracks_environments",
        store=True,
    )
    agile_environment_status_ids = fields.One2many(
        "project.task.environment.status",
        "task_id",
        copy=False,
        string="Environment Statuses",
    )
    agile_done_environment_id = fields.Many2one(
        "project.agile.environment",
        compute="_compute_environment_search",
        search="_search_done_environments",
        string="Done in environment",
    )
    agile_pending_environment_id = fields.Many2one(
        "project.agile.environment",
        compute="_compute_environment_search",
        search="_search_pending_environments",
        string="Not done in environment",
    )
    agile_waiting_for_production = fields.Boolean(
        compute="_compute_environment_search",
        search="_search_waiting_for_production",
        string="Waiting for Production",
    )

    _agile_task_key_unique = models.Constraint(
        "UNIQUE(agile_key)",
        "The Agile task key must be unique.",
    )

    @api.depends("name", "agile_key")
    # Compute methods assign fields, not return values.
    # pylint: disable-next=missing-return
    def _compute_display_name(self):
        super()._compute_display_name()
        for task in self.filtered("agile_key"):
            task.display_name = f"[{task.agile_key}] {task.display_name}"

    @api.model
    @api.readonly
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        if not name or operator not in ("=", "like", "ilike", "=like", "=ilike"):
            return super().name_search(name, domain, operator, limit)
        scope = Domain(domain or Domain.TRUE)
        key = name.upper() if operator in ("ilike", "=ilike") else name
        exact = super().name_search(
            name, scope & Domain("agile_key", "=", key), operator, limit
        )
        if not exact:
            return super().name_search(name, domain, operator, limit)
        if limit and len(exact) >= limit:
            return exact
        remaining = scope & Domain("id", "not in", [task_id for task_id, _ in exact])
        return exact + super().name_search(
            name, remaining, operator, limit - len(exact) if limit else limit
        )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        project_id = values.get(
            "project_id", self.env.context.get("default_project_id")
        )
        if not project_id:
            return values
        project = self.env["project.project"].browse(project_id)
        if not project.agile_enabled:
            return values
        item_type_id = self.env.context.get("default_agile_item_type_id")
        if "default_agile_item_type_id" not in self.env.context:
            default_type = project.agile_default_item_type_id
            item_type_id = default_type.id if default_type.active else False
            if "agile_item_type_id" in fields_list:
                values["agile_item_type_id"] = item_type_id
        if (
            item_type_id
            and "stage_id" in fields_list
            and "default_stage_id" not in self.env.context
        ):
            task = self.new(
                {"project_id": project.id, "agile_item_type_id": item_type_id}
            )
            values["stage_id"] = task._first_agile_stage().id
        return values

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            self._check_environment_derived_input(values)
        values_list = [dict(values) for values in vals_list]
        defaults = self.default_get(["project_id", "agile_item_type_id"])
        for values in values_list:
            if defaults.get("project_id"):
                values.setdefault("project_id", defaults["project_id"])
        project_ids = [
            values.get("project_id")
            for values in values_list
            if values.get("project_id")
        ]
        projects_by_id = {
            project.id: project
            for project in self.env["project.project"].browse(project_ids)
        }
        for values in values_list:
            project = projects_by_id.get(values.get("project_id"))
            values["agile_key"] = False
            if project and project.agile_enabled:
                self._prepare_agile_task_values(project, values)
        tasks = super().create(values_list)
        tasks._assign_agile_keys()
        tasks._sync_environment_statuses()
        return tasks

    @api.model
    def _prepare_agile_task_values(self, project, values):
        if "agile_item_type_id" not in values:
            default_type = project.agile_default_item_type_id
            values["agile_item_type_id"] = self.env.context.get(
                "default_agile_item_type_id",
                default_type.id if default_type.active else False,
            )
        if (
            values["agile_item_type_id"]
            and "stage_id" not in values
            and "default_stage_id" not in self.env.context
        ):
            task = self.new(
                {
                    "project_id": project.id,
                    "agile_item_type_id": values["agile_item_type_id"],
                }
            )
            values["stage_id"] = task._first_agile_stage().id

    def _assign_agile_keys(self):
        tasks = self.filtered(
            lambda task: task.project_id.agile_enabled
            and not task.project_id.is_template
            and not task.has_template_ancestor
            and not task.agile_key
        )
        tasks.check_access("write")
        tasks.project_id.check_access("read")
        for task in tasks:
            # Write the key below our own write, which refuses key changes.
            super(ProjectTask, task).write(
                {"agile_key": task.project_id._next_agile_task_key()}
            )
        return tasks

    def write(self, values):
        self._check_environment_derived_input(values)
        if "agile_key" in values:
            for task in self:
                if values["agile_key"] != task.agile_key:
                    raise ValidationError(_("An assigned Agile key is immutable."))
        if "project_id" in values:
            for task in self:
                if task.agile_key and values["project_id"] != task.project_id.id:
                    raise ValidationError(
                        _(
                            "A keyed Agile task cannot move to another project. "
                            "Copy it into the target project instead."
                        )
                    )
        moving = self.browse()
        project = self.env["project.project"]
        if values.get("project_id"):
            project = self.env["project.project"].browse(values["project_id"])
            project.check_access("read")
            if project.agile_enabled and not project.is_template:
                moving = self.filtered(
                    lambda task: task.project_id != project
                    and not task.agile_key
                    and not task.has_template_ancestor
                )
        if moving:
            defaults = dict(values)
            self._prepare_agile_task_values(project, defaults)
            groups = moving.grouped(
                lambda task: values.get(
                    "agile_item_type_id",
                    task.agile_item_type_id.id or defaults["agile_item_type_id"],
                )
            )
            for item_type_id, tasks in groups.items():
                prepared = dict(values, agile_item_type_id=item_type_id)
                self._prepare_agile_task_values(project, prepared)
                super(ProjectTask, tasks).write(prepared)
        result = super(ProjectTask, self - moving).write(values)
        restoring_from_template = values.get("is_template", True) is False
        if moving or restoring_from_template:
            # Native parent changes recompute descendant eligibility without write().
            affected = moving | self if restoring_from_template else moving
            affected = affected.with_context(active_test=False)
            (affected | affected._get_all_subtasks())._assign_agile_keys()
        if {
            "project_id",
            "agile_item_type_id",
            "active",
            "state",
            "is_template",
            "parent_id",
        } & values.keys():
            affected = self.with_context(active_test=False)
            (affected | affected._get_all_subtasks())._sync_environment_statuses()
        return result

    @api.depends(
        "project_id.agile_enabled",
        "project_id.is_template",
        "has_template_ancestor",
        "agile_item_type_id.tracks_environments",
    )
    def _compute_agile_tracks_environments(self):
        for task in self:
            task.agile_tracks_environments = bool(
                task.project_id.agile_enabled
                and not task.project_id.is_template
                and not task.has_template_ancestor
                and task.agile_item_type_id.tracks_environments
            )

    def _compute_environment_search(self):
        for task in self:
            task.agile_done_environment_id = False
            task.agile_pending_environment_id = False
            task.agile_waiting_for_production = False

    @api.model
    def _search_pending_environments(self, operator, value):
        return self._search_done_environments(operator, value, pending=True)

    @api.model
    def _search_done_environments(self, operator, value, pending=False):
        pending = pending != (
            operator in ("not in", "not like", "not ilike", "not any")
        )
        if operator in ("any", "not any"):
            # Native many2one normalization turns name patterns into related domains.
            value = self.env["project.agile.environment"].search(value).ids
        elif operator not in ("in", "not in"):
            if operator not in (
                "like",
                "ilike",
                "=like",
                "=ilike",
                "not like",
                "not ilike",
            ):
                return NotImplemented
            environments = self.env["project.agile.environment"].search(
                [("display_name", operator.removeprefix("not "), value)]
            )
            value = environments.ids
        return self._environment_completion_domain(value, pending=pending)

    @api.model
    def _environment_completion_domain(self, environment_ids, pending=False):
        done = Domain(
            "agile_environment_status_ids",
            "any",
            [
                ("applicable", "=", True),
                ("environment_id", "in", environment_ids),
                ("status", "in", ["done", "verified"]),
            ],
        )
        if not pending:
            return done
        # Only tracking tasks whose Project has a matching active environment count.
        return (
            Domain("agile_tracks_environments", "=", True)
            & Domain(
                "project_id.agile_environment_ids",
                "any",
                [("id", "in", environment_ids), ("active", "=", True)],
            )
            & ~done
        )

    @api.model
    def _search_waiting_for_production(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        environments = self.env["project.agile.environment"].search(
            [("active", "=", True)]
        )
        production = environments.filtered("is_production")
        waiting = self._environment_completion_domain(
            environments.ids
        ) & self._environment_completion_domain(production.ids, pending=True)
        matches = Domain.OR(waiting if flag else ~waiting for flag in value)
        return matches if operator == "in" else ~matches

    def _sync_environment_statuses(self):
        tasks = self.filtered("agile_tracks_environments")
        tasks.check_access("write")
        tasks.project_id.check_access("read")
        status_model = self.env["project.task.environment.status"]
        # Include hidden identities so an existing line is never inserted twice.
        existing = status_model.sudo().search([("task_id", "in", tasks.ids)])
        pairs = {(line.task_id.id, line.environment_id.id) for line in existing}
        values = []
        for task in tasks:
            for environment in task.project_id.agile_environment_ids.filtered("active"):
                if (task.id, environment.id) not in pairs:
                    values.append(
                        {"task_id": task.id, "environment_id": environment.id}
                    )
        if values:
            context = {
                key: value
                for key, value in self.env.context.items()
                if not key.startswith("default_")
            }
            # Remove Task form defaults before creating status records.
            # pylint: disable-next=context-overridden
            status_model.with_context(context).create(values)

    @api.model
    def _check_environment_derived_input(self, values):
        derived = {
            "agile_tracks_environments",
            "agile_done_environment_id",
            "agile_pending_environment_id",
            "agile_waiting_for_production",
        }
        defaults = {
            key.removeprefix("default_")
            for key in self.env.context
            if key.startswith("default_")
        }
        if derived & (values.keys() | defaults):
            raise AccessError(
                self.env._(
                    "Environment eligibility is derived from the Project and item type."
                )
            )

    @api.constrains("project_id")
    def _check_environment_history_project(self):
        for task in self:
            if any(
                line.environment_id.project_id != task.project_id
                for line in task.agile_environment_status_ids
            ):
                raise ValidationError(
                    self.env._(
                        "Copy tasks with environment history into another Project."
                    )
                )

    def action_environment_history(self):
        self.ensure_one()
        self.check_access("read")
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Environment history"),
            "res_model": "project.task.environment.status",
            "view_mode": "list,form",
            "domain": [("task_id", "=", self.id)],
            "context": {"create": False},
        }

    @api.constrains("parent_id", "project_id", "agile_item_type_id")
    def _check_agile_parent_policy(self):
        for task in self:
            parent = task.parent_id
            if not parent:
                continue
            if (
                task.project_id.agile_enabled or parent.project_id.agile_enabled
            ) and task.project_id != parent.project_id:
                raise ValidationError(_("Agile task hierarchies cannot span projects."))
            if not (
                task.project_id.agile_enabled
                and task.agile_item_type_id
                and parent.agile_item_type_id
            ):
                continue
            if (
                task.agile_item_type_id
                not in parent.agile_item_type_id.allowed_child_type_ids
            ):
                raise ValidationError(
                    _("The parent Agile item type does not allow this child item type.")
                )

    @api.constrains("agile_story_points", "project_id", "agile_item_type_id")
    def _check_agile_story_points(self):
        for task in self.filtered(lambda task: task.project_id.agile_enabled):
            if task.agile_item_type_id and not task.agile_uses_story_points:
                continue
            method = task.project_id.agile_estimation_method
            if method == "none" and task.agile_story_points:
                raise ValidationError(
                    _("Story points require a configured estimation method.")
                )
            if (
                method == "fibonacci"
                and task.agile_story_points not in _FIBONACCI_STORY_POINTS
            ):
                raise ValidationError(
                    _("Story points must use the configured Fibonacci values.")
                )

    @api.depends(
        "agile_story_points",
        "agile_item_type_id.uses_story_points",
        "project_id.agile_enabled",
    )
    def _compute_agile_effective_story_points(self):
        for task in self:
            hour_based = (
                task.project_id.agile_enabled
                and task.agile_item_type_id
                and not task.agile_uses_story_points
            )
            task.agile_effective_story_points = (
                0 if hour_based else task.agile_story_points
            )

    def _agile_stage_domain(self):
        self.ensure_one()
        return [
            ("project_ids", "=", self.project_id.id),
            "|",
            ("agile_item_type_ids", "=", False),
            ("agile_item_type_ids", "in", self.agile_item_type_id.ids),
        ]

    def _first_agile_stage(self):
        self.ensure_one()
        return self.env["project.task.type"].search(
            self._agile_stage_domain(), order="sequence, id", limit=1
        )

    @api.depends("project_id", "agile_item_type_id")
    def _compute_stage_id(self):
        result = super()._compute_stage_id()
        for task in self:
            if not (task.project_id.agile_enabled and task.agile_item_type_id):
                continue
            stage = task.stage_id
            if not stage or (
                stage.agile_item_type_ids
                and task.agile_item_type_id not in stage.agile_item_type_ids
            ):
                task.stage_id = task._first_agile_stage()

        return result

    @api.constrains("stage_id", "agile_item_type_id", "project_id")
    def _check_agile_stage(self):
        for task in self:
            if not (
                task.project_id.agile_enabled
                and task.agile_item_type_id
                and task.stage_id
            ):
                continue
            stage = task.stage_id
            if (
                stage.agile_item_type_ids
                and task.agile_item_type_id not in stage.agile_item_type_ids
            ):
                raise ValidationError(
                    _("Choose a stage compatible with the Agile item type.")
                )

    @api.model
    def _agile_column_types(self, domain):
        # Conservative abstraction: unknown task predicates allow every type.
        # Negation of an unknown predicate cannot safely narrow columns.
        if "!" in domain:
            return None
        conditions = list(Domain(domain).iter_conditions())
        supported = {"agile_item_type_id", "agile_uses_story_points"}
        if not any(condition.field_expr in supported for condition in conditions):
            return None
        # Native grouping normalizes Boolean False to not in [True].
        if any(
            condition.field_expr in supported
            and condition.operator not in ("=", "in")
            and not (condition.operator == "!=" and condition.value is False)
            and not (
                condition.operator == "not in"
                and (
                    tuple(condition.value) == (False,)
                    or (
                        condition.field_expr == "agile_uses_story_points"
                        and tuple(condition.value) == (True,)
                    )
                )
            )
            for condition in conditions
        ):
            return None

        def untyped_condition(condition):
            if condition.field_expr not in supported:
                return Domain.TRUE
            if condition.operator == "!=":
                matches = condition.value is not False
            elif condition.operator == "in":
                matches = False in condition.value
            elif condition.operator == "not in":
                matches = False not in condition.value
            else:
                matches = condition.value is False
            return Domain.TRUE if matches else Domain.FALSE

        if not Domain(domain).map_conditions(untyped_condition).is_false():
            return None

        def type_condition(condition):
            if condition.field_expr not in supported:
                return Domain.TRUE
            field = (
                "id"
                if condition.field_expr == "agile_item_type_id"
                else "uses_story_points"
            )
            return Domain(field, condition.operator, condition.value)

        return (
            self.env["project.agile.item.type"]
            .with_context(active_test=False)
            .search(Domain(domain).map_conditions(type_condition))
        )

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        expanded = super()._read_group_stage_ids(stages, domain)
        project_id = self.env.context.get("default_project_id")
        project = (
            self.env["project.project"].browse(project_id) if project_id else False
        )
        if "!" in domain:
            return expanded

        def outside_agile(condition):
            if condition.field_expr == "project_id.agile_enabled" and (
                (condition.operator == "=" and condition.value is True)
                or (condition.operator == "in" and tuple(condition.value) == (True,))
            ):
                return Domain.FALSE
            if (
                project
                and project.agile_enabled
                and condition.field_expr == "project_id"
                and (
                    (condition.operator == "=" and condition.value == project.id)
                    or (
                        condition.operator == "in"
                        and tuple(condition.value) == (project.id,)
                    )
                )
            ):
                return Domain.FALSE
            return Domain.TRUE

        if not Domain(domain).map_conditions(outside_agile).is_false():
            return expanded
        item_types = self._agile_column_types(domain)
        if item_types is None:
            return expanded
        return expanded.filtered(
            lambda stage: not stage.agile_item_type_ids
            or bool(stage.agile_item_type_ids & item_types)
        )
