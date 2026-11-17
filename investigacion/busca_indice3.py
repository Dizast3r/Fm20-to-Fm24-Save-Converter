import numpy as np, pickle, csv, sys, mmap, collections
import fm_tad as T
ls=open('x20rg/player_stats_hist_ls.dat','rb').read(); L,c,t,d0=T.leer(ls)
last=pickle.load(open('psh_last20.pkl','rb'))
offs=[];own=[]
for i,l in enumerate(L):
    for o in l: offs.append(o); own.append(i)
pn,_=T.cab(ls); p=pn+4; lpos=[]
for l in L: lpos.append(p); p+=4+4*len(l)
offs=np.array(offs,dtype=np.int64); own=np.array(own,dtype=np.int64); o_s=np.argsort(offs); offs=offs[o_s]; own=own[o_s]
lt=np.array([t if (y>=2029 and t is not None) else -2 for y,t in last],dtype=np.int64)
idx=np.arange(len(L),dtype=np.int64)
lpos=np.array(lpos,dtype=np.int64)
club={}
for r in csv.DictReader(open('trabajo/fm20.csv',encoding='utf-8-sig')):
    try: club[int(r['id_jugador'])]=int(r['id_club'] or -1)
    except ValueError: pass
ks=np.array(sorted(club),dtype=np.uint32); kc=np.array([club[k] for k in sorted(club)],dtype=np.int64)
for path in sys.argv[1:]:
    f=open(path,'rb'); m=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)
    cnt=collections.Counter(); W=8<<20; D=24
    if len(m)<64: continue
    for al in range(4):
        n=(len(m)-al)//4; a=np.frombuffer(m,dtype=np.uint32,count=n,offset=al)
        for s in range(0,n,W):
            lo=max(0,s-D); hi=min(n,s+W+D); blk=a[lo:hi]
            core=np.arange(s-lo,min(s+W,n)-lo)
            pos=np.searchsorted(ks,blk[core]); pos[pos>=len(ks)]=0
            h=core[ks[pos]==blk[core]]
            if len(h)==0: continue
            cl=kc[np.searchsorted(ks,blk[h])]
            for d in range(-D,D+1):
                if d==0: continue
                j=h+d; ok=(j>=0)&(j<len(blk)); v=blk[j[ok]].astype(np.int64); c2=cl[ok]
                for nm,arr,ownr in (('fila',offs,own),('pos_ls',lpos,idx),('indice',idx,idx)):
                    q=np.searchsorted(arr,v); q[q>=len(arr)]=0; eq=arr[q]==v
                    cnt[(nm,al,d*4)]+=int((eq & (lt[ownr[q]]==c2)).sum())
        pass #print('alin',al,[x for x in cnt.most_common(5)],flush=True)
    print(path,cnt.most_common(8),flush=True)
