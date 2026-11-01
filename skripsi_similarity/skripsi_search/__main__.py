import argparse
import json
from pathlib import Path
from .engine import load_index,CONFIGS
from .evaluate import run_evaluation,write_csv
from .ingest import read_sources,write_json

def main():
    p=argparse.ArgumentParser(description='Exact SBERT + BM25 skripsi search')
    p.add_argument('--root',default='.',help='Project directory containing sources.json')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('ingest')
    ix=sub.add_parser('index'); ix.add_argument('--rebuild',action='store_true')
    search=sub.add_parser('search'); search.add_argument('--title',default=''); search.add_argument('--description',default=''); search.add_argument('--problem',default=''); search.add_argument('--method',default=''); search.add_argument('--dataset',default=''); search.add_argument('--query-json'); search.add_argument('--top-k',type=int,default=5); search.add_argument('--config',choices=CONFIGS); search.add_argument('--rerank',type=float,choices=[0,.05,.1]); search.add_argument('--output',default='reports/search.json')
    ev=sub.add_parser('evaluate'); ev.add_argument('--queries'); ev.add_argument('--annotations')
    args=p.parse_args(); root=Path(args.root)
    if args.command=='ingest':
        c=json.loads((root/'sources.json').read_text(encoding='utf-8')); docs,report=read_sources(c,root); write_json(root/'reports/corpus.json',docs); write_json(root/'reports/data_quality.json',report)
        print(json.dumps({k:report[k] for k in ('initial_rows','documents','excluded_count','duplicates_merged','conflict_groups')},indent=2)); return
    index=load_index(root,rebuild=getattr(args,'rebuild',False))
    if args.command=='index': print(json.dumps({'documents':len(index.docs),'fingerprint':index.fingerprint,'truncation':index.truncation},indent=2)); return
    if args.command=='evaluate':
        report=run_evaluation(index,root,args.queries,args.annotations)
        for r in report['aggregate']: print(r)
        return
    q=json.loads(Path(args.query_json).read_text(encoding='utf-8')) if args.query_json else {k:getattr(args,k) for k in ('title','description','problem','method','dataset')}
    settings=json.loads((root/'default_config.json').read_text(encoding='utf-8'))
    result=index.search(q,args.top_k,args.config or settings['configuration'],settings['rerank_strength'] if args.rerank is None else args.rerank)
    dest=root/args.output; write_json(dest,result); write_csv(dest.with_suffix('.csv'),result['results'])
    print('Rank | ID | SBERT | BM25 | Fusion | Judul')
    for r in result['results']: print(f"{r['final_rank']:>4} | {r['id']} | {r['sbert_raw']:.3f} | {r['bm25_raw']:.2f} | {r['hybrid_score']:.4f} | {r['title']}")
    if result['no_positive_signal']: print('Tidak ada sinyal positif pada channel konfigurasi ini; tidak ada kandidat ditampilkan.')
    print(result['interpretation']); print(f'JSON: {dest}; CSV: {dest.with_suffix(".csv")}')

if __name__=='__main__': main()
