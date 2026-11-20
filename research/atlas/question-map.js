import {element,readJSON} from '/editorial/content.js';
import {programs} from '/research/atlas/programs.js';

const outlet=document.querySelector('#route');
async function start() {
  const [atlas,catalog]=await Promise.all([readJSON('/research/atlas/topics.json'),readJSON('/publications.json')]);
  const program=outlet.dataset.program;
  const {routes,initial}=programs[program];
  const graph=atlas.graphs[program];
  const nodes=new Map(graph.nodes.map(n=>[n.id,n]));
  const papers=new Map(catalog.publications.map(p=>[p.anchor,p]));
  function render(){
    const key=location.hash.slice(1);
    const active=Object.hasOwn(routes,key)?key:initial;
    const route=routes[active];
    document.querySelectorAll('.fork a').forEach(a=>{
      if(a.hash==='#'+active)a.setAttribute('aria-current','true');
      else a.removeAttribute('aria-current');
    });
    const heading=element('h2',route.title);
    const steps=element('ol','','steps');
    for(const [verb,title,body] of route.steps){
      const li=element('li');
      li.append(element('small',verb),element('h3',title),element('p',body));
      steps.append(li);
    }
    outlet.replaceChildren(heading,steps);
    for(const [index,[id,title,result,scope]] of route.cases.entries()){
      const node=nodes.get(id);
      if(!node)continue;
      const panel=element('details');
      panel.open=index===0;
      panel.append(element('summary',title),element('p',result),element('p',scope,'scope'));
      const links=element('div','','references');
      const paper=papers.get(node.paper);
      if(paper){
        const a=element('a',paper.title);
        a.href='/catalog/#'+paper.anchor;
        links.append(element('small','Manuscript'),a);
      }
      const a=element('a','Explore this node in Graphify →');
      a.href='/research/atlas/graph.html?program='+program+'&node='+encodeURIComponent(id);
      links.append(element('small',node.status),a);
      panel.append(links);
      outlet.append(panel);
    }
  }
  render();
  window.addEventListener('hashchange',render);
}
start().catch(()=>{outlet.textContent='The research map could not load. Reload to try again.';});
