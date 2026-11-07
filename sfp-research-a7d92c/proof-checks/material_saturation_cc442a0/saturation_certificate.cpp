// SFP: absence of interior stationary points on the competitive sublevel.
// Author computer-assisted proof; independent review remains required.
// Rigorous conditional on IEEE-754 round-to-nearest and correctly rounded sqrt.
// Compiled without fast math or contraction. No optimization oracle used.
#include <cmath>
#include <cstdio>
#include <vector>
#include <array>
#include <algorithm>
#include <chrono>
#include <limits>
#include <fstream>
#include <cfenv>
#include <cstdlib>
using namespace std;
const double inf=numeric_limits<double>::infinity();
double down(double x){return nextafter(x,-inf);} double up(double x){return nextafter(x,inf);}
struct I {double a,b; I(double x=0):a(x),b(x){if(!isfinite(x))throw 3;} I(double x,double y):a(x),b(y){if(!isfinite(x)||!isfinite(y))throw 3;}};
I operator+(I x,I y){return {down(x.a+y.a),up(x.b+y.b)};} I operator-(I x){return {-x.b,-x.a};} I operator-(I x,I y){return x+-y;}
I operator*(I x,I y){double a=x.a*y.a,b=x.a*y.b,c=x.b*y.a,d=x.b*y.b;return {down(min(min(a,b),min(c,d))),up(max(max(a,b),max(c,d)))};}
I operator/(I x,I y){if(y.a<=0 && y.b>=0)throw 1;return x*I(down(1/y.b),up(1/y.a));}
I rat(double n,double d){return I(n)/I(d);} I sq(I x){double lo=x.a<=0&&x.b>=0?0:down(min(x.a*x.a,x.b*x.b));return {max(0.,lo),up(max(x.a*x.a,x.b*x.b))};}
I root(I x){if(x.b<0)throw 1;return {max(0.,down(sqrt(max(0.,x.a)))),up(sqrt(max(0.,x.b)))};}
double mag(I x){return max(abs(x.a),abs(x.b));} double mid(I x){return x.a+(x.b-x.a)/2;}
using V=array<I,3>;using M=array<V,3>;
V mv(const M&a,const V&b){V z{};for(int i=0;i<3;i++)for(int j=0;j<3;j++)z[i]=z[i]+a[i][j]*b[j];return z;}
I dot(const V&a,const V&b){I s;for(int i=0;i<3;i++)s=s+a[i]*b[i];return s;}
M mul(const M&a,const M&b){M z{};for(int i=0;i<3;i++)for(int j=0;j<3;j++)for(int k=0;k<3;k++)z[i][j]=z[i][j]+a[i][k]*b[k][j];return z;}
// All integer literals in rational constants are exactly representable in binary64.
const V C{rat(1,5100),rat(1,51),rat(1,51)};
const I budget=rat(181901,85000), L=rat(6825559,2000000), tmin=rat(19673,4607252325);
M makeK(V f){I Q=f[0]*f[1]+f[0]*f[2]+f[1]*f[2], t=f[0]*f[1]*f[2]/Q;M k{};for(int i=0;i<3;i++)for(int j=0;j<3;j++)k[i][j]=(i==j?C[i]-I(2)*t:I(0))+t-I(3)*t*f[i]*f[j]/Q;return k;}
M vs{};
struct Box{array<double,3>lo,hi;int dep;};
struct Result{int tag;I ell,der,mass;};
Result eval(const Box&bb){
 V f;for(int i=0;i<3;i++)f[i]=C[i]*I(bb.lo[i],bb.hi[i]);
 I Q=f[0]*f[1]+f[0]*f[2]+f[1]*f[2], t=f[0]*f[1]*f[2]/Q;
 if(t.b<tmin.a)return {2,{},{},{}};
 I mass=C[0]+C[1]+C[2]+f[0]+f[1]+f[2]+f[0]*f[1]/f[2]+f[0]*f[2]/f[1]+f[1]*f[2]/f[0];
 if(mass.a>budget.b)return {1,{},{},mass};
 M k=makeK(f);
 M R{};
 {double a=mid(k[0][0]),b=mid(k[0][1]),c=mid(k[0][2]),d=mid(k[1][1]),e=mid(k[1][2]),ff=mid(k[2][2]);
 double dt=a*(d*ff-e*e)+b*(c*e-b*ff)+c*(b*e-c*d);
 if(dt>0){R={{{I((d*ff-e*e)/dt),I((c*e-b*ff)/dt),I((b*e-c*d)/dt)},{I((c*e-b*ff)/dt),I((a*ff-c*c)/dt),I((b*c-a*e)/dt)},{I((b*e-c*d)/dt),I((b*c-a*e)/dt),I((a*d-b*b)/dt)}}};}
 else for(int i=0;i<3;i++)R[i][i]=I(1/mid(C[i]));}
 M E=mul(R,k);for(int i=0;i<3;i++)for(int j=0;j<3;j++)E[i][j]=I(i==j)-E[i][j];
 M uu{},zz{},rhs{};array<I,3>norms;I ell;
// Conditional enclosure: for every point with ell<=L, each of the three
 // triangle side vectors has norm at most L/2. This is not an unconstrained inverse bound.
 double cap=(L/I(2)).b;
 for(int a=0;a<3;a++){rhs[a]=mv(R,vs[a]);for(int i=0;i<3;i++)uu[a][i]=I(-cap,cap);}
 // Intersections preserve every competitive solution of Ku=v, irrespective
 // of whether the preconditioned fixed-point map is contractive.
 for(int it=0;it<12;it++){
  for(int a=0;a<3;a++)for(int i=0;i<3;i++){
   I ni=rhs[a][i];for(int j=0;j<3;j++)ni=ni+E[i][j]*uu[a][j];
   uu[a][i]={max(uu[a][i].a,ni.a),min(uu[a][i].b,ni.b)};
   if(uu[a][i].a>uu[a][i].b)return {9,{},{},mass};
  }
  // exact u_2=u_0-u_1, including all three implied constraints
  for(int i=0;i<3;i++){
   I z0=uu[1][i]+uu[2][i],z1=uu[0][i]-uu[2][i],z2=uu[0][i]-uu[1][i];
   I zzs[3]={z0,z1,z2};for(int a=0;a<3;a++){uu[a][i]={max(uu[a][i].a,zzs[a].a),min(uu[a][i].b,zzs[a].b)};if(uu[a][i].a>uu[a][i].b)return {9,{},{},mass};}
  }
  ell=I(0);for(int a=0;a<3;a++){I nn;for(I z:uu[a])nn=nn+sq(z);norms[a]=root(nn);ell=ell+norms[a];}
  if(ell.a>L.b)return {3,ell,{},mass};
 }
 // det(K)>0 for physical states; its common positive factor may be omitted in derivative sign tests.
 I aa=k[0][0],bb1=k[0][1],cc=k[0][2],dd=k[1][1],ee=k[1][2],ff=k[2][2];
 M adj{{{dd*ff-sq(ee),cc*ee-bb1*ff,bb1*ee-cc*dd},{cc*ee-bb1*ff,aa*ff-sq(cc),bb1*cc-aa*ee},{bb1*ee-cc*dd,bb1*cc-aa*ee,aa*dd-sq(bb1)}}};
 for(int a=0;a<3;a++)zz[a]=mv(adj,uu[a]);
 V w;for(int i=0;i<3;i++)w[i]=(Q-sq(f[i]))/(f[(i+1)%3]*f[(i+2)%3]);
 I deriv;for(int a=0;a<3;a++){V wu;for(int i=0;i<3;i++)wu[i]=w[i]*uu[a][i];if(norms[a].a<=0)return {0,ell,{},mass};deriv=deriv+dot(zz[a],wu)/norms[a];}
 if(deriv.a>0||deriv.b<0)return {4,ell,deriv,mass};
 // First-order stationarity can be excluded by any coordinate derivative.
 for(int v=0;v<3;v++){
   I dq=C[v]*(f[(v+1)%3]+f[(v+2)%3]);
   I dt=t*(C[v]/f[v]-dq/Q), da=I(3)*(dt/Q-t*dq/sq(Q));
   M dk{};for(int i=0;i<3;i++)for(int j=0;j<3;j++)
     dk[i][j]=(i==j?-I(2)*dt:I(0))+dt-da*f[i]*f[j]-I(3)*t/Q*((i==v?C[v]*f[j]:I(0))+(j==v?f[i]*C[v]:I(0)));
   I gr;for(int a=0;a<3;a++)gr=gr-dot(zz[a],mv(dk,uu[a]))/norms[a];
   if(gr.a>0||gr.b<0)return {5+v,ell,gr,mass};
 }
 return {0,ell,deriv,mass};
}
int main(int argc,char**argv){
 static_assert(numeric_limits<double>::is_iec559 && numeric_limits<double>::digits==53,"IEEE-754 binary64 required");
 if(fegetround()!=FE_TONEAREST){fprintf(stderr,"round-to-nearest required\n");return 3;}
 if(argc>3){fprintf(stderr,"Usage: certificate [max_boxes] [max_seconds]\n");return 3;}
 long long maxnodes=argc>1?atoll(argv[1]):3000000;double maxsec=argc>2?atof(argv[2]):300.;
 if(maxnodes<=0||!(maxsec>0)){fprintf(stderr,"positive limits required\n");return 3;}
 V fr;for(int i=0;i<3;i++)fr[i]=C[i]/I(2);M kr=makeK(fr);
 for(int i=0;i<3;i++){vs[0][i]=kr[i][1];vs[1][i]=kr[i][2];vs[2][i]=kr[i][1]-kr[i][2];}
 Box initial;initial.dep=0;for(int i=0;i<3;i++){initial.lo[i]=(tmin/C[i]).a;initial.hi[i]=1.;}
 vector<Box>todo{initial};
 long long counts[10]={},done=0;int depth=0;auto start=chrono::steady_clock::now();
 bool ok=true;
 while(!todo.empty()&&done<maxnodes){if(done%10000==0&&chrono::duration<double>(chrono::steady_clock::now()-start).count()>maxsec)break;
  Box b=todo.back();todo.pop_back();done++;depth=max(depth,b.dep);
  // Exact symmetry exchanges f2 and f3; exclude only strict exterior of y>=z.
  if(b.hi[1]<b.lo[2]){counts[8]++;continue;}
  Result r;try{r=eval(b);}catch(int ex){fprintf(stderr,"Arithmetic/inclusion error %d\n",ex);ok=false;break;}
  if(r.tag){counts[r.tag]++;continue;}
  // Branching uses only stored floating endpoints, so children cover the parent.
  int j=0;double width=0;for(int i=0;i<3;i++){double w=log(b.hi[i]/b.lo[i]);if(w>width){width=w;j=i;}}
  double md=sqrt(b.lo[j]*b.hi[j]);if(!(md>b.lo[j]&&md<b.hi[j])){ok=false;break;}
  Box a=b,c=b;a.hi[j]=md;c.lo[j]=md;a.dep=c.dep=b.dep+1;todo.push_back(c);todo.push_back(a);
 }
 double sec=chrono::duration<double>(chrono::steady_clock::now()-start).count();
 long long nleaf=0;for(int i=1;i<10;i++)nleaf+=counts[i];
 bool complete=ok&&todo.empty()&&done==2*nleaf-1;
 printf("{\"certified\":%s,\"processed\":%lld,\"pending\":%zu,\"leaves\":%lld,\"max_depth\":%d,\"seconds\":%.9f,\"counts\":[",complete?"true":"false",done,todo.size(),nleaf,depth,sec);
 for(int i=0;i<10;i++)printf("%s%lld",i?",":"",counts[i]);
 printf("],\"from_full_initial_domain\":true,\"resume_used\":false}\n");
 return complete?0:1;
}
