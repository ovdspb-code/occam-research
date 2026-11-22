import {stableText} from './layout.js';
import {response} from './engine.js';
const copy={
 ru:['Что запомнила клетка?','Выберите клетку на любом кольце или по номеру. Тройка читается слева направо: левый сосед, выбранная клетка, правый сосед. Восемь накопленных весов задают отклик на каждую из восьми возможных троек. При отрицательном отклике следующим значением будет 1, при нуле или положительном — 0.','Клетка','Показать первое расхождение','Тройка одинакова, но знак отклика различается. Поэтому клетка примет разные значения.','Одинаковый вход даёт одинаковое следующее значение на этом шаге.','Входные тройки уже различаются. Сравнить отклики на одинаковый вход можно в таблицах.','Проба закончена. Вернитесь на шаг назад, чтобы увидеть переход.','Все рисунки пробы совпали.','Вход → отклик → следующее значение','Отклик на все восемь троек','Вход','Отклик','Далее'],
 en:['What did this cell remember?','Pick a cell on either ring or select its number. Read the triple as left neighbour, selected cell, right neighbour. Eight learned weights set its response to each of the eight possible triples. A negative response produces 1; zero or a positive response produces 0.','Cell','Show first divergence','The input is identical, but the responses have opposite output signs. The next bits differ.','The same input gives the same next bit at this step.','The input triples already differ. Use the tables to compare responses to an identical input.','The probe has ended. Go back one step to inspect a transition.','All patterns in the probe match.','Input → response → next bit','Responses to all eight triples','Input','Response','Next']
};
const el=id=>document.getElementById(id);
export function firstDifference(words){
 const step=words[0].findIndex((w,i)=>w!==words[1][i]);
 if(step<1)return null;
 return {step:step-1,cell:[...words[0][step]].findIndex((v,i)=>v!==words[1][step][i])};
}
export function describeDifference(lang,words,start=0,swap=false){
 const first=firstDifference(words),end=start+words[0].length-1,ru=lang==='ru';
 if(!first){
  if(swap)return ru?`После обмена все клетки на каждом шаге до конца опыта (шаг ${end}) повторили ход без обмена.`:`After the swap, every cell matched its original run at every step through step ${end}.`;
  return ru?`За весь опыт (шаги 0–${end}) все клетки обоих колец совпали.`:`Both rings matched in every cell throughout the experiment (steps 0–${end}).`;
 }
 const index=first.step+1;
 const [a,b]=words.map(series=>series[index]);
 const changes=Array.from(a, (bit,i)=>bit===b[i]?null:`${i+1} (${bit} → ${b[i]})`).filter(Boolean);
 const key=swap?(ru?'без обмена → после обмена':'original → swapped'):(ru?'А → Б':'A → B');
 return ru?`Первое расхождение на шаге ${start+index}. ${changes.length===1?'Клетка':'Клетки'} ${changes.join(', ')}. Значения: ${key}.`:`First divergence at step ${start+index}. ${changes.length===1?'Cell':'Cells'} ${changes.join(', ')}. Values: ${key}.`;
}
export function inspect(lang,words,step,memory,masks,panels){
 const c=copy[lang],cell=Number(el('cell').value),end=step===words[0].length-1,first=firstDifference(words);
 ['ins-title','ins-help','ins-cell','find-diff'].forEach((id,i)=>el(id).textContent=c[i]);
 el('find-diff').disabled=!first;
 const triples=words.map(series=>{const w=series[step],n=w.length;return w[(cell+n-1)%n]+w[cell]+w[(cell+1)%n];});
 const differs=!end&&words[0][step+1][cell]!==words[1][step+1][cell];
 const message=end?c[7]:(first?'':c[8]+' ')+(triples[0]!==triples[1]?c[6]:differs?c[4]:c[5]);
 stableText(el('ins-state'),message,[...c.slice(4,8),c[8]+' '+c[5]]);
 for(const [i,p] of [...panels.children].entries()){
  const weights=memory[i][step],input=triples[i],value=x=>response(weights,cell,parseInt(x,2),masks);
  const fmt=x=>Number(x.toPrecision(5)).toLocaleString(lang,{maximumSignificantDigits:5});
  const line=document.createElement('div');line.className='cell-readout';line.append(c[9],document.createElement('br'));
  const code=document.createElement('strong');code.textContent=input+' → '+fmt(value(input))+' → '+(end?'—':words[i][step+1][cell]);line.append(code);p.querySelector('.diagram').after(line);
  const d=document.createElement('details'),summary=document.createElement('summary');summary.textContent=c[10];d.append(summary);
  const table=document.createElement('table');for(const [k,row] of [[c[11],c[12],c[13]],...Array.from({length:8},(_,j)=>{const bits=j.toString(2).padStart(3,'0'),score=value(bits);return [bits,fmt(score),Number(score<0)];})].entries()){
   const tr=table.insertRow();if(row[0]===input)tr.className='active-triple';for(const v of row){const td=document.createElement(k?'td':'th');td.textContent=v;tr.append(td);}
  }d.append(table);line.append(d);
 }
}
