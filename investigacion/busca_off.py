import numpy as np, csv, struct, sys, mmap
import fm_tad as T
db, lsf, dtf, csvf, campo, R = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], int(sys.argv[6])
ls=open(lsf,'rb').read(); L,c,t,d0=T.leer(ls); dt=open(dtf,'rb').read(); N=len(L)
pairs=set()
for i,l in enumerate(L):
    for o in l: pairs.add(i*1000000+struct.unpack_from('<I',dt,d0+o+1)[0]%1000000)
pairs=np.array(sorted(pairs),dtype=np.int64)
pb=[];cl=[]
for r in csv.DictReader(open(csvf,encoding='utf-8-sig')):
    try: x=int(r[campo]); y=int(r['id_club']); pb.append(x); cl.append(y)
    except ValueError: pass
pb=np.array(pb,dtype=np.int64); cl=np.array(cl,dtype=np.int64)
f=open(db,'rb'); m=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ); a=np.frombuffer(m,dtype=np.uint8)
res=[]
for d in range(-R,R):
    idx=pb+d
    for w in (2,3,4):
        v=np.zeros(len(pb),dtype=np.int64)
        for k in range(w): v|=a[idx+k].astype(np.int64)<<(8*k)
        ok=v<N; key=v*1000000+cl%1000000
        q=np.searchsorted(pairs,key); q[q>=len(pairs)]=0
        s=int((ok&(pairs[q]==key)).sum())
        if s>20: res.append((s,d,w))
res.sort(reverse=True); print(db,campo,res[:8],flush=True)
