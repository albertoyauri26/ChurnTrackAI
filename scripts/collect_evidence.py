"""Record real local HTTP measurements; only the synthetic public demo is used."""
import asyncio
import json
import statistics
import sys
import time
from datetime import datetime,timezone
from pathlib import Path
import httpx
base=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8000'
from urllib.parse import urlparse
local = urlparse(base).hostname in ('127.0.0.1','localhost')
suffix = 'local' if local else 'public'
out=Path('evidence');out.mkdir(exist_ok=True)
measurements={}
with httpx.Client(base_url=base,timeout=70) as client:
    for path,method in [('/health','GET'),('/','GET'),('/api/demo','POST')]:
        times=[]
        for _ in range(5):
            start=time.perf_counter();response=client.request(method,path);response.raise_for_status();times.append((time.perf_counter()-start)*1000)
        measurements[path]={'samples':5,'median_ms':statistics.median(times),'max_ms':max(times),'status':response.status_code}
        if path=='/api/demo':
            (out/f'demo-trace-{suffix}.json').write_text(json.dumps(response.json(),indent=2),encoding='utf-8')
    status=client.get('/health').json()
async def burst(n=6):
    # Six simultaneous 300-client demos. Inference without LLM never yields the event loop, so one worker serves them in sequence.
    async with httpx.AsyncClient(base_url=base,timeout=70) as client:
        async def one():
            start=time.perf_counter();response=await client.post('/api/demo?size=300');return response.status_code,(time.perf_counter()-start)*1000
        results=await asyncio.gather(*[one() for _ in range(n)])
    return {'requests':n,'endpoint':'POST /api/demo?size=300','status_counts':{str(s):sum(x==s for x,_ in results) for s in sorted({x for x,_ in results})},'median_ms':statistics.median(t for _,t in results),'max_ms':max(t for _,t in results)}
concurrency=asyncio.run(burst())
(out/('http-measurements.json' if local else 'http-measurements-public.json')).write_text(json.dumps({'created':datetime.now(timezone.utc).isoformat(),'base_url':base,'scope':'LOCAL HTTP, not public production' if local else 'PUBLIC HTTPS from development computer','measurements':measurements,'concurrency':concurrency,'health':status},indent=2),encoding='utf-8')
print(json.dumps({**measurements,'concurrency':concurrency},indent=2))
