import json,pytest,httpx
from app.core.cache import Cache
from app.integrations.sleeper import SleeperClient,SleeperNotFound,SleeperRateLimited,SleeperMalformed,SleeperUnavailable

def make(handler):
 c=httpx.AsyncClient(transport=httpx.MockTransport(handler));return SleeperClient('https://x',Cache(None),c,timeout=.1,concurrency=2),c
@pytest.mark.asyncio
async def test_404_normalized():
 s,c=make(lambda req:httpx.Response(404,json={}))
 with pytest.raises(SleeperNotFound):await s.league('1')
 await c.aclose()
@pytest.mark.asyncio
async def test_invalid_players_shape_rejected():
 s,c=make(lambda req:httpx.Response(200,json={}))
 with pytest.raises(SleeperMalformed):await s.players()
 await c.aclose()
@pytest.mark.asyncio
async def test_5xx_retries_then_typed_error():
 n={'v':0}
 def h(req):n['v']+=1;return httpx.Response(502,json={})
 s,c=make(h)
 with pytest.raises(SleeperUnavailable):await s.league('1')
 assert n['v']==3;await c.aclose()
@pytest.mark.asyncio
async def test_cache_stampede_coalesces():
 import asyncio
 n={'v':0}
 async def ah(req):pass
 def h(req):n['v']+=1;return httpx.Response(200,json={'league_id':'1'})
 s,c=make(h)
 out=await asyncio.gather(*[s.league('1') for _ in range(8)])
 assert n['v']==1 and len(out)==8;await c.aclose()
