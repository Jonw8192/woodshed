from __future__ import annotations
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker,AsyncSession
from app.core.config import Settings
class Database:
    def __init__(self,settings:Settings):
        self.url=settings.database_url;self.engine=create_async_engine(self.url,pool_pre_ping=True,pool_size=5,max_overflow=10) if self.url else None
        self.sessions=async_sessionmaker(self.engine,expire_on_commit=False,class_=AsyncSession) if self.engine else None
    async def ping(self)->bool:
        if not self.engine:return False
        try:
            from sqlalchemy import text
            async with self.engine.connect() as c:await c.execute(text('select 1'))
            return True
        except Exception:return False
    async def close(self):
        if self.engine:await self.engine.dispose()
