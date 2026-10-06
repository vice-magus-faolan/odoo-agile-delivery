"""Disposable optional-bridge proof and independent relink/Sprint event races."""
import json

from odoo.addons.project_agile_solution.tests.task_concurrency import race, seed

assert env.cr.dbname == 'odoo_agile_verify_install'
for name in ('project_agile_solution', 'project_scrum', 'project_agile_solution_scrum'):
    assert env['ir.module.module'].search([('name', '=', name)]).state == 'installed'
for name in ('project_agile_git', 'project_scrum_analytics', 'sale', 'document_page'):
    module = env['ir.module.module'].search([('name', '=', name)])
    assert not module or module.state != 'installed', name
print('M8_ISOLATED_SOLUTION_SCRUM_INSTALL_OK', flush=True)
results = []
for index, (winner_action, loser_action) in enumerate((('relink', 'start'), ('start', 'relink'), ('relink', 'add'), ('relink', 'close'))):
    manager, project, solution, revision = seed(env, 'M8SCOPERACE' + str(index))
    task = env['project.task'].with_user(manager).create({'name': 'SYNTHETIC scope race', 'project_id': project.id,
        'agile_item_type_id': env.ref('project_agile.project_agile_item_type_story').id})
    link = env['project.agile.requirement.task.link'].with_user(manager).create({'task_id': task.id, 'requirement_revision_id': revision.id})
    successor = revision.browse(revision.requirement_id.action_new_revision()['res_id'])
    successor.write({'description': 'SYNTHETIC deliberately changed v2'})
    team = env['project.agile.team'].with_user(manager).create({'name': 'SYNTHETIC race team', 'project_id': project.id})
    sprint = env['project.sprint'].with_user(manager).create({'name': 'SYNTHETIC race sprint', 'project_id': project.id, 'team_id': team.id})
    if loser_action == 'add':
        sprint.action_start()
    else:
        task.write({'sprint_id': sprint.id})
    if loser_action == 'close':
        sprint.action_start()
    env.cr.commit()
    common = {'uid': manager.id, 'task_id': task.id, 'sprint_id': sprint.id, 'successor_id': successor.id}
    workers = race(env, {**common, 'action': winner_action}, {**common, 'action': loser_action})
    event_type = {'start': 'committed', 'add': 'added', 'close': 'carried_to_backlog'}[loser_action if loser_action != 'relink' else winner_action]
    event = env['project.sprint.scope.event'].with_user(manager).search([('task_id', '=', task.id), ('event_type', '=', event_type)])
    contexts = env['project.agile.solution.sprint.context'].with_user(manager).search([('scope_event_id', '=', event.id)])
    assert len(event) == 1 and event.solution_capture_status == 'captured'
    expected = revision if winner_action == 'start' else successor
    assert contexts.requirement_revision_id == expected, (winner_action, loser_action, contexts.requirement_revision_id.ids)
    assert json.loads(contexts.payload_json)['requirement']['revision_id'] == expected.id
    results.append({'winner': winner_action, 'loser': loser_action, 'captured_revision': expected.number, 'workers': workers})
print('M8_SCRUM_TRACE_CONCURRENCY_OK ' + json.dumps({'races': results}, sort_keys=True), flush=True)
