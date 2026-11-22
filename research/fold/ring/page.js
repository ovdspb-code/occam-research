import {probeFrom} from './engine.js';
import {inspect,firstDifference} from './inspector.js';
import {text} from './text.js';
import {boundaries,rhythm,ring,plot} from './charts.js';
const $=id=>document.getElementById(id);
const query=new URLSearchParams(location.search);
let lang=query.get('lang')==='ru'?'ru':'en',status='pending',origin='archive',busy=false;
let memory,archiveMemory,model,archive,traces,current,defaults,worker;
const t=k=>text[lang][k];
const controls={};
function node(tag,value){const n=document.createElement(tag);n.textContent=value;return n;}
function settings(){return Object.fromEntries(Object.entries(controls).map(([k,el])=>[k,k==='probe'?el.value:Number(el.value)]));}
function replayUrl(s){
 const url=new URL(location.href);url.search='';url.searchParams.set('lang',lang);
 for(const [k,v] of Object.entries(s))url.searchParams.set(k,v);
 return url;
}
function panels(){
 if(!traces)return;
 const step=Number($('step').value);$('tick').value=step;
 const allWords=traces.map(trace=>[current.probe,...trace]);
 const allCounts=allWords.map(words=>words.map(boundaries));
 $('panels').replaceChildren();
 for(const [i,words] of allWords.entries()){
  const counts=allCounts[i],p=node('article','');p.className='panel';
  const name=t('history')+' '+(lang==='ru'?['А','Б'][i]:['A','B'][i]);
  p.append(node('h3',name));
  const diagram=node('div','');diagram.className='diagram';
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 116 116');svg.setAttribute('aria-hidden','true');ring(svg,words[step],Number($('cell').value),i=>{$('cell').value=i;panels();});
  const values=node('div','');values.append(node('code',words[step]),node('div',t('bounds')+' · '+counts[step]));diagram.append(svg,values);p.append(diagram);
  const chart=svg.cloneNode(false);chart.classList.add('line');chart.setAttribute('viewBox','0 0 300 80');plot(chart,counts,step);
  const axis=node('div','');axis.className='axis';axis.append(node('span',t('first')),node('span','0–12 · '+t('bounds')),node('span',t('last')));
  p.append(chart,axis,node('p',t('period')+' · '+(rhythm(counts.slice(1))??t('none'))+' / '+t('word')+' · '+(rhythm(words.slice(1))??t('none'))));
  $('panels').append(p);
 }
 inspect(lang,allWords,step,memory,model.law.walsh_masks,$('panels'));
 const diff=series=>series[0].findIndex((v,i)=>v!==series[1][i]);
 const d=diff(allWords),c=diff(allCounts);
 $('difference').textContent=[d<0?t('same'):t('delta')+' · '+d,c<0?t('sameCounts'):t('countDelta')+' · '+c].join('. ');
 $('output').hidden=false;$('share').href=replayUrl(current);
}
function paint(){
 document.documentElement.lang=lang;document.title=t('title')+' · Occam Research';
 document.querySelectorAll('[data-t]').forEach(n=>{n.textContent=t(n.dataset.t)});
 $('lang').textContent=lang==='ru'?'English':'Русский';$('lang').lang=lang==='ru'?'en':'ru';
 $('status').textContent=status?t(status):'';$('origin').textContent=t(origin);
 $('run').disabled=!model||busy;$('reset').disabled=!model||busy;
 for(const el of Object.values(controls))el.disabled=busy;
 $('settings').setAttribute('aria-busy',String(busy));
 panels();
}
function complete(trace,s,kind){
 traces=trace;current=s;origin=kind;status='';busy=false;
 const first=firstDifference(trace.map(w=>[s.probe,...w]));
 $('step').value=first?.step??0;$('cell').value=first?.cell??0;paint();
}
function run(){
 if(busy||!model)return;
 const s=settings();busy=true;status='busy';paint();
 worker??=new Worker('worker.js',{type:'module'});
 function fail(){busy=false;status='error';worker.terminate();worker=null;paint();}
 worker.onerror=fail;
 worker.onmessage=({data})=>{
  if(data.working)return;
  if(data.error){fail();return;}
  const same=Object.keys(s).every(k=>s[k]===defaults[k]);
  const matches=same&&JSON.stringify(data.trace)===JSON.stringify(archive);
  memory=data.memory;complete(data.trace,s,matches?'verified':'fresh');
 };
 worker.postMessage({model,settings:s});
}
$('lang').onclick=()=>{
 lang=lang==='en'?'ru':'en';const url=new URL(location.href);url.searchParams.set('lang',lang);history.replaceState(null,'',url);paint();
};
$('settings').onsubmit=e=>{e.preventDefault();run();};
$('step').oninput=panels;$('cell').onchange=panels;
$('find-diff').onclick=()=>{const first=firstDifference(traces.map(w=>[current.probe,...w]));if(first){$('step').value=first.step;$('cell').value=first.cell;panels();}};
$('reset').onclick=()=>{
 for(const [k,v] of Object.entries(defaults))controls[k].value=String(v);
 memory=archiveMemory;history.replaceState(null,'','?lang='+lang);complete(archive,{...defaults},'archive');
};
$('settings').onchange=()=>{status='dirty';paint();};
paint();
try{
 const read=async path=>{const r=await fetch(path);if(!r.ok)throw Error();return r.json();};
 [model,archive]=await Promise.all([read('model.json'),read('example.json')]);
 defaults={steps:model.steps,noise:model.noise,eta:model.law.eta,probe:model.probe};
 const choices={steps:[model.cut,500,2000,5000,10000,model.steps],noise:[0,.25,.5,1,2],eta:[0,.005,.01,.02,.04],probe:[model.probe,'1000000000000','1010101010101','0000000000000']};
 for(const [key,options] of Object.entries(choices)){
  const label=node('label',''),title=node('span',t(key)),sel=node('select','');title.dataset.t=key;sel.id=key;
  for(const v of options)sel.add(new Option(String(v),String(v)));
  sel.value=options.map(String).includes(query.get(key))?query.get(key):String(defaults[key]);
  controls[key]=sel;label.append(title,sel);document.querySelector('.fields').append(label);
 }
 const weights=await read('example-weights.json');
 const archivedRuns=weights.map(w=>probeFrom(model,defaults,Float64Array.from(w.flat())));
 if(JSON.stringify(archivedRuns.map(r=>r.trace))!==JSON.stringify(archive))throw Error();
 memory=archiveMemory=archivedRuns.map(r=>r.memory);
 for(let i=0;i<model.law.cells;i++)$('cell').add(new Option(String(i+1),String(i)));
 $('step').max=model.horizon;
 complete(archive,{...defaults},'archive');
 if(Object.keys(defaults).some(k=>query.has(k)))run();
}catch{status='error';paint();}
