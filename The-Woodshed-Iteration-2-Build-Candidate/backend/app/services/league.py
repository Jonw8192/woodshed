import asyncio
from app.integrations.sleeper import SleeperClient
from app.domain.league_dna import analyze_dna

class LeagueService:
    def __init__(self,sleeper:SleeperClient,db=None):self.sleeper=sleeper;self.db=db
    async def dna(self,league_id:str):
        chain,picks=await self.sleeper.historical_picks(league_id)
        return {'league_id':league_id,'seasons':[x.get('season') for x in chain],'sample_size':len(picks),'fingerprints':analyze_dna(picks)}
    async def overview(self,league_id:str):
        league,users,rosters=await asyncio.gather(self.sleeper.league(league_id),self.sleeper.users(league_id),self.sleeper.rosters(league_id))
        return {'league':league,'users':users,'rosters':rosters,'persistence':{'configured':bool(self.db and self.db.url),'state':'available' if self.db and self.db.url else 'environment_pending'}}
