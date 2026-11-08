// Outward binary64 localization + Hessian certificate; parameters are positional.
// Build without fast-math / fused contraction. No scientific search is performed.
#include <array>
#include <vector>
#include <iostream>
#include <iomanip>
#include <cmath>
#include <limits>
#include <chrono>
#include <string>
#include <algorithm>
using std::array;
bool invalid=false; long arithmetic_flags=0,nonfinite_flags=0,empty_flags=0;
void flag(double a,double b){
 if(!std::isfinite(a)||!std::isfinite(b))nonfinite_flags++;
 if(a>b)empty_flags++;
 if(!std::isfinite(a)||!std::isfinite(b)||a>b){invalid=true;arithmetic_flags++;}
}
double dn(double a){return std::nextafter(a,-INFINITY);}
double up(double a){return std::nextafter(a,INFINITY);}
struct I{
 double l,h;
 I(double a=0):l(a),h(a){flag(a,a);}
 I(double a,double b):l(a),h(b){flag(a,b);}
};
I operator+(I a,I b){return {dn(a.l+b.l),up(a.h+b.h)};}
I operator-(I a){return {-a.h,-a.l};}
I operator-(I a,I b){return a+-b;}
I operator*(I a,I b){
 array<double,4> q={a.l*b.l,a.l*b.h,a.h*b.l,a.h*b.h};
 return {dn(*std::min_element(q.begin(),q.end())),
         up(*std::max_element(q.begin(),q.end()))};
}
I inv(I a){
 if(a.l<=0&&a.h>=0)return {-INFINITY,INFINITY};
 return {dn(1/a.h),up(1/a.l)};
}
I operator/(I a,I b){return a*inv(b);}
I sq(I a){
 if(a.l<=0&&a.h>=0)return {0,up(std::max(a.l*a.l,a.h*a.h))};
 return {dn(std::min(a.l*a.l,a.h*a.h)),up(std::max(a.l*a.l,a.h*a.h))};
}
I root(I a){return {dn(std::sqrt(std::max(0.,a.l))),up(std::sqrt(a.h))};}
double mag(I a){return std::max(std::abs(a.l),std::abs(a.h));}
double mid(I a){return a.l+(a.h-a.l)/2;}
I rat(std::string a){
 auto j=a.find('/');
 if(j==std::string::npos)return I(std::stod(a));
 return I(std::stod(a.substr(0,j)))/I(std::stod(a.substr(j+1)));
}
struct J{
 I z; array<I,2> g; array<array<I,2>,2> h;
 J(I a=I(0)):z(a){}
 static J variable(I a,int i){J r(a);r.g[i]=I(1);return r;}
};
J operator+(J a,J b){
 J r(a.z+b.z); for(int i=0;i<2;i++){r.g[i]=a.g[i]+b.g[i];
 for(int j=0;j<2;j++)r.h[i][j]=a.h[i][j]+b.h[i][j];}return r;
}
J operator-(J a){
 J r(-a.z);for(int i=0;i<2;i++){r.g[i]=-a.g[i];
 for(int j=0;j<2;j++)r.h[i][j]=-a.h[i][j];}return r;
}
J operator-(J a,J b){return a+-b;}
J operator*(J a,J b){
 J r(a.z*b.z);
 for(int i=0;i<2;i++){r.g[i]=a.g[i]*b.z+a.z*b.g[i];
 for(int j=0;j<2;j++)r.h[i][j]=a.h[i][j]*b.z+
 a.g[i]*b.g[j]+a.g[j]*b.g[i]+a.z*b.h[i][j];}return r;
}
J inv(J a){
 J r(inv(a.z));I a2=sq(a.z),a3=a2*a.z;
 for(int i=0;i<2;i++){r.g[i]=-a.g[i]/a2;
 for(int j=0;j<2;j++)r.h[i][j]=I(2)*a.g[i]*a.g[j]/a3-a.h[i][j]/a2;}
 return r;
}
J operator/(J a,J b){return a*inv(b);}
using V=array<I,3>; using M=array<V,3>;
using JM=array<array<J,3>,3>;
V operator+(V a,V b){for(int i=0;i<3;i++)a[i]=a[i]+b[i];return a;}
V operator-(V a){for(auto &x:a)x=-x;return a;}
V operator-(V a,V b){return a+-b;}
V operator*(I a,V b){for(auto &x:b)x=a*x;return b;}
I dot(V a,V b){I r;for(int i=0;i<3;i++)r=r+a[i]*b[i];return r;}
V mul(M a,V b){V r;for(int i=0;i<3;i++)r[i]=dot(a[i],b);return r;}
I norm(V a){I r;for(auto x:a)r=r+sq(x);return root(r);}
struct Solver{
 M b,r; double eta=INFINITY;
 Solver(M k){
 double a[3][3],q[3][3];
 for(int i=0;i<3;i++)for(int j=0;j<3;j++)a[i][j]=mid(k[i][j]);
 double det=a[0][0]*(a[1][1]*a[2][2]-a[1][2]*a[2][1])
 -a[0][1]*(a[1][0]*a[2][2]-a[1][2]*a[2][0])
 +a[0][2]*(a[1][0]*a[2][1]-a[1][1]*a[2][0]);
 if(!std::isfinite(det)||det==0)return;
 for(int i=0;i<3;i++)for(int j=0;j<3;j++){
 int i1=(j+1)%3,i2=(j+2)%3,j1=(i+1)%3,j2=(i+2)%3;
 q[i][j]=(a[i1][j1]*a[i2][j2]-a[i1][j2]*a[i2][j1])/det;
 r[i][j]=I(q[i][j]);}
 eta=0;
 for(int i=0;i<3;i++){I rowsum;
 for(int j=0;j<3;j++){I v;for(int k0=0;k0<3;k0++)v=v+r[i][k0]*k[k0][j];
 b[i][j]=I(i==j)-v;rowsum=rowsum+I(mag(b[i][j]));}
 eta=std::max(eta,rowsum.h);}
 }
 bool valid(){return !invalid&&std::isfinite(eta)&&eta<1;}
 V solve(V rhs){
 V c=mul(r,rhs),y;
 double cmax=0;for(auto x:c)cmax=std::max(cmax,mag(x));
 double bound=(I(cmax)/(I(1)-I(eta))).h;
 for(auto &x:y)x=I(-bound,bound);
 for(int it=0;it<8;it++){
 V z=c+mul(b,y);
 for(int i=0;i<3;i++)y[i]=I(std::max(y[i].l,z[i].l),std::min(y[i].h,z[i].h));}
 return y;
 }
};
I A,B,P,L,T0,R;
JM matrix(J s,J d){
 J one(I(1)),two(I(2)),three(I(3)),four(I(4));
 J u=(s+d)/two,v=(s-d)/two,p=u*v,H=one+s+s*s-p;
 J f=J(R)/(H*(one+s)*(one+s));JM k;
 k[0][0]=J(A)-f*p*(one+s+three*p);
 k[1][1]=J(B)-f*(p*(one+s)+three*u*u);
 k[2][2]=J(B)-f*(p*(one+s)+three*v*v);
 k[0][1]=k[1][0]=f*p*(one-two*u+v);
 k[0][2]=k[2][0]=f*p*(one+u-two*v);
 k[1][2]=k[2][1]=f*p*(s-two);return k;
}
array<V,3> work(){
 I x=A/I(2),y=B/I(2),z=y,Q=x*y+x*z+y*z,t=x*y*z/Q;
 V f={x,y,z};M k;
 for(int i=0;i<3;i++)for(int j=0;j<3;j++)
 k[i][j]=I(i==j)*(i==0?A:B)-t*I(2*(i==j)-1)-I(3)*t*f[i]*f[j]/Q;
 V a,b;for(int i=0;i<3;i++){a[i]=k[i][1];b[i]=k[i][2];}
 return {a,b,a-b};
}
struct Eval{bool ok=false;I ell;array<I,2> grad;array<array<I,2>,2> hes;};
Eval evaluate(I s,I d,bool hessian){
 Eval e;JM k=matrix(J::variable(s,0),J::variable(d,1));M kz;array<M,2> kg;
 array<array<M,2>,2> kh;
 for(int i=0;i<3;i++)for(int j=0;j<3;j++){
 kz[i][j]=k[i][j].z;
 for(int p=0;p<2;p++){kg[p][i][j]=k[i][j].g[p];
 for(int q=0;q<2;q++)kh[p][q][i][j]=k[i][j].h[p][q];}}
 Solver solve(kz);if(!solve.valid())return e;
 for(V w:work()){
 V u=solve.solve(w);I n=norm(u);if(invalid||n.l<=0||!std::isfinite(n.h))return e;
 e.ell=e.ell+n;array<V,2> du;array<I,2> ip;
 for(int p=0;p<2;p++){du[p]=solve.solve(-mul(kg[p],u));
 ip[p]=dot(u,du[p]);e.grad[p]=e.grad[p]+ip[p]/n;}
 if(hessian)for(int p=0;p<2;p++)for(int q=0;q<2;q++){
 V dd=solve.solve(-mul(kh[p][q],u)-mul(kg[p],du[q])-mul(kg[q],du[p]));
 e.hes[p][q]=e.hes[p][q]+(dot(du[p],du[q])+dot(u,dd))/n-ip[p]*ip[q]/(n*n*n);}
 }
 e.ok=!invalid;return e;
}
struct Box{I s,d;int phase,depth;};
int main(int argc,char **argv){
 if(argc!=14){std::cerr<<"P A B L t0 smax blo bhi dmax boxlimit seconds iterations_unused outputlabel\n";return 2;}
 P=rat(argv[1]);A=rat(argv[2]);B=rat(argv[3]);L=rat(argv[4]);T0=rat(argv[5]);
 R=P-A-I(2)*B;I S=rat(argv[6]),lo=rat(argv[7]),hi=rat(argv[8]),dd=rat(argv[9]);
 int limit=std::stoi(argv[10]);double seconds=std::stod(argv[11]);
 // Outer bounds contain exact rational limits; inner limits are chosen inward.
 double slo=lo.h,shi=hi.l,dhi=dd.l;
 std::vector<Box> q={{{lo.l,hi.h},{-dd.h,dd.h},1,0},{{0,S.h},{0,S.h},0,0}};
 array<long,9> counts={};long processed=0;int maxdepth=0;
 double minss=INFINITY,mindd=INFINITY,mindet=INFINITY;
 auto start=std::chrono::steady_clock::now();
 while(!q.empty()){
 if(processed>=limit||std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()>seconds)break;
 Box b=q.back();q.pop_back();processed++;maxdepth=std::max(maxdepth,b.depth);invalid=false;
 if(b.phase==0){
 if(b.d.l>=b.s.h){counts[0]++;continue;}
 I u=(b.s+b.d)/I(2),v=(b.s-b.d)/I(2),p=u*v,H=I(1)+b.s+b.s*b.s-p;
 I x=R*p/H,y=R*u/H,z=R*v/H,t=x/(I(1)+b.s);
 if(!invalid&&(x.l>A.h||y.l>B.h||z.l>B.h||x.h<=0||z.h<=0||t.h<T0.l)){counts[1]++;continue;}
 if(b.s.l>=slo&&b.s.h<=shi&&b.d.h<=dhi){counts[2]++;continue;}
 }
 Eval e=evaluate(b.s,b.d,b.phase==1);
 if(e.ok&&b.phase==0){
 if(e.ell.l>L.h){counts[3]++;continue;}
 if(e.grad[0].l>0||e.grad[0].h<0){counts[4]++;continue;}
 if(e.grad[1].l>0||e.grad[1].h<0){counts[5]++;continue;}
 }
 if(e.ok&&b.phase==1){
 I determinant=e.hes[0][0]*e.hes[1][1]-sq(e.hes[0][1]);
 if(!invalid&&e.hes[0][0].l>0&&e.hes[1][1].l>0&&determinant.l>0){
 counts[6]++;minss=std::min(minss,e.hes[0][0].l);mindd=std::min(mindd,e.hes[1][1].l);
 mindet=std::min(mindet,determinant.l);continue;}
 }
 if(invalid)counts[8]++;
 if(b.depth>=60){q.push_back(b);break;}
 int axis=(b.s.h-b.s.l> b.d.h-b.d.l)?0:1;I a=axis==0?b.s:b.d;double c=mid(a);
 if(c<=a.l||c>=a.h){q.push_back(b);break;}
 Box r=b;r.depth++;b.depth++;
 if(axis==0){b.s.h=c;r.s.l=c;}else{b.d.h=c;r.d.l=c;}
 q.push_back(r);q.push_back(b);counts[7]++;
 }
 double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
 std::cout<<std::setprecision(17)<<"label "<<argv[13]<<"\nstatus "<<(q.empty()?"PASS":"UNCERTIFIED")
 <<"\nprocessed "<<processed<<"\nleftover "<<q.size()<<"\nmaxdepth "<<maxdepth
 <<"\nelapsed "<<elapsed<<"\ncounts";for(auto n:counts)std::cout<<" "<<n;
 std::cout<<"\nminimum_Hss "<<minss<<"\nminimum_Hdd "<<mindd<<"\nminimum_det "<<mindet<<"\n";
 std::cout<<"arithmetic_flags "<<arithmetic_flags<<"\narguments";
 for(int i=1;i<argc;i++)std::cout<<" "<<argv[i];std::cout<<"\n";
 std::cout<<"nonfinite_flags "<<nonfinite_flags<<"\nempty_flags "<<empty_flags<<"\n";
 return q.empty()?0:1;
}
