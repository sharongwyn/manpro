"""Execute the notebook's Python cells in order in one namespace (local CPU).

This is a local sequential-cell check, not a claim of remote Colab execution.
"""
import contextlib
import io
import json
import time
import traceback
from pathlib import Path

path=Path('Pencarian_Kemiripan_Skripsi.ipynb')
nb=json.loads(path.read_text(encoding='utf-8')); ns={'__name__':'__main__'}
def display(obj):
    print(obj.to_string(index=False) if hasattr(obj,'to_string') else repr(obj))
ns['display']=display
checks=[]; count=0
for i,c in enumerate(nb['cells']):
    if c['cell_type']!='code': continue
    count+=1; log=io.StringIO(); start=time.perf_counter(); status='passed'
    try:
        with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
            exec(compile(''.join(c['source']),f'{path}:cell-{i}','exec'),ns)
    except Exception:
        status='failed'; log.write(traceback.format_exc())
    c['execution_count']=count
    c['outputs']=[{'output_type':'stream','name':'stdout','text':log.getvalue().splitlines(True)}]
    checks.append({'cell':i,'execution_count':count,'status':status,'seconds':round(time.perf_counter()-start,3)})
    print(f'Cell {i}: {status}',flush=True)
    if status=='failed': break
Path('reports/notebook_execution.json').write_text(json.dumps({'method':'Local sequential exec of all Python cells in a shared namespace; Colab upload branch not remotely executed','cells':checks,'all_passed':len(checks)==sum(c['cell_type']=='code' for c in nb['cells']) and all(x['status']=='passed' for x in checks)},indent=2),encoding='utf-8')
Path('reports/Pencarian_Kemiripan_Skripsi_executed.ipynb').write_text(json.dumps(nb,ensure_ascii=False,indent=1),encoding='utf-8')
if any(x['status']=='failed' for x in checks): raise SystemExit(log.getvalue())
