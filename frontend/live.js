'use strict';
// Agent states are derived from trace messages the server streams while it runs; nothing is simulated.
const liveLabels={pending:'Pendiente',running:'Ejecutando',done:'Completado',error:'Error'};
function liveStates(messages){
 const s={supervisor:{state:'running',detail:'Recibe la solicitud y coordina'},predictivo:{state:'pending',detail:'Espera la delegación'},retencion:{state:'pending',detail:'Espera el diagnóstico'}};
 for(const m of messages){
  if(m.tool==='delegate_prediction')s.predictivo.state='running';
  if(m.tool==='delegate_retention'||m.tool==='request_correction'){if(s.predictivo.state==='running')s.predictivo.state='done';s.retencion.state='running';}
  if(m.tool==='recommendations')s.retencion.state='done';
  if(m.tool==='validated_report')s.supervisor.state='done';
  if(m.tool==='execution_failed')Object.values(s).forEach(a=>{if(a.state==='running')a.state='error';});
  const agent=m.sender==='llm'?m.recipient:m.sender==='usuario'?'supervisor':m.sender;
  if(!s[agent])continue;
  s[agent].detail=m.sender==='llm'&&m.status==='error'?'El LLM no devolvió una respuesta válida; continúa con reglas y controles':m.status==='retry'?'Reintenta la consulta al LLM':toolNames[m.tool]||m.tool;
 }
 return s;
}
function renderLive(messages){
 const s=liveStates(messages);
 $('live-agents').innerHTML=['supervisor','predictivo','retencion'].map(k=>`<li class="${s[k].state}"><b>${k==='supervisor'?'Supervisor (orquestador)':agentNames[k]}</b><span>${liveLabels[s[k].state]}</span><small>${esc(s[k].detail)}</small></li>`).join('')+`<li class="count"><small>${messages.length} mensajes recibidos del servidor</small></li>`;
}
async function analyzeLive(path,options){
 if(!$('live-agents'))$('busy').insertAdjacentHTML('beforeend','<ol id="live-agents" class="live-agents" aria-live="polite"></ol>');
 const messages=[];renderLive(messages);
 const headers={...(typeof options.body==='string'?{'Content-Type':'application/json'}:{}),...(apiKey?{Authorization:'Bearer '+apiKey}:{}),...options.headers};
 const lost='Se perdió la conexión durante el análisis. Revisa el historial antes de repetirlo.';
 let response;
 try{response=await fetch(path+(path.includes('?')?'&':'?')+'stream=true',{...options,headers,signal:AbortSignal.timeout(90000)});}catch(e){throw Error('No se pudo conectar. El servidor podría estar despertando; espera un minuto y vuelve a intentarlo.');}
 if(!response.ok){const data=await response.json().catch(()=>({detail:'Respuesta del servidor no válida'}));if(response.status===401){show('settings');if($('private-access'))$('private-access').open=true;}throw Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail||data));}
 const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
 while(true){
  const {value,done}=await reader.read().catch(()=>{throw Error(lost);});
  if(done)throw Error(lost);
  buffer+=decoder.decode(value,{stream:true});
  let cut;
  while((cut=buffer.indexOf('\n\n'))>=0){
   const line=buffer.slice(0,cut);buffer=buffer.slice(cut+2);
   if(!line.startsWith('data: '))continue;
   const event=JSON.parse(line.slice(6));
   if(event.type==='message'){messages.push(event.message);renderLive(messages);}
   else if(event.type==='result')return event.run;
   else throw Error(event.detail);
  }
 }
}
