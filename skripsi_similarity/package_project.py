import hashlib
import json
import zipfile
from pathlib import Path
root=Path('.').resolve()
destination=root.parent/'skripsi_similarity.zip'
excluded={'.model_cache','.embedding_cache','.pytest_cache','__pycache__','.venv','.git'}
files=sorted(p for p in root.rglob('*') if p.is_file() and not any(part in excluded for part in p.relative_to(root).parts) and p.suffix not in ('.pyc','.zip'))
for source in json.loads((root/'reports/source_manifest.json').read_text(encoding='utf-8')):
    target=root/'reference'/Path(source['original']).name
    assert hashlib.sha256(target.read_bytes()).hexdigest()==source['sha256'],target
with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as z:
    for p in files: z.write(p,Path(root.name)/p.relative_to(root))
with zipfile.ZipFile(destination) as z:
    assert z.testzip() is None
    assert all(not n.startswith('/') and '..' not in Path(n).parts for n in z.namelist())
    required=['skripsi_search/engine.py','Pencarian_Kemiripan_Skripsi.ipynb','README.md','reports/evaluation/aggregate.json','tests/test_core.py','data/DSA.xlsx','data/INFOR.xlsx','data/SIB.xlsx']
    assert all(root.name+'/'+n in z.namelist() for n in required)
print(json.dumps({'archive':str(destination),'files':len(files),'bytes':destination.stat().st_size,'source_hashes_verified':True,'zip_integrity':'passed'},indent=2))
