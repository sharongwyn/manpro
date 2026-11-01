"""Read-only audit of old definitions, outputs and loader policies."""
import ast
import csv
import json
import re
from pathlib import Path
import openpyxl
from skripsi_search.ingest import write_json

root=Path('.')
definitions={}; outputs={}
for name in ('Testing_Baru','cek_kemiripan_colab'):
    nb=json.loads((root/'reference'/f'{name}.ipynb').read_text(encoding='utf-8'))
    occurrences=[]; assignments=[]; texts=[]
    for i,c in enumerate(nb['cells']):
        src=''.join(c.get('source',[]))
        if c['cell_type']=='code' and not src.lstrip().startswith(('!','%')):
            try: tree=ast.parse(src)
            except SyntaxError: continue
            for node in tree.body:
                if isinstance(node,(ast.FunctionDef,ast.ClassDef)): occurrences.append({'cell':i,'name':node.name})
                if isinstance(node,ast.Assign):
                    for target in node.targets:
                        if isinstance(target,ast.Attribute): assignments.append({'cell':i,'target':ast.unparse(target),'value':ast.unparse(node.value)})
        for out in c.get('outputs',[]):
            text=''.join(out.get('text',[])) or ''.join(out.get('data',{}).get('text/plain',[]))
            if text: texts.append({'cell':i,'text':text})
    definitions[name]={'definitions':occurrences,'attribute_patches':assignments}; outputs[name]=texts
rows=[]
for p in (root/'data').glob('*.xlsx'):
    wb=openpyxl.load_workbook(p,read_only=True,data_only=True)
    for ws in wb:
        it=iter(ws.values); header=next(it)
        for row in it: rows.append(dict(zip(header,row)))
    wb.close()
sentinel=sum(str(r.get('Judul')).strip().upper()=='TIDAK DITEMUKAN' for r in rows)
old_colab={str(r.get('Judul')).strip() for r in rows if len(str(r.get('Judul')).strip())>3}
old_testing={str(r.get('Judul')).strip() for r in rows if str(r.get('Judul')).strip().upper()!='TIDAK DITEMUKAN' and len(str(r.get('Abstrak') or ''))>50}
with (root/'kamus/kamus_method.csv').open(encoding='utf-8-sig') as f: methods=[r['method'] for r in csv.DictReader(f)]
with (root/'kamus/kamus_dataset.csv').open(encoding='utf-8-sig') as f: datasets=[r['dataset'] for r in csv.DictReader(f)]
method_regex=r'\b('+'|'.join(map(re.escape,methods))+r')\b'
data_regex=r'\b('+'|'.join(map(re.escape,datasets))+r')\b'
report={'initial_rows':len(rows),'sentinel_titles':sentinel,'colab_exact_title_dedup':len(old_colab),'testing_filtered_exact_title_dedup':len(old_testing),'definitions':definitions,'old_regex_probes':{'C++':re.findall(method_regex,'Menggunakan C++ dan C#.',re.I),'long_dataset_phrase':re.findall(data_regex,'Google Play Store',re.I),'long_method_phrase':re.findall(method_regex,'K-Means Clustering',re.I),'YOLO_aliases':re.findall(method_regex,'YOLO v8 YOLO-v8 YOLOv11 YOLO11',re.I),'problem_without_terminal_punctuation':bool(re.search(r'([^.!?]*(masalah)[^.!?]*[.!?])','masalah pada deteksi objek',re.I))},'saved_A_rows':[line for o in outputs['Testing_Baru'] for line in o['text'].splitlines() if re.match(r'\d+\s+A\d{2}\s+A\s+',line)],'saved_output_reference':'reports/*_cells.txt contain all saved output text; notebooks in reference preserve full outputs.'}
write_json(root/'reports/legacy_audit.json',report)
print({k:v for k,v in report.items() if k not in ('definitions','saved_A_rows')})
