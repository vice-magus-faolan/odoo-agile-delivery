"""Independent-process disposable Git policy race worker, not production code."""
import json
import os
from pathlib import Path
import time
from unittest.mock import patch

from odoo import Command
from psycopg2.errors import DeadlockDetected, SerializationFailure

scenario = json.loads(os.environ["GIT_POLICY_SCENARIO"])
directory = Path(scenario["directory"])
name = scenario["worker"]
operation = scenario["operation"]

def signal(suffix):
    (directory / (name + '.' + suffix)).write_text('ready')


def wait(filename):
    deadline = time.monotonic() + 15
    while not (directory / filename).exists():
        if time.monotonic() > deadline:
            raise RuntimeError('Race rendezvous timed out')
        time.sleep(0.02)


def dependency_away_and_back(task):
    blocker = env['project.task'].with_user(scenario['executor_id']).browse(scenario['blocker_id'])
    before = task.git_policy_transition_version
    if operation == 'manual_dependency':
        task.write({'depend_on_ids': [Command.link(blocker.id)]})
    else:
        blocker.write({'state': '01_in_progress'})
    env.flush_all()
    assert task.state == '04_waiting_normal'
    intermediate = task.git_policy_transition_version
    assert intermediate > before
    if operation == 'manual_dependency':
        task.write({'depend_on_ids': [Command.unlink(blocker.id)]})
    else:
        blocker.write({'state': '1_done'})
    env.flush_all()
    assert task.state == '01_in_progress' and task.git_policy_transition_version > intermediate
    result['transition_versions'] = [before, intermediate, task.git_policy_transition_version]


def mutate():
    author = env['res.users'].browse(scenario['author_id'])
    task = env['project.task'].with_user(scenario['executor_id']).browse(scenario['task_id'])
    if operation == 'disable':
        env['project.project'].with_user(author).browse(scenario['project_id']).action_disable_git_policy()
    elif operation == 'revision':
        env['project.git.policy.revision'].with_user(author).browse(scenario['revision_id']).action_new_revision()
    elif operation == 'revoke':
        revision = env['project.git.policy.revision'].browse(scenario['revision_id'])
        revision.rule_id.activation_id._revoke('authority_changed')
    elif operation == 'manual':
        task.write({'stage_id': scenario['other_stage_id']})
        task.write({'stage_id': scenario['source_stage_id']})
    elif operation in {'manual_dependency', 'blocker_state'}:
        dependency_away_and_back(task)
    elif operation == 'identity':
        env['res.users'].browse(scenario['executor_id']).write({'active': False})
    elif operation == 'fact':
        env['project.git.pull.request'].browse(scenario['pr_id']).write({'head_sha': 'c' * 40})
    elif operation == 'stage':
        env['project.task.type'].browse(scenario['target_stage_id']).write({'active': False})
    else:
        raise RuntimeError('Unknown fixed fixture mutation')


result = {'operation': operation, 'pid': os.getpid(), 'claimed': False, 'restarts': 0}
for restart in range(3):
    try:
        env.cr.execute("SET LOCAL lock_timeout = '8s'")
        env.cr.execute("SET LOCAL statement_timeout = '12s'")
        env.cr.execute('SELECT pg_backend_pid()')
        result['backend_pid'] = env.cr.fetchone()[0]
        signal('started')
        attempts = env['project.git.policy.attempt']
        if operation in {'claim', 'claim_crash', 'write_crash'}:
            signal('ready')
            wait('start')
            item = attempts._claim_attempt()
            result['claimed'] = bool(item)
            if operation == 'claim_crash':
                assert item
                os._exit(79)
            if item:
                if operation == 'write_crash':
                    def crash_after_task(*args, **kwargs):
                        os._exit(77)
                    with patch.object(type(env['project.git.policy.effect']), '_append', crash_after_task):
                        item._process_claim()
                else:
                    time.sleep(0.3)
                    item._process_claim()
        elif operation in {'process', 'apply_hold'}:
            item = attempts.browse(scenario['attempt_id'])
            signal('executing')
            item._process_claim(scenario['lease_token'])
            if operation == 'apply_hold':
                signal('ready')
                wait(name + '.release')
        else:
            mutate()
            signal('ready')
            wait(name + '.release')
        env.cr.commit()
        result.update(state=item.state, reason=item.reason) if operation in {'process', 'apply_hold', 'claim'} and item else None
        break
    except (SerializationFailure, DeadlockDetected):
        env.cr.rollback()
        env.invalidate_all()
        result['restarts'] += 1
else:
    raise RuntimeError('Fresh-transaction retries exhausted')
(directory / (name + '.json')).write_text(json.dumps(result, sort_keys=True))
