import json
import re
from collections import Counter, defaultdict
from pathlib import Path
import openpyxl
from .text import value, clean, title_key, digest, parse_chapter, legacy_sections

ALIASES={'title':'title','judul':'title','abstract':'abstract','abstrak':'abstract','chapter1':'chapter','bab1':'chapter','latarbelakang':'chapter','year':'year','tahun':'year','department':'department','prodi':'department','jurusan':'department','id':'repository_id','repositoryid':'repository_id','nrp':'nrp','namapenulis':'author','nama':'author'}

def column(c):
    return ALIASES.get(re.sub(r'[^\w]','',str(c).casefold()).replace('_',''),str(c).strip().casefold())

def read_sources(config, root):
    records=[]; excluded=[]; sources=[]
    for src in config['sources']:
        path=Path(root)/src['path']
        wb=openpyxl.load_workbook(path,read_only=True,data_only=True)
        ws=wb[src['sheet']]; it=iter(ws.values); headers=[column(c) for c in next(it)]
        if len(headers)!=len(set(headers)): raise ValueError(f'Duplicate normalized columns: {path}')
        count=0
        for rownum,row in enumerate(it,2):
            count+=1; r={k:value(v) for k,v in zip(headers,row)}
            p={'file':src['path'],'sheet':src['sheet'],'row':rownum,'repository_id':r.get('repository_id',''),'nrp':r.get('nrp',''),'author':r.get('author',''),'year':r.get('year',''),'department':r.get('department') or src['department']}
            title=r.get('title',''); abstract=r.get('abstract',''); chapter=r.get('chapter','')
            reason='missing_or_sentinel_title' if not title else 'no_informative_text' if len(tokens_informative(abstract+' '+chapter))<3 else ''
            if reason:
                excluded.append({**p,'title':title,'raw_title':str(row[headers.index('title')]) if 'title' in headers else '', 'reason':reason}); continue
            rec={k:r.get(k,'') for k in ('title','abstract','chapter','year','repository_id','nrp','author')}
            rec['year']=re.sub(r'\.0$','',rec['year']); rec['department']=p['department']; rec['provenance']=[p]
            records.append(rec)
        sources.append({**src,'rows':count,'sha256':__import__('hashlib').sha256(path.read_bytes()).hexdigest()})
        wb.close()
    groups=defaultdict(list)
    for r in records: groups[title_key(r['title'])].append(r)
    docs=[]; conflicts=[]; merged=[]
    for key,items in sorted(groups.items()):
        # Compare all pairs before merging; do not transitively bridge conflicting identities.
        reasons=[]
        for i,a in enumerate(items):
            for b in items[i+1:]:
                for field in ('repository_id','author','year'):
                    if a[field] and b[field] and title_key(a[field])!=title_key(b[field]): reasons.append(field)
                if a['abstract'] and b['abstract'] and clean(a['abstract']).casefold()!=clean(b['abstract']).casefold(): reasons.append('abstract')
        if reasons:
            exact=defaultdict(list)
            for r in items:
                exact[digest({k:v for k,v in r.items() if k!='provenance'})].append(r)
            partitions=list(exact.values())
        else:
            partitions=[items]
        if reasons: conflicts.append({'title_key':key,'fields':sorted(set(reasons)),'sources':[p for r in items for p in r['provenance']]})
        for part in partitions:
            doc={k:max((r[k] for r in part),key=lambda s:(len(s),s)) for k in part[0] if k!='provenance'}
            doc['provenance']=sorted([p for r in part for p in r['provenance']],key=lambda p:(p['file'],p['sheet'],p['row']))
            identity='repo:'+doc['repository_id'] if doc['repository_id'] else 'title:'+key
            if reasons and not doc['repository_id']: identity+=':'+digest({k:doc[k] for k in ('author','year','abstract','chapter')})
            doc['id']='thesis-'+digest(identity)[:20]
            doc['parsed']=parse_chapter(doc['chapter']); doc['legacy_sections']=legacy_sections(doc['chapter'])
            docs.append(doc)
            if len(part)>1: merged.append({'id':doc['id'],'removed_count':len(part)-1,'provenance':doc['provenance']})
    # Same repository ID with different titles is a conflict, never silently overwrite.
    counts=Counter(d['id'] for d in docs)
    for d in docs:
        if counts[d['id']]>1:
            conflicts.append({'id':d['id'],'reason':'repository_id_with_distinct_titles','title':d['title']})
            d['id']+='-'+digest(title_key(d['title']))[:8]
    docs.sort(key=lambda d:d['id'])
    report={'initial_rows':sum(s['rows'] for s in sources),'valid_rows_before_merge':len(records),'documents':len(docs),'excluded_count':len(excluded),'duplicates_merged':sum(x['removed_count'] for x in merged),'conflict_groups':len(conflicts),'sources':sources,'excluded':excluded,'merges':merged,'conflicts':conflicts,'completeness':{k:sum(bool(d.get(k)) for d in docs) for k in ('title','abstract','chapter','year','department','repository_id','author')},'parsing':{k:dict(Counter(d['parsed']['sections'][k]['status'] for d in docs)) for k in ('scope','problem','purpose')}}
    return docs,report

def tokens_informative(s):
    return re.findall(r'\w+',clean(s))

def write_json(path,obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
