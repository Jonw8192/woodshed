from __future__ import annotations
from datetime import datetime,timezone
from sqlalchemy import select
from app.schemas.canonical import SourceStamp,CanonicalLeague,LeagueSettings,CanonicalRoster,SCHEMA_VERSION
from app.data.models import AccountRecord,LeagueRecord,RosterRecord,ManagerRecord


def normalize_sleeper_league(*,account_id:str,league:dict,rosters:list[dict]):
    now=datetime.now(timezone.utc);lid=str(league.get('league_id') or '')
    stamp=SourceStamp(provider='sleeper',source_record_id=lid,observed_at=now,ingested_at=now,schema_version=SCHEMA_VERSION)
    out_league=CanonicalLeague(id=f'sleeper:{lid}',account_id=account_id,provider='sleeper',provider_league_id=lid,name=league.get('name') or lid,season=str(league.get('season') or ''),source=stamp)
    settings=league.get('settings') or {};scoring=league.get('scoring_settings') or {}
    out_settings=LeagueSettings(league_id=out_league.id,roster_positions=league.get('roster_positions') or [],scoring={k:float(v) for k,v in scoring.items() if isinstance(v,(int,float))},waiver_budget=settings.get('waiver_budget'),source=stamp)
    total=settings.get('waiver_budget',100) or 100
    out_rosters=[]
    for r in rosters:
        used=(r.get('settings') or {}).get('waiver_budget_used',0) or 0
        out_rosters.append(CanonicalRoster(id=f'{out_league.id}:roster:{r.get("roster_id")}',league_id=out_league.id,roster_id=str(r.get('roster_id')),players=r.get('players') or [],starters=r.get('starters') or [],faab_left=max(0,total-used),source=stamp))
    return out_league,out_settings,out_rosters

async def persist_import(session,*,account_id:str,league:CanonicalLeague,settings:LeagueSettings,rosters:list[CanonicalRoster]):
    account=await session.get(AccountRecord,account_id)
    if not account:
        account=AccountRecord(id=account_id,status='active',created_at=datetime.now(timezone.utc));session.add(account);await session.flush()
    q=await session.execute(select(LeagueRecord).where(LeagueRecord.account_id==account_id,LeagueRecord.provider=='sleeper',LeagueRecord.provider_league_id==league.provider_league_id));lr=q.scalar_one_or_none()
    if not lr:
        lr=LeagueRecord(account_id=account_id,provider='sleeper',provider_league_id=league.provider_league_id,name=league.name,season=league.season,settings=settings.model_dump(mode='json'),observed_at=league.source.observed_at,schema_version=SCHEMA_VERSION);session.add(lr);await session.flush()
    else:
        lr.name=league.name;lr.season=league.season;lr.settings=settings.model_dump(mode='json');lr.observed_at=league.source.observed_at
    for r in rosters:
        q=await session.execute(select(RosterRecord).where(RosterRecord.league_id==lr.id,RosterRecord.provider_roster_id==r.roster_id));rr=q.scalar_one_or_none()
        if not rr:
            rr=RosterRecord(league_id=lr.id,provider_roster_id=r.roster_id,manager_id=None,players=r.players,starters=r.starters,faab_left=r.faab_left,observed_at=r.source.observed_at);session.add(rr)
        else:
            rr.players=r.players;rr.starters=r.starters;rr.faab_left=r.faab_left;rr.observed_at=r.source.observed_at
    await session.commit();return lr.id
