// Noise tables contain PCG64 standard-normal draws followed by packed output flips, in absolute step order.
function makeTransition(model,settings,progress) {
  const {cells:n,walsh_masks:masks,positive_order:order,q}=model.law;
  const width=masks.length, ones=x=>x.toString(2).replace(/0/g,'').length;
  const features=Array.from({length:8},(_,x)=>masks.map(m=>ones(x&m)%2?-1:1));
  const signs=masks.map(m=>ones(m)>=order?1:-1);
  function evolve(word,weights,from,to,stream,probe){
    let next=new Uint8Array(n);
    const raw=new Float64Array(n*width),v=new Float64Array(width),trace=[],memory=[];
    for(let t=from;t<to;t++){
      if(probe)memory.push(weights.slice());
      for(let i=0;i<n;i++){
        const f=features[4*word[(i+n-1)%n]+2*word[i]+word[(i+1)%n]],o=i*width;
        for(let k=0;k<width;k++)v[k]=weights[o+k]*f[k];
        // NumPy's eight-term binary64 pairwise reduction.
        const field=sum(v);
        const y=field+(probe?0:settings.noise*stream.noise[t*n+i])>=0?1:-1;
        next[i]=Number(y<0)^(probe?0:(stream.flips[t]>>i)&1);
        for(let k=0;k<width;k++)raw[o+k]=q*weights[o+k]+settings.eta*y*f[k]*signs[k];
      }
      for(let i=0;i<n;i++)for(let k=0;k<width;k++){
        weights[i*width+k]=(raw[((i+n-1)%n)*width+k]+2*raw[i*width+k]+raw[((i+1)%n)*width+k])/4;
      }
      [word,next]=[next,word];
      if(probe)trace.push(word.join(''));
      if(t%2048===0)progress();
    }
    return {word,weights,trace,memory};
  }
  return evolve;
}
export function probeFrom(model,settings,weights){
  return makeTransition(model,settings,()=>{})(Uint8Array.from(settings.probe),weights,0,model.horizon,null,true);
}
export function simulate(model,buffers,settings,progress=()=>{}){
  const n=model.law.cells,width=model.law.walsh_masks.length;
  const evolve=makeTransition(model,settings,progress);
  const streams=buffers.map(b=>({noise:new Float64Array(b,0,model.steps*n), flips:new Uint16Array(b,model.steps*n*8)}));
  const common=evolve(Uint8Array.from(model.initial),new Float64Array(n*width),0,model.cut,streams[0],false);
  return streams.map(stream=>{
    const s=evolve(common.word.slice(),common.weights.slice(),model.cut,settings.steps,stream,false);
    return probeFrom(model,settings,s.weights);
  });
}

function sum(v){return ((v[0]+v[1])+(v[2]+v[3]))+((v[4]+v[5])+(v[6]+v[7]));}
export function response(weights,cell,input,masks){
  const terms=masks.map((mask,k)=>weights[cell*masks.length+k]*((-1)**((input&mask).toString(2).replace(/0/g,'').length)));
  return sum(terms);
}
