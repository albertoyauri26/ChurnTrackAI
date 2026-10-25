import asyncio
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field, PrivateAttr
from .schemas import AnalysisRequest, Message, Prediction, Recommendation, LLMResponse
from .llm import ProviderError, explain_error
from .analytics import portfolio

log = logging.getLogger('churntrackai.agents')

def now():
    return datetime.now(timezone.utc).isoformat()

ACTIONS = {
    'contact': ('Programar contacto preventivo', ['probability']),
    'monitor': ('Mantener seguimiento comercial', ['probability']),
    'reactivate': ('Consultar necesidades y proponer reactivación', ['dias_ultima_compra']),
    'claims': ('Revisar los reclamos registrados con el ejecutivo', ['reclamos']),
    'payments': ('Revisar pagos atrasados y evaluar alternativas', ['pagos_atrasados']),
    'review_data': ('Validar datos fuera del dominio antes de actuar', ['probability']),
}

PLANS = {
    'contact': ('Ejecutivo comercial', ['Revisar el historial de compras y contacto.', 'Consultar necesidades y registrar la respuesta del cliente.'], 'Contacto registrado y siguiente paso acordado.'),
    'monitor': ('Analista comercial', ['Revisar indicadores en el siguiente corte.', 'Comparar la frecuencia de compra con su historial.'], 'Nueva revisión registrada; no asumir retención lograda.'),
    'reactivate': ('Ejecutivo comercial', ['Comprobar la fecha de la última compra.', 'Consultar si existen necesidades pendientes sin asumir el motivo de la inactividad.'], 'Respuesta del cliente y oportunidad confirmada, si corresponde.'),
    'claims': ('Atención al cliente', ['Revisar el estado y detalle de los reclamos.', 'Acordar un responsable y verificar la resolución con el cliente.'], 'Estado de cada reclamo actualizado y validado.'),
    'payments': ('Cobranza y ejecutivo comercial', ['Validar vencimientos y posibles errores de registro.', 'Conversar sobre alternativas autorizadas por la empresa.'], 'Situación de pagos verificada y acuerdo documentado, si existe.'),
    'review_data': ('Responsable de datos', ['Contrastar los valores con la fuente original.', 'Corregir errores o validar un modelo adecuado antes de decidir.'], 'Datos validados; no actuar basándose en una extrapolación.'),
}

def rule_action(p):
    options = allowed(p)
    if p.warnings or p.risk == 'BAJO':
        return options[0]
    feature_action = {'dias_ultima_compra':'reactivate','reclamos':'claims','pagos_atrasados':'payments'}
    for factor in p.factors:
        action = feature_action.get(factor.feature)
        if factor.delta_probability > 0 and action in options:
            return action
    return options[0]

def allowed(p):
    if p.warnings:
        return ['review_data']
    choices = ['monitor'] if p.risk == 'BAJO' else ['contact']
    if p.observed['dias_ultima_compra'] >= 60:
        choices.append('reactivate')
    if p.observed['reclamos'] >= 3:
        choices.append('claims')
    if p.observed['pagos_atrasados'] >= 2:
        choices.append('payments')
    return choices

class SharedState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created: str = Field(default_factory=now)
    status: str = 'running'
    predictions: list[Prediction] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    trace: list[Message] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    usage: list[dict] = Field(default_factory=list)
    llm_attempts: list[dict] = Field(default_factory=list)
    mode: str = 'rules'
    agent_llm: dict = Field(default_factory=dict)
    _listener: object = PrivateAttr(default=None)

    def send(self, sender, recipient, tool, payload, status='ok'):
        if len(self.trace) >= 32:
            raise RuntimeError('MAX_STEPS')
        self.trace.append(Message(sequence=len(self.trace)+1, timestamp=now(), sender=sender, recipient=recipient, tool=tool, status=status, payload=payload))
        if self._listener:
            self._listener(self.trace[-1])

async def review_stage(stage, request, state, provider, store):
    report = {'status':'not_called','checked_indices':[],'choices':[]}
    state.agent_llm[stage] = report
    if not request.use_llm or not provider.key or not hasattr(provider,'review'):
        report['reason'] = 'Sin solicitud, configuración o herramienta de revisión LLM.'
        return
    if not store.reserve_call(int(os.getenv('LLM_DAILY_LIMIT','50'))):
        report['reason'] = 'Presupuesto diario agotado.'
        state.warnings.append(f'{stage}: sin cuota LLM; se conservan controles deterministas.')
        return
    indices = sorted(range(len(state.predictions)),key=lambda i:-state.predictions[i].probability)[:20]
    payload = []
    for i in indices:
        p = state.predictions[i]
        options = (['review_data'] if p.warnings else ['interpret_risk']) if stage=='predictivo' else ['approve_plan','request_review']
        row = {'index':i,'probability':p.probability,'risk':p.risk,'observed':p.observed,'allowed_actions':options}
        if stage=='supervisor':
            rec = state.recommendations[i]
            row['proposal'] = {'action':rec.action,'evidence':rec.evidence,'steps':rec.steps}
        payload.append(row)
    state.send(stage,'llm',stage+'_llm_request',{'input':payload,'identifiers_removed':True,'provider':getattr(provider,'name','test-provider'),'model':getattr(provider,'model','test-provider')})
    start = time.perf_counter()
    try:
        response, usage = await provider.review(payload,stage)
        response = LLMResponse.model_validate(response.model_dump())
        state.usage.append({**usage,'agent':stage})
        if sorted(c.index for c in response.choices)!=sorted(indices):
            raise ProviderError('INCOMPLETE_CHOICES')
        by_index={r['index']:r for r in payload}
        for c in response.choices:
            if c.action not in by_index[c.index]['allowed_actions'] or not set(c.evidence).issubset({*state.predictions[c.index].observed,'probability'}):
                raise ProviderError('UNSUPPORTED_RECOMMENDATION')
        report.update(status='validated',checked_indices=indices,choices=[c.model_dump() for c in response.choices],usage=usage)
        state.send('llm',stage,stage+'_llm_result',response.model_dump())
        state.llm_attempts.append({'agent':stage,'attempt':1,'status':'validated','elapsed_ms':round((time.perf_counter()-start)*1000,2)})
        if stage=='supervisor' and any(c.action=='request_review' for c in response.choices):
            state.warnings.append('El supervisor LLM solicita revisión humana adicional para algunas propuestas; consulta sus observaciones antes de aceptar.')
    except ProviderError as exc:
        report.update(status='failed',reason=explain_error(str(exc)))
        state.send('llm',stage,stage+'_llm_result',{'error':str(exc)},'error')
        state.llm_attempts.append({'agent':stage,'attempt':1,'status':'failed','code':str(exc),'elapsed_ms':round((time.perf_counter()-start)*1000,2)})
        state.warnings.append(stage+': '+explain_error(str(exc)))
        log.warning('llm_failed agent=%s attempt=1 code=%s elapsed_ms=%.0f', stage, exc, (time.perf_counter()-start)*1000)

class PredictiveAgent:
    def __init__(self, model):
        self.model = model

    def execute(self, request, state):
        # Validation is repeated at the agent boundary, not delegated to the UI.
        request = AnalysisRequest.model_validate(request.model_dump())
        state.predictions = [self.model.predict(c) for c in request.customers]
        state.send('predictivo','supervisor','neural_inference_and_mean_ablation', {'model_sha256':self.model.digest,'outputs':[{'index':i,'probability':p.probability,'risk':p.risk,'factors':[f.model_dump() for f in p.factors[:3]],'out_of_domain':bool(p.warnings)} for i,p in enumerate(state.predictions)]})

class RetentionAgent:
    def __init__(self, provider, store):
        self.provider, self.store = provider, store

    def materialize(self, p, action, source, evidence=None):
        evidence = evidence or ACTIONS[action][1]
        facts = {**p.observed, 'probability':round(p.probability,6)}
        reason = '; '.join(f'{key} = {facts[key]}' for key in evidence)
        owner, steps, check = PLANS[action]
        timeframe = 'Antes de actuar' if p.warnings else {'ALTO':'Propuesta: en 48 horas','MEDIO':'Propuesta: esta semana','BAJO':'Propuesta: próximo corte mensual'}[p.risk]
        return Recommendation(cliente_id=p.cliente_id, action=action, evidence=evidence, rationale=f'{ACTIONS[action][0]}. Evidencia: {reason}. Validar el contexto con una persona.', priority={'ALTO':'URGENTE','MEDIO':'ATENCION','BAJO':'NORMAL'}[p.risk], source=source, owner=owner, steps=steps, timeframe=timeframe, success_check=check)

    async def execute(self, request, state, correction=False):
        selections = None
        if request.use_llm and not correction:
            candidates = sorted(range(len(state.predictions)), key=lambda i: -state.predictions[i].probability)[:20]
            payload = [{'index':i,'probability':p.probability,'risk':p.risk,'observed':p.observed,'allowed_actions':allowed(p)} for i in candidates for p in [state.predictions[i]]]
            if len(state.predictions) > 20:
                state.warnings.append('El LLM se solicita para los 20 clientes de mayor probabilidad; los restantes utilizan reglas explícitas.')
            interpretation={c['index']:c for c in state.agent_llm.get('predictivo',{}).get('choices',[])}
            for row in payload:
                if row['index'] in interpretation: row['predictive_review']=interpretation[row['index']]
            state.send('retencion','llm','structured_selection_request', {'input':payload, 'identifiers_removed':True, 'provider':getattr(self.provider,'name','test-provider'), 'model':getattr(self.provider,'model','test-provider')})
            for attempt in range(2):
                if not self.provider.key:
                    state.warnings.append('LLM no configurado. Se aplicaron reglas explícitas, sin generación LLM.')
                    state.send('retencion','supervisor','llm_unavailable', {'reason':'LLM_NOT_CONFIGURED'},'error')
                    break
                if not self.store.reserve_call(int(os.getenv('LLM_DAILY_LIMIT','50'))):
                    state.warnings.append('Límite diario LLM alcanzado; se aplicaron reglas.')
                    state.send('retencion','supervisor','daily_budget', {'limit_reached':True},'error')
                    break
                try:
                    attempt_start = time.perf_counter()
                    response, usage = await self.provider.choose(payload)
                    response = LLMResponse.model_validate(response.model_dump())
                    state.usage.append({**usage,'agent':'retencion'})
                    ids = [c.index for c in response.choices]
                    if sorted(ids) != sorted(candidates):
                        raise ProviderError('INCOMPLETE_CHOICES')
                    selections = {c.index:c for c in response.choices}
                    for i, choice in selections.items():
                        p = state.predictions[i]
                        if choice.action not in allowed(p) or not set(choice.evidence).issubset({*p.observed,'probability'}) or not set(ACTIONS[choice.action][1]).issubset(choice.evidence):
                            raise ProviderError('UNSUPPORTED_RECOMMENDATION')
                    state.send('llm','retencion','validated_json',response.model_dump())
                    state.llm_attempts.append({'agent':'retencion','attempt':attempt+1,'status':'validated','elapsed_ms':round((time.perf_counter()-attempt_start)*1000,2)})
                    state.mode = 'mixed' if len(state.predictions) > 20 else 'llm'
                    break
                except ProviderError as exc:
                    selections = None
                    state.llm_attempts.append({'agent':'retencion','attempt':attempt+1,'status':'failed','code':str(exc),'elapsed_ms':round((time.perf_counter()-attempt_start)*1000,2)})
                    state.send('llm','retencion','provider_call', {'attempt':attempt+1,'error':str(exc)},'retry' if attempt == 0 else 'error')
                    log.warning('llm_failed agent=retencion attempt=%d code=%s elapsed_ms=%.0f', attempt+1, exc, (time.perf_counter()-attempt_start)*1000)
                    if attempt == 1 or any(x in str(exc) for x in ('HTTP_400','HTTP_401','HTTP_403','HTTP_404','HTTP_429')):
                        state.warnings.append(explain_error(str(exc)))
                        break
                    await asyncio.sleep(0.5)
            if selections is None:
                state.warnings.append('Proveedor LLM falló o devolvió evidencia inválida; se aplicaron reglas.')
        recs = []
        for i, p in enumerate(state.predictions):
            if selections and i in selections:
                choice = selections[i]
                recs.append(self.materialize(p,choice.action,'llm',choice.evidence))
            else:
                recs.append(self.materialize(p, rule_action(p), 'rules'))
        state.recommendations = recs
        state.send('retencion','supervisor','recommendations', {'source':state.mode,'outputs':[{'index':i,'action':r.action,'evidence':r.evidence,'priority':r.priority} for i,r in enumerate(recs)], 'correction':correction})

class SupervisorAgent:
    def __init__(self, model, provider, store):
        self.predictive = PredictiveAgent(model)
        self.retention = RetentionAgent(provider,store)
        self.model, self.store = model, store

    def validate(self, state):
        if len(state.predictions) != len(state.recommendations):
            return False
        for p,r in zip(state.predictions,state.recommendations):
            if r.cliente_id != p.cliente_id or r.action not in allowed(p) or r.priority != {'ALTO':'URGENTE','MEDIO':'ATENCION','BAJO':'NORMAL'}[p.risk] or r.decision != 'pending':
                return False
            if not set(ACTIONS[r.action][1]).issubset(r.evidence) or not set(r.evidence).issubset({*p.observed,'probability'}):
                return False
            if (r.owner, r.steps, r.success_check) != PLANS[r.action]:
                return False
        return True

    async def run(self, request, persist=True, demo=False, listener=None):
        state = SharedState()
        state._listener = listener
        start = time.perf_counter()
        async def workflow():
            state.send('usuario','supervisor','analysis_request', {'customer_count':len(request.customers),'requested_llm':request.use_llm,'demo':demo})
            state.send('supervisor','predictivo','delegate_prediction',{'task':'validate, infer, explain'},'delegated')
            self.predictive.execute(request,state)
            await review_stage('predictivo',request,state,self.retention.provider,self.store)
            state.send('supervisor','retencion','delegate_retention',{'prediction_message':3,'task':'select grounded actions'},'delegated')
            await self.retention.execute(request,state)
            if not self.validate(state):
                state.send('supervisor','retencion','request_correction',{'reason':'inconsistent_recommendations'},'retry')
                state.mode = 'rules'
                await self.retention.execute(request,state,correction=True)
            if not self.validate(state):
                raise RuntimeError('SUPERVISOR_REJECTED')
            await review_stage('supervisor',request,state,self.retention.provider,self.store)
            flagged = [c['index'] for c in state.agent_llm['supervisor'].get('choices',[]) if c['action']=='request_review']
            state.send('supervisor','usuario','validated_report',{'approved_for_human_review':True,'external_actions_executed':0,
                'customers':len(state.predictions),'risk':{r:sum(p.risk==r for p in state.predictions) for r in ('ALTO','MEDIO','BAJO')},
                'llm_recommendations':sum(r.source=='llm' for r in state.recommendations),'flagged_for_review':flagged})
            state.status = 'completed'
        try:
            await asyncio.wait_for(workflow(), timeout=60)
        except (TimeoutError, RuntimeError) as exc:
            state.status = 'failed'
            state.warnings.append('Ejecución interrumpida: '+type(exc).__name__)
            if len(state.trace) < 32:
                state.send('supervisor','usuario','execution_failed', {'error':type(exc).__name__},'error')
        state.agent_llm['retencion'] = {'status':'validated' if any(r.source=='llm' for r in state.recommendations) else 'failed' if any(a.get('agent')=='retencion' for a in state.llm_attempts) else 'not_called','checked_indices':[i for i,r in enumerate(state.recommendations) if r.source=='llm']}
        run = state.model_dump()
        successful = any(r.source=='llm' for r in state.recommendations)
        errors = [a['code'] for a in state.llm_attempts if a.get('code')]
        run['llm_report'] = {
            'requested':request.use_llm,
            'provider':getattr(self.retention.provider,'name','test-provider'),
            'model':getattr(self.retention.provider,'model','test-provider'),
            'api':getattr(self.retention.provider,'api','test-api'),
            'status':'validated' if successful else 'failed' if state.llm_attempts else 'not_called',
            'attempts':state.llm_attempts,
            'message':'El LLM respondió y su selección pasó los controles.' if successful else explain_error(errors[-1]) if errors else 'No se realizó una llamada al LLM. Revisa las advertencias si fue solicitado.',
            'usage':state.usage,
            'identifiers_sent':False,
            'selected_customers':sum(r.source=='llm' for r in state.recommendations),
        }
        for choice in state.agent_llm.get('supervisor',{}).get('choices',[]):
            run['recommendations'][choice['index']]['supervisor_review']=choice
        for choice in state.agent_llm.get('predictivo',{}).get('choices',[]):
            run['predictions'][choice['index']]['llm_interpretation']=choice
        run['analytics'] = portfolio(state.predictions)
        run['agent_report'] = {
            'predictive': {'count':len(state.predictions),'out_of_domain':sum(bool(p.warnings) for p in state.predictions)},
            'retention': {'llm_count':sum(r.source=='llm' for r in state.recommendations),'rules_count':sum(r.source=='rules' for r in state.recommendations),'actions':{action:sum(r.action==action for r in state.recommendations) for action in ACTIONS}},
            'supervisor': {'validated':state.status=='completed','checks':['Correspondencia de clientes','Acciones compatibles con indicadores','Evidencia verificable','Plan de seguimiento y revisión humana'],'corrections':sum(m.tool=='request_correction' for m in state.trace)},
        }
        run.update({'elapsed_ms':round((time.perf_counter()-start)*1000,2),'model_sha256':self.model.digest,'demo':demo,'ephemeral':not persist,'summary':{'customers':len(state.predictions),'high':sum(p.risk=='ALTO' for p in state.predictions),'medium':sum(p.risk=='MEDIO' for p in state.predictions),'low':sum(p.risk=='BAJO' for p in state.predictions)}})
        if persist:
            self.store.save(run)
        return run

