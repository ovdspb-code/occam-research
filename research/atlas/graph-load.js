import {symbolsFor} from './landmarks.js';
import {programs} from './programs.js';

const palette = ['#477694','#bb7941','#795e8e','#559688','#a55862','#778742','#976c54','#597ca9','#986f90','#617e74','#aa8552','#66778b','#937855'];
const program = new URLSearchParams(location.search).get('program');
function script(src) {
  return new Promise((resolve,reject) => {
    const el=document.createElement('script');
    el.src=src; el.onload=resolve; el.onerror=reject;
    document.body.append(el);
  });
}
async function load() {
  const response=await fetch('topics.json');
  if (!response.ok) throw Error('Missing graph data');
  const books=await response.json();
  const {nodes,edges}=books.graphs[program];
  const topics=books[program].map(t=>t.name);
  const degrees=new Map(nodes.map(n=>[n.id,0]));
  for(const [from,to] of edges){
    degrees.set(from,degrees.get(from)+1);
    degrees.set(to,degrees.get(to)+1);
  }
  const symbols=symbolsFor(nodes,edges,program);
  document.querySelector('#sfp-key span').textContent='◆ '+programs[program].landmark;
  document.querySelector('#sfp-key').hidden=false;
  window.RAW_NODES=nodes.map(n=>{
    const group=topics.indexOf(n.topic),color=palette[group%palette.length],degree=degrees.get(n.id);
    return {...n,color:{background:color,border:color,highlight:{background:'#f8e6b7',border:color}},
      title:n.label,community:group,community_name:n.topic,degree,size:6+Math.sqrt(degree)*2,font:{size:13,color:'#222222'},...symbols(n,degree)};
  });
  window.RAW_EDGES=edges.map(([from,to,title,inferred])=>({from,to,title:title+(inferred?' (inferred)':''),dashes:inferred,width:1,color:{color:'#81909e',opacity:.55}}));
  window.LEGEND=topics.map((label,cid)=>({label,cid,color:palette[cid%palette.length],count:nodes.filter(n=>n.topic===label).length}));
  await script('graph-network.js');
  await script('graph-controls.js');
  const findings=books.graphs[program].findings;
  if (findings && Object.keys(findings.entries).length) {
    window.atlasFindings=findings;
    await script('findings.js');
  }
  document.querySelector('#stats').textContent=nodes.length+' nodes · '+edges.length+' directed links';
}
load().catch(()=>{document.querySelector('#stats').textContent='Graph unavailable. Reload to try again.';});
