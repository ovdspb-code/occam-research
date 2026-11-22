import {simulate} from './engine.js';
let streams;
self.onmessage=async ({data:{model,settings}})=>{
 try{
  streams??=Promise.all([0,1].map(async i=>{const r=await fetch('stream-'+i+'.bin');if(!r.ok)throw Error();return r.arrayBuffer();}));
  const trace=simulate(model,await streams,settings,()=>postMessage({working:true}));
  postMessage({trace});
 }catch{streams=null;postMessage({error:true});}
};
