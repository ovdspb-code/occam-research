const ns='http://www.w3.org/2000/svg';
function shape(tag,attributes){
 const node=document.createElementNS(ns,tag);
 for(const [key,v] of Object.entries(attributes))node.setAttribute(key,v);
 return node;
}
export const boundaries=word=>Array.from(word).filter((bit,i)=>bit!==word[(i+1)%word.length]).length;
export function rhythm(series){
 for(let p=1;p<=series.length/2;p++)if(series.slice(-p).every((v,i)=>v===series[series.length-2*p+i]))return p;
 return null;
}
export function ring(svg,word,cell,onPick){
 svg.replaceChildren(shape('circle',{cx:58,cy:58,r:46,fill:'none',stroke:'var(--line)'}));
 for(let i=0;i<word.length;i++){
  const a=i*2*Math.PI/word.length-Math.PI/2;
  const cx=58+46*Math.cos(a),cy=58+46*Math.sin(a);
  if(i===cell)svg.append(shape('circle',{cx,cy,r:10,stroke:'#b75016','stroke-width':2,fill:'none'}));
  const dot=shape('circle',{cx,cy,r:7,stroke:'var(--ink)',fill:word[i]==='1'?'var(--ink)':'var(--paper)'});
  dot.style.cursor='pointer';dot.onclick=()=>onPick(i);svg.append(dot);
 }
}
export function plot(svg,counts,step){
 const X=i=>4+292*i/(counts.length-1),Y=v=>74-v*5.7;
 svg.replaceChildren();
 for(const y of [0,6,12])svg.append(shape('line',{x1:4,x2:296,y1:Y(y),y2:Y(y),stroke:'var(--line)'}));
 svg.append(shape('polyline',{points:counts.map((v,i)=>X(i)+','+Y(v)).join(' '),fill:'none',stroke:'currentColor','stroke-width':1.5}),shape('line',{x1:X(step),x2:X(step),y1:3,y2:76,stroke:'var(--muted)','stroke-dasharray':'2 2'}),shape('circle',{cx:X(step),cy:Y(counts[step]),r:3,fill:'currentColor'}));
}
