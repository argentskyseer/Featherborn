import json,re
def loads(s):
    out=[];i=0;n=len(s);instr=False
    while i<n:
        c=s[i]
        if instr:
            out.append(c)
            if c=='\\': out.append(s[i+1]); i+=2; continue
            if c=='"': instr=False
            i+=1; continue
        if c=='"': instr=True; out.append(c); i+=1; continue
        if s.startswith('//',i):
            while i<n and s[i]!='\n': i+=1
            continue
        if s.startswith('/*',i):
            i=s.index('*/',i)+2; continue
        out.append(c); i+=1
    t=''.join(out)
    t=re.sub(r',(\s*[\]}])',r'\1',t)
    t=re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_\-]*)(\s*:)',r'\1"\2"\3',t)
    return json.loads(t.lstrip('﻿'))
def load(p): return loads(open(p,encoding='utf-8-sig').read())
