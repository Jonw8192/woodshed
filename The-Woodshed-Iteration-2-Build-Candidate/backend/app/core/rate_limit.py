from __future__ import annotations
import time
from collections import defaultdict,deque

class RateLimiter:
    def __init__(self,limit:int,redis_client=None):self.limit=limit;self.redis=redis_client;self._local=defaultdict(deque)
    async def allowed(self,key:str)->bool:
        if self.redis:
            bucket=int(time.time()//60);rk=f'rl:{key}:{bucket}'
            try:
                n=await self.redis.incr(rk)
                if n==1:await self.redis.expire(rk,70)
                return n<=self.limit
            except Exception:
                return False
        now=time.time();q=self._local[key]
        while q and q[0]<now-60:q.popleft()
        if len(q)>=self.limit:return False
        q.append(now);return True
