from __future__ import annotations
import asyncio,random,logging,httpx
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
from app.core.cache import Cache
from app.schemas.fantasy import DraftPick
log=logging.getLogger(__name__)
class SleeperError(RuntimeError): code='upstream_error'
class SleeperNotFound(SleeperError): code='not_found'
class SleeperRateLimited(SleeperError): code='rate_limited'
class SleeperUnavailable(SleeperError): code='unavailable'
class SleeperMalformed(SleeperError): code='malformed_response'

def _retry_after(value:str|None,default=.5)->float:
    if not value:return default
    try:return max(0,float(value))
    except ValueError:
        try:
            dt=parsedate_to_datetime(value)
            if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
            return max(0,(dt-datetime.now(timezone.utc)).total_seconds())
        except Exception:return default

def _draft_purpose(d:dict)->str:
    meta=d.get('metadata') or {};text=' '.join(str(x) for x in [meta.get('name'),meta.get('description'),meta.get('type'),d.get('name')] if x).lower()
    for purpose in ('rookie','startup','supplemental','veteran'):
        if purpose in text:return purpose
    return 'unknown'

def _draft_mechanic(d:dict)->str:
    raw=str(d.get('type') or 'unknown').lower()
    for x in ('snake','linear','auction'):
        if x in raw:return x
    return 'other' if raw!='unknown' else 'unknown'

class SleeperClient:
    def __init__(self,base_url:str,cache:Cache,client:httpx.AsyncClient,timeout:float=12,concurrency:int=8):
        self.base=base_url.rstrip('/');self.cache=cache;self.client=client;self.timeout=timeout;self.sem=asyncio.Semaphore(concurrency)
    async def _fetch(self,path):
        last=None
        for attempt in range(3):
            try:
                async with self.sem:r=await self.client.get(self.base+path,timeout=self.timeout)
                if r.status_code==404:raise SleeperNotFound('Sleeper resource not found')
                if r.status_code==429:
                    if attempt<2:await asyncio.sleep(min(_retry_after(r.headers.get('Retry-After')),2));continue
                    raise SleeperRateLimited('Sleeper rate limit reached')
                if 500<=r.status_code<600:
                    last=SleeperUnavailable(f'Sleeper upstream {r.status_code}')
                    if attempt<2:await asyncio.sleep(.2*(2**attempt)+random.random()*.1);continue
                    raise last
                r.raise_for_status()
                try:return r.json()
                except Exception as e:raise SleeperMalformed('Sleeper returned invalid JSON') from e
            except (httpx.TimeoutException,httpx.NetworkError) as e:
                last=SleeperUnavailable('Sleeper network timeout/unavailable')
                if attempt<2:await asyncio.sleep(.2*(2**attempt)+random.random()*.1);continue
                raise last from e
            except httpx.HTTPStatusError as e:raise SleeperUnavailable('Sleeper request failed') from e
        raise last or SleeperUnavailable('Sleeper unavailable')
    async def _get(self,path,ttl=300):
        key='sleeper:'+path.replace('/',':');cached=await self.cache.get_json(key)
        if cached is not None:return cached
        async with self.cache.key_lock(key):
            cached=await self.cache.get_json(key)
            if cached is not None:return cached
            data=await self._fetch(path);await self.cache.set_json(key,data,ttl);return data
    async def league(self,lid):return await self._get(f'/league/{lid}')
    async def users(self,lid):return await self._get(f'/league/{lid}/users')
    async def rosters(self,lid):return await self._get(f'/league/{lid}/rosters',120)
    async def drafts(self,lid):return await self._get(f'/league/{lid}/drafts',900)
    async def draft_picks(self,did):return await self._get(f'/draft/{did}/picks',3600)
    async def matchups(self,lid,week):return await self._get(f'/league/{lid}/matchups/{week}',60)
    async def transactions(self,lid,week):return await self._get(f'/league/{lid}/transactions/{week}',60)
    async def state(self):return await self._get('/state/nfl',60)
    async def players(self):
        data=await self._get('/players/nfl',86400)
        if not isinstance(data,dict) or len(data)<1000:raise SleeperMalformed('Sleeper player dataset failed validation')
        return data
    async def ping(self):
        data=await self.state();return isinstance(data,dict)
    async def season_chain(self,lid,max_back=8):
        out=[];seen=set();cur=lid
        while cur and len(out)<max_back and cur not in seen:
            seen.add(cur);lg=await self.league(cur);out.append(lg);cur=lg.get('previous_league_id')
        return out
    async def historical_picks(self,lid):
        chain=await self.season_chain(lid);players=await self.players();allp=[]
        for lg in chain:
            uid_names={u.get('user_id'):u.get('display_name') or u.get('username') or u.get('user_id') for u in await self.users(lg['league_id'])}
            for d in await self.drafts(lg['league_id']):
                if d.get('status')!='complete':continue
                purpose=_draft_purpose(d);mechanic=_draft_mechanic(d)
                for pk in await self.draft_picks(d['draft_id']):
                    pid=pk.get('player_id');meta=players.get(pid,{})
                    picked_by=pk.get('picked_by');roster_id=pk.get('roster_id')
                    allp.append(DraftPick(season=str(d.get('season') or lg.get('season') or ''),manager_id=str(picked_by or f'{lg.get("season","unknown")}:{roster_id or "unknown"}'),
                        manager_name=uid_names.get(picked_by),round=pk.get('round'),pick_no=pk.get('pick_no'),player_id=pid,
                        player_name=meta.get('full_name') or pid,position=meta.get('position') or '',nfl_team_at_event=None,adp=None,adp_source=None,
                        draft_purpose=purpose,draft_mechanic=mechanic,draft_status='complete',roster_id=str(roster_id or '') or None,
                        attribution_quality='provider_reported' if picked_by else 'uncertain'))
        return chain,allp
