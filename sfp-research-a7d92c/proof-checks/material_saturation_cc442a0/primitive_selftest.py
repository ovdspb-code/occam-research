"""Exact Fraction checks of interval primitives. This is testing, not a formal arithmetic proof."""
import ctypes
import json
import random
import subprocess
import tempfile
from fractions import Fraction as F
from pathlib import Path
root=Path(__file__).resolve().parent
wrapper=r'''
#define main certificate_main
#include "saturation_certificate.cpp"
#undef main
extern "C" int operation(int op,double a,double b,double c,double d,double*out){try{I x(a,b),y(c,d),z;switch(op){case 0:z=x+y;break;case 1:z=x-y;break;case 2:z=x*y;break;case 3:z=x/y;break;case 4:z=sq(x);break;case 5:z=root(x);break;default:return 9;}out[0]=z.a;out[1]=z.b;return 0;}catch(int e){return e;}}
'''
with tempfile.TemporaryDirectory() as temp:
 p=Path(temp);(p/'wrapper.cpp').write_text(wrapper)
 subprocess.run(['g++','-O2','-std=c++17','-ffp-contract=off','-shared','-fPIC','-I',str(root),str(p/'wrapper.cpp'),'-o',str(p/'wrapper.so')],check=True)
 lib=ctypes.CDLL(str(p/'wrapper.so'));fn=lib.operation
 fn.argtypes=[ctypes.c_int]+[ctypes.c_double]*4+[ctypes.POINTER(ctypes.c_double)];fn.restype=ctypes.c_int
 rng=random.Random(20261107);counts=[0]*6
 for j in range(10000):
  a,b=sorted([rng.uniform(-20,20)*10**rng.randrange(-6,4) for _ in range(2)])
  c,d=sorted([rng.uniform(-20,20)*10**rng.randrange(-6,4) for _ in range(2)])
  af,bf,cf,df=map(F.from_float,(a,b,c,d))
  for op in range(6):
   if op==3 and c<=0<=d:continue
   if op==5 and a<0:continue
   out=(ctypes.c_double*2)();rc=fn(op,a,b,c,d,out)
   if rc:raise RuntimeError((rc,op,a,b,c,d))
   lo,hi=map(F.from_float,out)
   if op==0: ll,hh=af+cf,bf+df
   elif op==1: ll,hh=af-df,bf-cf
   elif op==2: vv=[af*cf,af*df,bf*cf,bf*df];ll,hh=min(vv),max(vv)
   elif op==3: vv=[af/cf,af/df,bf/cf,bf/df];ll,hh=min(vv),max(vv)
   elif op==4: ll=0 if a<=0<=b else min(af*af,bf*bf);hh=max(af*af,bf*bf)
   else:
    if not(0<=lo and lo*lo<=af and hi*hi>=bf):raise RuntimeError('sqrt inclusion')
    counts[op]+=1;continue
   if not(lo<=ll<=hh<=hi):raise RuntimeError(('inclusion',op,a,b,c,d))
   counts[op]+=1
record={'seed':20261107,'all_exact_fraction_inclusions_passed':True,'counts_add_sub_mul_div_square_sqrt':counts,'formal_IEEE_or_compiler_verification':False}
print(json.dumps(record,indent=2));(root/'primitive_selftest_result.json').write_text(json.dumps(record,indent=2)+'\n')
