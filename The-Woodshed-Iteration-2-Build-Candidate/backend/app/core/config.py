from functools import lru_cache
from pydantic import model_validator
from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
    model_config=SettingsConfigDict(env_file='.env',extra='ignore')
    app_name:str='The Woodshed API'; app_env:str='development'; environment:str='development'; api_prefix:str='/api/v1'
    allowed_origins:str='http://localhost:3000'; sleeper_base_url:str='https://api.sleeper.app/v1'; sleeper_timeout_seconds:float=12
    sleeper_max_concurrency:int=8; sleeper_required:bool=False
    cache_ttl_seconds:int=1800; redis_url:str|None=None; redis_required:bool=False
    database_url:str|None=None; database_required:bool=False
    ai_enabled:bool=False; openai_api_key:str|None=None; openai_model:str='gpt-5-mini'; ai_daily_quota:int=50
    rate_limit_per_minute:int=120; body_limit_bytes:int=1_000_000; trusted_proxy_ips:str='127.0.0.0/8,::1/128,172.16.0.0/12'
    simulation_concurrency:int=2; account_api_keys:str=''
    @property
    def cors_origins(self):return [x.strip() for x in self.allowed_origins.split(',') if x.strip()]
    @property
    def proxies(self):return [x.strip() for x in self.trusted_proxy_ips.split(',') if x.strip()]
    @property
    def accounts(self):
        # dev/test bootstrap format account_id:key,account2:key2. Production should use an external identity provider.
        out={}
        for pair in self.account_api_keys.split(','):
            if ':' in pair:
                account,key=pair.split(':',1);out[key.strip()]=account.strip()
        return out
    @model_validator(mode='after')
    def production_policy(self):
        env=(self.app_env or self.environment).lower()
        if env=='production':
            if self.database_required and not self.database_url: raise ValueError('DATABASE_REQUIRED=true requires DATABASE_URL')
            if self.redis_required and not self.redis_url: raise ValueError('REDIS_REQUIRED=true requires REDIS_URL')
            if self.ai_enabled and not self.openai_api_key: raise ValueError('AI_ENABLED=true requires OPENAI_API_KEY')
            if '*' in self.cors_origins: raise ValueError('wildcard CORS is not allowed in production')
        return self
@lru_cache
def get_settings():return Settings()
