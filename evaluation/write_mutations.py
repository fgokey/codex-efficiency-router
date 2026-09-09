"""Selected write/diagnostic invariants; subprocess-local mutants, no source edits."""
from pathlib import Path
import subprocess
import sys


def run(root: Path, output: Path) -> list[dict]:
    source=(root/'scripts/write_policy.py').read_text(encoding='utf-8')
    specs=[
        ('astra_can_write','known_executor and not is_astra(model) and not read_only', 'model is not None and not read_only'),
        ('readonly_role_ignored','and not read_only',''),
        ('identity_not_checked','known_executor and not is_astra(model)', 'not is_astra(model)'),
        ('optout_ignored','if no_subagents:', 'if False:'),
        ('writer_capacity_ignored',"    if sum(w.state == 'active' for w in scope.writers) >= scope.writer_limit:", '    if False:'),
        ('authority_ignored','or not scope.authorized or not scope.ownership_clear',''),
        ('unknown_writer_replayed',"or any(w.state == 'unknown' for w in scope.writers)",'') ,
        ('same_owner_started_busy',"if owner.state == 'active':",'if False:'),
        ('astra_never_helps',"if complex_judgment or (qualified_attempts >= 2 and failure_kind in ('capability', 'unexplained')):",'if False:'),
        ('counter_is_capability',"failure_kind in ('capability', 'unexplained')",'True'),
        ('parent_spawns_duplicate_astra','if is_astra(model):','if False:'),
        ('executor_experiment_skipped','if cheap_check_available:','if False:'),
    ]
    harness='''import sys,types,unittest
sys.path.insert(0,'scripts')
m=types.ModuleType('write_policy');sys.modules[m.__name__]=m
exec(compile(sys.stdin.read(),'<write-mutation>','exec'),m.__dict__)
r=unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.discover('tests',pattern='test_write_gate.py'))
sys.exit(2 if r.errors else 0 if r.wasSuccessful() else 1)
'''
    results=[]
    for name,old,new in specs:
        if source.count(old)!=1:
            results.append({'name':name,'outcome':'INVALID_MUTATION'});continue
        p=subprocess.run([sys.executable,'-c',harness],input=source.replace(old,new,1),cwd=root,
                         text=True,encoding='utf-8',capture_output=True,timeout=20)
        (output/f'write-mutation-{name}.log').write_text(p.stdout+p.stderr,encoding='utf-8')
        results.append({'name':name,'outcome':{0:'SURVIVED',1:'KILLED',2:'TEST_ERROR'}.get(p.returncode,'RUNNER_ERROR')})
    return results
