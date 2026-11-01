import hashlib
import json
import math
import re
import unicodedata
from bisect import bisect_right

TEXT_VERSION = 'clean-parse-technical-v1'
SENTINELS = {'tidak ditemukan', 'not found', 'nan', 'none', 'null', '-', 'n/a'}
STOP = set('yang dan di ke dari untuk pada dengan dalam adalah ini itu atau juga serta oleh sebagai dapat akan agar karena sehingga bahwa para tersebut terhadap antara sebuah suatu ada tidak lebih sangat telah secara hal saat masih'.split())

def value(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ''
    s = unicodedata.normalize('NFKC', str(v)).strip()
    return '' if s.casefold() in SENTINELS else s

def clean(v):
    s = value(v).replace('\x00', ' ')
    s = re.sub(r'\b\d{1,3}\s+Universitas Kristen Petra\s*[-–]*', ' ', s, flags=re.I)
    s = re.sub(r'(?im)^\s*(?:\d+\s*)?Universitas Kristen Petra\s*[-–]*\s*$', ' ', s)
    s = re.sub(r'(?m)^\s*\d{1,4}\s*$', ' ', s)
    s = re.sub(r'Universitas Kristen Petra\s*[-–]{2,}', ' ', s, flags=re.I)
    return re.sub(r'\s+', ' ', s).strip()

def title_key(v):
    return re.sub(r'[^\w]+', ' ', clean(v).casefold()).strip()

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()

def tokens(text, legacy=False):
    if legacy:
        return [w for w in re.sub(r'[^a-z0-9\s]', ' ', text.lower()).split() if w not in STOP and len(w)>1]
    # C++, C#, Node.js, TF-IDF, YOLOv8 and model versions remain atomic.
    return [w for w in re.findall(r'[^\W_]+(?:[.+#-]+[^\W_]+)*[+#]*', clean(text).casefold()) if w not in STOP]

NAMES = {
    'problem': r'(?:rumusan|perumusan|identifikasi)\s+masalah',
    'scope': r'(?:ruang\s+lingkup(?:\s+(?:skripsi|penelitian))?|batasan(?:\s+(?:masalah|penelitian))?)',
    'purpose': r'tujuan(?:\s+(?:penelitian|skripsi))?',
    'background': r'latar\s+belakang(?:\s+masalah)?',
    'benefit': r'manfaat(?:\s+penelitian)?',
    'structure': r'sistematika(?:\s+(?:penulisan|penelitian))?',
    'methodology': r'(?:metodologi|metode)\s+penelitian',
}
HEADING = re.compile(r'(?<![\w.])1\s*\.\s*\d{1,2}(?!\d)\s*\.?\s*(?=[A-Za-z])', re.I)

def parse_chapter(raw):
    text = clean(raw)
    # Recognized numbered headings are boundaries; numbered lists are not headings.
    heads=[]
    for m in HEADING.finditer(text):
        tail=text[m.end():]
        named=next(((k,re.match(p,tail,re.I)) for k,p in NAMES.items() if re.match(p,tail,re.I)),None)
        if named: heads.append((m.start(),m.end()+named[1].end(),named[0]))
    result={}
    for key in ('problem','scope','purpose'):
        parts=[text[end:(heads[i+1][0] if i+1<len(heads) else len(text))].strip(' .:-') for i,(_,end,k) in enumerate(heads) if k==key]
        content=' '.join(parts)
        hinted=bool(re.search(NAMES[key],text,re.I))
        status='parsed' if content else ('parse_failed' if hinted else 'not_available')
        result[key]={'text':content,'status':status}
    return {'raw':value(raw),'cleaned':text,'sections':result,'heading_count':len(heads)}

def legacy_sections(raw):
    text=re.sub(r'\s+',' ',value(raw))
    text=re.sub(r'\d*\s*Universitas Kristen Petra\s*-*',' ',text)
    heads=[m for m in re.finditer(r'(?<![\d.])1\.\d{1,2}\.?\s+(?=[A-Za-z])',text) if text[m.end():m.end()+1].isupper()]
    out={'scope':'','problem':''}
    for i,m in enumerate(heads):
        for k in out:
            patterns={'problem':r'(?:rumusan|perumusan|identifikasi)\s+masalah','scope':r'ruang\s+lingkup|batasan(?:\s+masalah|\s+penelitian)?'}
            h=re.match(patterns[k],text[m.end():m.end()+60],re.I)
            if h: out[k]+=' '+text[m.end()+h.end():heads[i+1].start() if i+1<len(heads) else len(text)].strip()
    return {k:v.strip()[:1500] for k,v in out.items()}

def sentences(text):
    return [m for m in re.finditer(r'[^.!?]+(?:[.!?]+(?=\s|$)|$)',text) if m.group().strip()]

def chunk_text(text, tokenizer, max_length, doc_id, section, overlap=16):
    """Sentence-aware chunks with exact offsets in the cleaned source and token checks."""
    if not text.strip(): return []
    budget=max_length-tokenizer.num_special_tokens_to_add(pair=False)
    if budget<8 or not 0<=overlap<budget: raise ValueError('Invalid token budget/overlap')
    encoded=tokenizer(text,add_special_tokens=False,return_offsets_mapping=True)
    offsets=encoded['offset_mapping']; n=len(offsets); chunks=[]; start=0
    ends={m.end() for m in sentences(text)}
    token_ends=[b for _,b in offsets]
    sentence_stops=[]
    for end in sorted(ends):
        j=bisect_right(token_ends,end)
        if j and offsets[j-1][1]<=end<=(offsets[j][0] if j<n else len(text)):
            sentence_stops.append(j)
    while start<n:
        stop=min(start+budget,n)
        if stop<n:
            boundary=bisect_right(sentence_stops,stop)-1
            if boundary>=0 and sentence_stops[boundary]>=start+max(1,budget//2):
                stop=sentence_stops[boundary]
        lo,hi=offsets[start][0],offsets[stop-1][1]
        piece=text[lo:hi]
        count=len(tokenizer.encode(piece,add_special_tokens=True))
        while count>max_length and stop>start+1:
            stop-=1; hi=offsets[stop-1][1]; piece=text[lo:hi]; count=len(tokenizer.encode(piece,add_special_tokens=True))
        if count>max_length: raise ValueError('Tokenizer cannot satisfy chunk budget')
        chunks.append({'doc_id':doc_id,'section':section,'start':lo,'end':hi,'token_start':start,'token_end':stop,'token_count':count,'text':piece})
        if stop==n: break
        start=max(start+1,stop-overlap)
    return chunks
