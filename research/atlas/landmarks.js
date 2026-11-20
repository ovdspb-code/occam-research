import {programs} from './programs.js';

export function symbolsFor(nodes,edges,program) {
  const {routes,landmark}=programs[program];
  const anchors=new Map(Object.values(routes).map(r=>[r.cases[0][0],r.title]));
  const topics = new Map(nodes.map(node => [node.id,node.topic]));
  const outside = new Map(nodes.map(node => [node.id,new Set()]));
  for (const [a,b] of edges) {
    if (topics.get(a) !== topics.get(b)) {
      outside.get(a).add(b);
      outside.get(b).add(a);
    }
  }
  const ranking = nodes.map(({id}) => ({
    id, breadth:new Set([...outside.get(id)].map(other => topics.get(other))).size,
    contacts:outside.get(id).size
  })).filter(n => n.breadth >= 2 && !anchors.has(n.id))
    .sort((a,b) => b.breadth-a.breadth || b.contacts-a.contacts || a.id.localeCompare(b.id));
  const bridges = new Map(ranking.slice(0,5).map(n => [n.id,n.breadth]));
  return (node,degree) => {
    if (anchors.has(node.id)) return {shape:'diamond',size:34,borderWidth:3,role:landmark+' · '+anchors.get(node.id)};
    if (bridges.has(node.id)) return {shape:'square',size:19,borderWidth:2,role:'Cross-topic connector · links to '+bridges.get(node.id)+' other topics'};
    return {shape:'dot',size:5+Math.min(Math.sqrt(degree),6),borderWidth:1,role:''};
  };
}
