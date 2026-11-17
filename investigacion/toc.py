import struct,sys,json
b=open(sys.argv[1],'rb').read()
p=0
def s():
    global p
    n=struct.unpack_from('<I',b,p)[0]; p+=4; v=b[p:p+n].decode('utf8','replace'); p+=n; return v
name=s(); cnt=struct.unpack_from('<I',b,p)[0]; p+=4
ents=[]
for i in range(cnt):
    try:
        n=s(); e=s(); off,c,r,t1,t2=struct.unpack_from('<QQQqq',b,p); p+=40
    except Exception as ex: print('stop',i,ex); break
    ents.append((n,e,off,c,r))
print(name,cnt,'parsed',len(ents),'endpos',p,'of',len(b))
json.dump(ents,open(sys.argv[2],'w'))
import collections,re
g=collections.defaultdict(lambda:[0,0])
for n,e,off,c,r in ents:
    k=re.sub(r'\d+','#',n)+e; g[k][0]+=1; g[k][1]+=r
tot=sum(v[1] for v in g.values())
print('total raw',tot)
for k,v in sorted(g.items(),key=lambda x:-x[1][1]): print(f'{v[1]:>12} {v[0]:>5} {k}')
