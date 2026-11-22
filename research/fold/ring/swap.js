import {probeFrom} from './engine.js';

const strings={
 ru:['Обмен памятью одной клетки','На выбранном шаге копируем оба кольца и меняем между копиями все восемь весов выбранной клетки. Рисунки остаются прежними. Дальше веса снова обучаются по обычному закону. Каждую копию сравниваем с её собственным ходом без обмена.','Поменять веса и проследить','Выберите шаг до конца пробы.','Клетка','шаг обмена','Следующий бит: без обмена → после обмена','Шаг наблюдения','Без обмена','После обмена','Различаются клетки','ни одной','Строки сверху вниз — клетки 1–13; время идёт слева направо. Цвет показывает, где обмен изменил бит. Черта отмечает выбранный шаг.','История А','История Б','Изменить шаг наблюдения'],
 en:['Swap one cell’s memory','At the selected step, copy both rings and exchange all eight weights of the selected cell between the copies. Keep both patterns intact, then resume learning. Compare each copy with its own run without the swap.','Swap weights and follow the rings','Choose a step before the end of the probe.','Cell','swap step','Next bit: original → swapped','Observation step','Original','After swap','Cells that differ','none','Rows from top to bottom are cells 1–13; time runs left to right. Colour shows where the swap changed a bit. The line marks the selected step.','History A','History B','Change observation step']
};
const get=id=>document.getElementById(id);
function element(tag,text){const el=document.createElement(tag);el.textContent=text;return el;}
function svg(tag,attrs){
 const el=document.createElementNS('http://www.w3.org/2000/svg',tag);
 for(const [key,v] of Object.entries(attrs))el.setAttribute(key,v);
 return el;
}
function compare(words,changed,at){
 const a=words[at],b=changed[at];
 return Array.from(a,(_,i)=>i).filter(i=>a[i]!==b[i]);
}
function heatmap(base,changed,at){
 const width=base.length,height=base[0].length;
 const map=svg('svg',{viewBox:'0 0 '+width+' '+height,preserveAspectRatio:'none','aria-hidden':'true',class:'swap-map'});
 let path='';
 base.forEach((_,t)=>compare(base,changed,t).forEach(i=>{path+='M'+t+' '+i+'h1v1h-1z';}));
 map.append(svg('path',{d:path,fill:'#a54a26'}),svg('line',{x1:at+.5,x2:at+.5,y1:0,y2:height,stroke:'var(--ink)','stroke-width':1,'vector-effect':'non-scaling-stroke'}));
 return map;
}
let saved;
export function swapView(lang,model,settings,memory,words,step,cell){
 const c=strings[lang],btn=get('exchange'),out=get('swap-result'),end=step===model.horizon;
 get('swap-title').textContent=c[0];get('swap-help').textContent=c[1];btn.textContent=end?c[3]:c[2];btn.disabled=end;
 if(saved&&(saved.memory!==memory||saved.step!==step||saved.cell!==cell))saved=null;
 function render(){
  out.replaceChildren();if(!saved)return;
  const {base,changed}=saved;
  out.append(element('p',c[4]+' '+(cell+1)+' · '+c[5]+' '+step),element('p',c[12]));
  const label=element('label',c[7]+' '),tick=element('output',''),slider=document.createElement('input');label.className='step';
  slider.type='range';slider.min=step;slider.max=model.horizon;slider.value=step+saved.at;slider.setAttribute('aria-label',c[15]);label.append(tick,slider);out.append(label);
  const pair=element('div','');pair.className='swap-pair';out.append(pair);
  function draw(){
   pair.replaceChildren();saved.at=Number(slider.value)-step;tick.value=slider.value;
   base.forEach((series,h)=>{
    const after=changed[h],i=saved.at,p=element('article','');
    p.append(element('h4',c[13+h]),element('p',c[6]+': '+series[1][cell]+' → '+after[1][cell]),heatmap(series,after,i));
    const ids=compare(series,after,i).map(j=>j+1);
    for(const [title,val] of [[c[8],series[i]],[c[9],after[i]]]){
     const row=element('div',title+' ');row.append(element('code',val));p.append(row);
    }
    p.append(element('div',c[10]+': '+(ids.join(', ')||c[11])));pair.append(p);
   });
  }
  slider.oninput=draw;draw();
 }
 btn.onclick=()=>{
  const width=model.law.walsh_masks.length,offset=cell*width;
  const base=words.map(series=>series.slice(step));
  const changed=base.map((series,h)=>{
   const weights=memory[h][step].slice();
   weights.set(memory[1-h][step].subarray(offset,offset+width),offset);
   const {trace}=probeFrom(model,{...settings,probe:series[0]},weights,model.horizon-step);
   return [series[0],...trace];
  });
  saved={memory,step,cell,base,changed,at:1};render();
 };
 render();
}
