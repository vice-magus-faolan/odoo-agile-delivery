"""Materialize public-informed synthetic inputs, without implying customer proof."""
from odoo import Command


def seed_scenario(env, manager, company, scenario):
    """Create real intent/context/baselines; task links and acceptance remain later."""
    caller = env['project.agile.solution'].with_user(manager).env
    project = caller['project.project'].create({'name': scenario['project_name'], 'agile_key': scenario['project_key'],
                'company_id': company.id, 'agile_enabled': True, 'privacy_visibility': 'employees'})
    solution = caller['project.agile.solution'].create({'name': scenario['project_name'], 'project_id': project.id})
    tasks = {source['key']: caller['project.task'].create({'name': source['name'], 'project_id': project.id,
             'description': source.get('manual_description', ''),
             'agile_item_type_id': caller.ref('project_agile.project_agile_item_type_' + source['item_type']).id}) for source in scenario['tasks']}
    requirements = _seed_requirements(caller, solution, scenario)
    contexts, question = _seed_context(caller, solution, tasks, requirements, scenario)
    sow = caller['project.agile.solution.revision']
    if scenario['sow']:
        sow = _document(caller, solution, 'sow', scenario, requirements, contexts)
        sow.action_submit()
        sow.action_approve()
    spec = _document(caller, solution, 'spec', scenario, requirements, contexts, sow)
    spec.action_submit()
    spec.action_approve()
    return {'project': project, 'solution': solution, 'requirements': requirements, 'contexts': contexts,
            'question': question, 'sow': sow, 'spec': spec, 'tasks': tasks}


def _seed_requirements(env, solution, scenario):
    requirements = {}
    for source in scenario['requirements']:
        identity = env['project.agile.requirement'].create({'name': source['key'], 'solution_id': solution.id})
        requirements[source['key']] = env['project.agile.requirement.revision'].create({
            'requirement_id': identity.id, 'title': source['text'], 'description': source['text'],
            'requirement_type': source['type'], 'rationale': source['rationale'], 'priority': source['priority'],
            'verification_method': 'Synthetic scenario evaluation; not observed production evidence',
            'acceptance_expectations': source['verification'], 'audience': source['audience'],
        })
    return requirements


def _seed_context(env, solution, tasks, requirements, scenario):
    contexts = env['project.agile.solution.context.revision']
    for actor in scenario['actors']:
        contexts |= _context(env, solution, 'actor', actor['key'], business_role=actor['role'])
    for domain in scenario['domains']:
        contexts |= _context(env, solution, 'domain', domain, body='<p>' + domain + ' design area.</p>')
    deliverable = scenario['deliverable']
    contexts |= _context(env, solution, 'deliverable', deliverable['text'],
                         evaluation_expectations='Evaluate the explicitly referenced requirements; Task Done is not acceptance.',
                         affected_requirement_revision_ids=_references(requirements, deliverable))
    source = scenario['questions'][0]
    question = _context(env, solution, 'question', source['text'], question=source['text'], owner_id=env.user.id,
                        external_owner=source['owner_role'], planning_significance=source['significance'],
                        affected_requirement_revision_ids=_references(requirements, source), audience=source['audience'],
                        spike_task_ids=[Command.set(tasks[source['spike_task']].ids)] if source.get('spike_task') else [])
    if source['resolution']:
        question.action_resolve(source['resolution'], 'SYNTHETIC explicit scope decision, not a customer signature.')
    contexts |= question
    for source in scenario['decisions']:
        contexts |= _context(env, solution, 'decision', source['choice'], decision_context=source['context'],
                             choice=source['choice'], consequences=source['consequences'],
                             affected_requirement_revision_ids=_references(requirements, source), audience=source['audience'])
    contexts |= _context(env, solution, 'section', 'SYNTHETIC user journey / persona narrative',
                         body='<p>' + scenario['journey'] + '</p>', sequence=5)
    return contexts, question


def _references(requirements, source):
    return [Command.set([requirements[key].id for key in source['requirements']])]


def _context(env, solution, kind, title, **values):
    identity = env['project.agile.solution.context'].create({'name': title, 'kind': kind, 'solution_id': solution.id})
    return env['project.agile.solution.context.revision'].create({'context_id': identity.id, 'title': title, **values})


def _document(env, solution, kind, scenario, requirements, contexts, sow=None):
    identity = env['project.agile.solution.document'].create({'name': scenario['project_name'] + ' ' + kind,
                'solution_id': solution.id, 'kind': kind, 'approver_id': env.user.id})
    revision = env['project.agile.solution.revision'].create({'document_id': identity.id, 'title': identity.name,
                'based_sow_revision_id': sow.id if sow else False,
                'requirement_revision_ids': [Command.set([row.id for row in requirements.values()])],
                'context_revision_ids': [Command.set(contexts.ids)]})
    template = env.ref('project_agile_solution.template_sow_skeleton' if kind == 'sow' else 'project_agile_solution.template_internal_brief')
    revision.action_apply_template(template.id)
    if kind == 'sow':
        for section, text in zip(revision.section_ids.sorted('sequence'), scenario['sow_narrative']):
            section.write({'body': '<p>SYNTHETIC: ' + text + '</p>'})
    else:
        revision.section_ids[0].write({'body': '<p>SYNTHETIC: ' + scenario['purpose'] + '</p>'})
    return revision
