from __future__ import annotations
import asyncio,json,time,logging
from typing import Any
try: import redis.asyncio as redis
except Exception: redis=None
log=logging.getLogger(__name__)
class Cache:
    def __init__(self,url:str|None,ttl:int=1800):
        self.ttl=ttl;self._memory={};self._redis=redis.from_url(url,decode_responses=True) if redis and url else None
        self._lock=asyncio.Lock();self._key_locks={};self.degraded=False
    @property
    def redis_client(self): return self._redis
    async def get_json(self,key:str)->Any|None:
        if self._redis:
            try:
                raw=await self._redis.get(key);self.degraded=False;return json.loads(raw) if raw else None
            except Exception as e:self.degraded=True;log.warning('cache_redis_read_failed',extra={'error':type(e).__name__})
        async with self._lock:
            x=self._memory.get(key)
            if not x or x[0]<time.time():self._memory.pop(key,None);return None
            return json.loads(x[1])
    async def set_json(self,key:str,value:Any,ttl:int|None=None):
        raw=json.dumps(value,separators=(',',':'),default=str);exp=ttl or self.ttl
        if self._redis:
            try:await self._redis.set(key,raw,ex=exp);self.degraded=False;return
            except Exception as e:self.degraded=True;log.warning('cache_redis_write_failed',extra={'error':type(e).__name__})
        async with self._lock:self._memory[key]=(time.time()+exp,raw)
    def key_lock(self,key):
        lock=self._key_locks.get(key)
        if lock is None:lock=self._key_locks[key]=asyncio.Lock()
        return _ManagedKeyLock(self,key,lock)
    async def ping(self)->bool:
        if not self._redis:return True
        try:self.degraded=False;return bool(await self._redis.ping())
        except Exception:self.degraded=True;return False
    async def close(self):
        if self._redis:
            try:await self._redis.aclose()
            except Exception:pass
class _ManagedKeyLock:
    def __init__(self,cache,key,lock):self.cache=cache;self.key=key;self.lock=lock
    async def __aenter__(self):await self.lock.acquire();return self.lock
    async def __aexit__(self,*exc):
        self.lock.release()
        if not self.lock.locked() and not getattr(self.lock,'_waiters',None):self.cache._key_locks.pop(self.key,None)
