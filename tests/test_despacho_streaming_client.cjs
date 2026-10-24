/* El cliente procesa SSE incremental auténtico incluso cuando se dividen caracteres UTF-8. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../app/private/despacho.js'),'utf8');
const start=source.indexOf('async function streamChatRequest(');
const end=source.indexOf('function mergeItem(',start);
assert(start>=0&&end>start);
const code=source.slice(start,end);

function streamOf(parts){
  return new ReadableStream({start(controller){for(const part of parts)controller.enqueue(part);controller.close();}});
}
const s={client:{auth:{getSession:async()=>({data:{session:{access_token:'test-token'}}})}}};

(async()=>{
  const raw=': ping\n\nevent: status\ndata: {"message":"Analizando"}\n\nevent: delta\ndata: {"text":"María "}\n\nevent: delta\ndata: {"text":"Ñandú"}\n\nevent: done\ndata: {"answer":"María Ñandú"}\n\n';
  const bytes=new TextEncoder().encode(raw);
  let mid=bytes.findIndex((b,i)=>b===0xc3&&bytes[i+1]===0xad);
  const pieces=[bytes.slice(0,mid+1),bytes.slice(mid+1,mid+13),bytes.slice(mid+13)];
  let requests=0;
  const fetchMock=async(url,options)=>{requests++;assert.equal(url,'/api/despacho/chat/stream');assert.equal(options.headers.Authorization,'Bearer test-token');
    return new Response(streamOf(pieces),{status:200,headers:{'Content-Type':'text/event-stream; charset=utf-8'}});};
  const handle=new Function('S','API','fetch','TextDecoder',code+'return streamChatRequest;')(s,'/api/despacho',fetchMock,TextDecoder);
  const events=[];
  await handle({message:'hola'},new AbortController().signal,(type,data)=>events.push([type,data]));
  assert.equal(requests,1);
  assert.deepEqual(events.map(e=>e[0]),['status','delta','delta','done']);
  assert.equal(events[1][1].text,'María ');
  assert.equal(events[2][1].text,'Ñandú');
  assert.equal(events.at(-1)[1].answer,'María Ñandú');

  const noDone=new Function('S','API','fetch','TextDecoder',code+'return streamChatRequest;')(
    s,'/api/despacho',async()=>new Response(streamOf([new TextEncoder().encode('event: delta\ndata: {"text":"Parcial"}\n\n')]),
       {status:200,headers:{'Content-Type':'text/event-stream'}}),TextDecoder);
  await assert.rejects(()=>noDone({message:'hola'},new AbortController().signal,()=>{}),/Se cortó la conexión/);

  const providerError=new Function('S','API','fetch','TextDecoder',code+'return streamChatRequest;')(
    s,'/api/despacho',async()=>new Response(streamOf([new TextEncoder().encode('event: error\ndata: {"message":"Cuota agotada","status":429}\n\n')]),
       {status:200,headers:{'Content-Type':'text/event-stream'}}),TextDecoder);
  await assert.rejects(()=>providerError({message:'hola'},new AbortController().signal,()=>{}),/Cuota agotada/);

  assert(!source.includes('fakeTypingAnimation'));
  console.log('PASS: SSE incremental, unicode, metadatos finales y errores.');
})().catch(error=>{console.error(error);process.exitCode=1;});
