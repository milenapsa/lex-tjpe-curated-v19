import re,time,tempfile,subprocess,urllib.request
from html.parser import HTMLParser
from config import *
CACHE={}
STOP={"de","da","do","das","dos","e","a","o","em","para","por","com","um","uma","no","na","nos","nas","lei","art"}

def fetch(url,accept):
    hit=CACHE.get(url)
    if hit and time.time()-hit[0] < TTL: return hit[1]
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":accept})
    with urllib.request.urlopen(req,timeout=45) as r:data=r.read(30_000_000)
    CACHE[url]=(time.time(),data)
    return data

def pdftext(url):
    data=fetch(url,"application/pdf")
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(data); f.flush()
        return subprocess.check_output(["pdftotext","-layout",f.name,"-"],timeout=90).decode("utf-8","replace")

class Links(HTMLParser):
    def __init__(self): super().__init__(); self.href=None; self.text=[]; self.items=[]
    def handle_starttag(self,t,a):
        if t=="a":
            self.href=dict(a).get("href"); self.text=[]
    def handle_data(self,d):
        if self.href:self.text.append(d)
    def handle_endtag(self,t):
        if t=="a" and self.href:
            txt=" ".join(self.text).strip()
            self.items.append((self.href,txt))
            self.href=None; self.text=[]

def teu_links():
    p=Links(); p.feed(fetch(PAGE,"text/html").decode("utf-8","replace"))
    out={}
    for href,txt in p.items:
        m=re.search(r"(?i)S[úu]mula\s*0*(\d+)",txt)
        if m:
            n=int(m.group(1))
            out[n]={"url":href,"cancelled":"CANCELADA" in txt.upper()}
    return out

def toks(q):
    return [x for x in re.findall(r"[a-z0-9áéíóúâêôãõç]+",q.lower()) if len(x)>2 and x not in STOP]

def pack(source,label,url,n,body,score,kind):
    return {"id":f"{source}:{n}","title":f"{label} {n}","summary":body[:1800],"type":kind,
            "date":"","organization":"Tribunal de Justiça de Pernambuco","source":source,
            "source_label":label,"source_url":url,"official_url":url,"is_official":True,
            "is_synthetic":False,"retrieved_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
            "match_score":score}

def parse_blocks(text,pattern,source,label,url,q,kind,invalid_words=()):
    ms=list(pattern.finditer(text)); qt=toks(q); rows=[];excluded=0
    for i,m in enumerate(ms):
        n=int(m.group(1)); end=ms[i+1].start() if i+1<len(ms) else len(text)
        body=re.sub(r"\s+"," ",text[m.end():end]).strip()
        marker=(m.group(0)+" "+body[:320]).upper()
        if any(w in marker for w in invalid_words):
            excluded+=1; continue
        if len(body)<20: continue
        score=sum(t in body.lower() for t in qt)
        if score and (len(qt)<=1 or score>=min(2,len(qt))):
            rows.append((score,pack(source,label,url,n,body,score,kind)))
    rows.sort(key=lambda z:(-z[0],z[1]["id"]))
    return [r for _,r in rows],excluded

TRIB_HEAD=re.compile(r"(?im)^\s*S[ÚU]MULA\s+(?:N[ºO.]?\s*)?(\d{1,3})\b")
ADMIN_HEAD=re.compile(r"(?im)^\s*ENUNCIADO\s+ADMINISTRATIVO\s+N[ºO.]?\s*(\d{1,3})\s*:")
TEU_HEAD=re.compile(r"(?im)^\s*S[úu]MUla\s+0*(\d{1,3})\b")

def search(q,limit):
    results=[]; proof=[]
    try:
        text=pdftext(TRIBUNAL)
        r,x=parse_blocks(text,TRIB_HEAD,"tjpe_sumulas_tribunal","TJPE — Súmula",TRIBUNAL,q,"sumula_tjpe",("REVOGADA","REVOGADO","CANCELADA","CANCELADO"))
        results+=r[:limit]; proof.append({"source":"tjpe_sumulas_tribunal","status":"ok","count":min(len(r),limit),"invalid_excluded":x,"request_url":TRIBUNAL})
    except Exception as e: proof.append({"source":"tjpe_sumulas_tribunal","status":"error","error_type":type(e).__name__})
    try:
        text=pdftext(ADMIN)
        r,x=parse_blocks(text,ADMIN_HEAD,"tjpe_enunciados_administrativos","TJPE — Enunciado Administrativo",ADMIN,q,"enunciado_administrativo_tjpe",("REVOGADA","REVOGADO","CANCELADA","CANCELADO"))
        results+=r[:limit]; proof.append({"source":"tjpe_enunciados_administrativos","status":"ok","count":min(len(r),limit),"invalid_excluded":x,"request_url":ADMIN})
    except Exception as e: proof.append({"source":"tjpe_enunciados_administrativos","status":"error","error_type":type(e).__name__})
    try:
        links=teu_links(); rows=[]; excluded=0
        for n,meta in links.items():
            if meta["cancelled"] or n==5: excluded+=1; continue
            txt=pdftext(meta["url"])
            m=TEU_HEAD.search(txt)
            body=re.sub(r"\s+"," ",txt[m.end():] if m else txt).strip()
            score=sum(t in body.lower() for t in toks(q))
            if score and (len(toks(q))<=1 or score>=min(2,len(toks(q)))):
                rows.append((score,pack("tjpe_sumulas_teu","TJPE — TEU Súmula",meta["url"],n,body,score,"sumula_teu_tjpe")))
        rows.sort(key=lambda z:(-z[0],z[1]["id"]))
        results += [r for _,r in rows[:limit]]
        proof.append({"source":"tjpe_sumulas_teu","status":"ok","count":min(len(rows),limit),"cancelled_excluded":excluded,"request_url":PAGE})
    except Exception as e: proof.append({"source":"tjpe_sumulas_teu","status":"error","error_type":type(e).__name__})
    return results,proof
