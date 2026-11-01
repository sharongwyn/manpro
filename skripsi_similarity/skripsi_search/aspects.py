"""Rule-based extraction; confidence is rule strength, never a calibrated probability."""
import csv
import re
from pathlib import Path
from .text import clean, digest, sentences

ASPECT_VERSION='rules-v1'
FIELDS=('problem','algorithm','technology','research_method','object','dataset_identity','platform','data_type','collection','context')
PLATFORMS={'kaggle','uci','mendeley data','google play','google play store','twitter','instagram','youtube','tiktok','facebook','github','jobstreet','linkedin','wikidata','bmkg','bps','badan pusat statistik','spotify','chartmetric','turnbackhoax'}
IDENTITIES={'imagenet','mnist','cifar-10','cifar-100','isic','ham10000','global burden of disease','ravdess','iemocap','jester','nasa power','tkpi','tabel komposisi pangan indonesia','sentinel-2','chirps'}
COLLECTION={'kuesioner','wawancara','observasi','studi kasus','survei','scraping','web scraping','crawling'}
RESEARCH={'waterfall','scrum','agile','kanban','prototyping','rad','mdlc','multimedia development life cycle','sdlc','v-shaped model','uat','user acceptance testing','sus','system usability scale','black box testing','white box testing','grey box testing','tam','technology acceptance model','utaut','delphi method','analisis deskriptif','analisis kuantitatif','analisis kualitatif','studi literatur','systematic literature review','slr','design science research','dsr','action research','case study','focus group discussion','fgd','observasi','wawancara','kuesioner','survei'}
TECH={'flutter','react native','android studio','swift','kotlin','java','python','javascript','typescript','php','c#','c++','go','rust','laravel','codeigniter','django','flask','fastapi','node.js','express.js','spring boot','asp.net','rest api','graphql','grpc','websocket','mysql','postgresql','mongodb','redis','firebase','neo4j','sqlite','oracle','sql server','mariadb','iot','internet of things','arduino','raspberry pi','esp32','esp8266','mqtt','lora','zigbee','unity','unreal engine','godot','vr','ar','mixed reality','mvc','mvvm','bloc','provider','getx','redux','power bi','tableau','looker studio','excel solver','sparql','rdf','protégé','oauth','jwt','rbac','mediapipe','docker','phpseclib'}
ALIASES={'convolutional neural network':'cnn','support vector machine':'svm','k-nearest neighbors':'knn','k-means clustering':'k-means','algoritma genetika':'genetic algorithm','regresi linear':'linear regression','regresi logistik':'logistic regression','badan pusat statistik':'bps','google play store':'google play','tabel komposisi pangan indonesia':'tkpi','vision transformer':'vit','recurrent neural network':'rnn'}
OBJECTS=['aksara sunda','emosi','gerak bibir','hand gesture','sertifikat','kurikulum','rute','diet','darah','depresi','parkir','lalu lintas','gudang','pemrograman','panen','musik','chatbot','sentimen','penjualan','karyawan','mahasiswa','penyakit','saham']

class Extractor:
    def __init__(self, paths=()):
        self.terms=[]; self.problem_words=['masalah','kesulitan','bertujuan','tujuan','sulit','kendala']
        hashes={}
        for path in paths:
            path=Path(path); hashes[path.name]=digest(path.read_text(encoding='utf-8-sig'))
            with path.open(encoding='utf-8-sig',newline='') as f:
                reader=csv.DictReader(f)
                for row in reader:
                    for col,term in row.items():
                        term=clean(term).lower()
                        if not term: continue
                        if col=='problem': self.problem_words.append(term); continue
                        if col=='method': field='technology' if term in TECH else 'research_method' if term in RESEARCH else 'algorithm'
                        else: field='dataset_identity' if term in IDENTITIES else 'platform' if term in PLATFORMS else 'collection' if term in COLLECTION else 'data_type'
                        if term in {'data internal','data primer','data sekunder','data perusahaan'}: continue
                        self.terms.append((term,field,ALIASES.get(term,term)))
        for t in IDENTITIES|TECH|COLLECTION:
            field='dataset_identity' if t in IDENTITIES else 'technology' if t in TECH else 'collection'
            self.terms.append((t,field,ALIASES.get(t,t)))
        for t in OBJECTS: self.terms.append((t,'object',t))
        for t in ['citra','gambar','video','audio','teks','spektrogram','ulasan']:
            self.terms.append((t,'data_type',t))
        self.terms=sorted(set(self.terms),key=lambda x:(-len(x[0]),x))
        self.pattern=re.compile(r'(?<![\w+#])(?:'+ '|'.join(re.escape(t) for t,_,_ in self.terms)+r')(?![\w+#])',re.I)
        self.lookup={t:(f,c) for t,f,c in self.terms}
        self.fingerprint=digest({'version':ASPECT_VERSION,'hashes':hashes,'terms':self.terms,'aliases':ALIASES,'problem':self.problem_words})

    def extract(self,text):
        text=clean(text); result={k:{'status':'unknown','items':[]} for k in FIELDS}
        spans=list(sentences(text))
        def add(field,canonical,start,end,family=None):
            sent=next((s.group().strip() for s in spans if s.start()<=start<s.end()),text)
            role='uncertain'; strength=.5
            if field in ('algorithm','technology','research_method'):
                # Local clause evidence, conservative when multiple role markers coexist.
                local=re.split(r'[,;]|\b(?:sedangkan|namun|tetapi)\b',sent,flags=re.I)
                clause=next((c for c in local if text[start:end].lower() in c.lower()),sent)
                if re.search(r'tidak (?:menggunakan|dipakai)|ditolak|tidak dipilih',clause,re.I): role='rejected'; strength=.9
                elif re.search(r'penelitian (?:terdahulu|sebelumnya)|studi terdahulu',clause,re.I): role='prior_work'; strength=.8
                elif re.search(r'pembanding|dibandingkan|baseline',clause,re.I): role='comparison'; strength=.7
                elif re.search(r'menggunakan|memakai|digunakan|menerapkan|diimplementasi',clause,re.I): role='used'; strength=.9
            else: role='observed'; strength=.8 if field!='object' else .5
            item={'canonical':canonical,'original':text[start:end],'evidence':sent,'start':start,'end':end,'role':role,'strength':strength}
            if family: item['family']=family
            result[field]['items'].append(item); result[field]['status']='found'
        yolo=[]
        for m in re.finditer(r'(?<!\w)yolo\s*[- ]?v?\s*(\d{1,2})([nslmx]?)(?!\w)',text,re.I):
            add('algorithm','yolov'+m[1]+m[2].lower(),m.start(),m.end(),'yolo'); yolo.append(m.span())
        for m in self.pattern.finditer(text):
            if any(a<=m.start()<b for a,b in yolo): continue
            field,canonical=self.lookup[m.group().lower()]
            add(field,canonical,m.start(),m.end())
        for s in spans:
            if any(re.search(r'(?<!\w)'+re.escape(w)+r'(?!\w)',s.group(),re.I) for w in self.problem_words):
                add('problem',s.group().strip().lower(),s.start(),s.end())
        for m in re.finditer(r'\b(?:19|20)\d{2}(?:\s*(?:-|sampai|hingga)\s*(?:19|20)\d{2})?\b|\b(?:di|populasi|responden)\s+[A-Z][\w-]+(?:\s+[A-Z][\w-]+){0,3}',text):
            add('context',m.group().lower(),m.start(),m.end())
        return result

def compare(a,b):
    same=[]; different=[]; unknown=[]; score=0.
    weights={'algorithm':.45,'dataset_identity':.30,'object':.15,'problem':.05,'technology':.01,'context':.04}
    for field in FIELDS:
        ai=[x for x in a[field]['items'] if x['role'] not in ('prior_work','rejected','comparison')]
        bi=[x for x in b[field]['items'] if x['role'] not in ('prior_work','rejected','comparison')]
        if not ai or not bi: unknown.append(field); continue
        aset={x['canonical'] for x in ai}; bset={x['canonical'] for x in bi}; common=aset&bset
        if common:
            strength=min(max(x['strength'] for x in ai),max(x['strength'] for x in bi))
            score+=weights.get(field,0)*strength*len(common)/len(aset|bset)
            same.append({'aspect':field,'values':sorted(common),'query_evidence':[x for x in ai if x['canonical'] in common],'document_evidence':[x for x in bi if x['canonical'] in common]})
        elif field in ('algorithm','dataset_identity','object','context'):
            different.append({'aspect':field,'interpretation':'Istilah teramati berbeda; bukan bukti bahwa seluruh aspek berbeda.','query_evidence':ai,'document_evidence':bi})
    return {'score':score,'similarities':same,'differences':different,'unknown':unknown}
