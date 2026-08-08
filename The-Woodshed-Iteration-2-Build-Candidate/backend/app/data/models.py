from __future__ import annotations
from datetime import datetime
from sqlalchemy import String,Integer,Float,DateTime,ForeignKey,UniqueConstraint,Index,JSON,Boolean
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column,relationship
class Base(DeclarativeBase):pass
class AccountRecord(Base):
    __tablename__='accounts';id:Mapped[str]=mapped_column(String(64),primary_key=True);status:Mapped[str]=mapped_column(String(24),default='active');created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
class UserRecord(Base):
    __tablename__='users';id:Mapped[str]=mapped_column(String(64),primary_key=True);account_id:Mapped[str]=mapped_column(ForeignKey('accounts.id',ondelete='CASCADE'),index=True);display_name:Mapped[str|None]=mapped_column(String(160))
class ProviderConnectionRecord(Base):
    __tablename__='provider_connections';id:Mapped[int]=mapped_column(primary_key=True);account_id:Mapped[str]=mapped_column(ForeignKey('accounts.id',ondelete='CASCADE'),index=True);provider:Mapped[str]=mapped_column(String(32));provider_user_id:Mapped[str|None]=mapped_column(String(64));status:Mapped[str]=mapped_column(String(24),default='active')
class LeagueRecord(Base):
    __tablename__='leagues';id:Mapped[int]=mapped_column(primary_key=True);account_id:Mapped[str]=mapped_column(ForeignKey('accounts.id',ondelete='CASCADE'),index=True);provider:Mapped[str]=mapped_column(String(32));provider_league_id:Mapped[str]=mapped_column(String(32),index=True);name:Mapped[str]=mapped_column(String(180));season:Mapped[str]=mapped_column(String(8));settings:Mapped[dict]=mapped_column(JSON);observed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True));schema_version:Mapped[str]=mapped_column(String(16),default='2.0')
    __table_args__=(UniqueConstraint('account_id','provider','provider_league_id',name='uq_account_provider_league'),)
class ManagerRecord(Base):
    __tablename__='manager_identities';id:Mapped[str]=mapped_column(String(96),primary_key=True);account_id:Mapped[str]=mapped_column(ForeignKey('accounts.id',ondelete='CASCADE'),index=True);provider_user_id:Mapped[str|None]=mapped_column(String(64));display_name:Mapped[str|None]=mapped_column(String(160))
class RosterRecord(Base):
    __tablename__='rosters';id:Mapped[int]=mapped_column(primary_key=True);league_id:Mapped[int]=mapped_column(ForeignKey('leagues.id',ondelete='CASCADE'),index=True);provider_roster_id:Mapped[str]=mapped_column(String(32));manager_id:Mapped[str|None]=mapped_column(ForeignKey('manager_identities.id',ondelete='SET NULL'));players:Mapped[list]=mapped_column(JSON);starters:Mapped[list]=mapped_column(JSON);faab_left:Mapped[int|None]=mapped_column(Integer);observed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    __table_args__=(UniqueConstraint('league_id','provider_roster_id',name='uq_league_roster'),)
class LeagueSnapshot(Base):
    __tablename__='league_snapshots';id:Mapped[int]=mapped_column(primary_key=True);provider:Mapped[str]=mapped_column(String(32),default='sleeper');league_id:Mapped[str]=mapped_column(String(32),index=True);season:Mapped[str|None]=mapped_column(String(8));observed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True));schema_version:Mapped[int]=mapped_column(default=2);payload:Mapped[dict]=mapped_column(JSON)
    __table_args__=(UniqueConstraint('provider','league_id','observed_at',name='uq_league_snapshot'),)
class PlayerRecord(Base):
    __tablename__='players';id:Mapped[int]=mapped_column(primary_key=True);provider:Mapped[str]=mapped_column(String(32));provider_player_id:Mapped[str]=mapped_column(String(64));name:Mapped[str]=mapped_column(String(160));position:Mapped[str]=mapped_column(String(12));team:Mapped[str|None]=mapped_column(String(12));observed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True));schema_version:Mapped[int]=mapped_column(default=2)
    __table_args__=(UniqueConstraint('provider','provider_player_id','observed_at',name='uq_player_snapshot'),)
class PlayerTeamHistoryRecord(Base):
    __tablename__='player_team_history';id:Mapped[int]=mapped_column(primary_key=True);player_key:Mapped[str]=mapped_column(String(96),index=True);team:Mapped[str|None]=mapped_column(String(12));effective_at:Mapped[datetime]=mapped_column(DateTime(timezone=True));observed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True));source:Mapped[str]=mapped_column(String(64))
class DraftRecord(Base):
    __tablename__='drafts';id:Mapped[int]=mapped_column(primary_key=True);provider_draft_id:Mapped[str]=mapped_column(String(64),unique=True);league_id:Mapped[str]=mapped_column(String(32),index=True);season:Mapped[str]=mapped_column(String(8));draft_purpose:Mapped[str]=mapped_column(String(32));draft_mechanic:Mapped[str]=mapped_column(String(32));status:Mapped[str]=mapped_column(String(24));observed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
class DraftPickRecord(Base):
    __tablename__='draft_picks';id:Mapped[int]=mapped_column(primary_key=True);provider_draft_id:Mapped[str]=mapped_column(String(64),index=True);pick_no:Mapped[int]=mapped_column();round:Mapped[int|None]=mapped_column();manager_id:Mapped[str]=mapped_column(String(96));roster_id:Mapped[str|None]=mapped_column(String(32));player_id:Mapped[str|None]=mapped_column(String(64));attribution_quality:Mapped[str]=mapped_column(String(24),default='uncertain');observed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    __table_args__=(UniqueConstraint('provider_draft_id','pick_no',name='uq_draft_pick'),)
class TransactionRecord(Base):
    __tablename__='transactions';id:Mapped[int]=mapped_column(primary_key=True);league_id:Mapped[str]=mapped_column(String(32),index=True);provider_transaction_id:Mapped[str]=mapped_column(String(80));week:Mapped[int|None]=mapped_column(Integer);kind:Mapped[str]=mapped_column(String(32));payload:Mapped[dict]=mapped_column(JSON);observed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True));__table_args__=(UniqueConstraint('league_id','provider_transaction_id',name='uq_league_transaction'),)
class ProjectionSnapshot(Base):
    __tablename__='projection_snapshots';id:Mapped[int]=mapped_column(primary_key=True);player_id:Mapped[str]=mapped_column(String(64),index=True);source:Mapped[str]=mapped_column(String(64));horizon:Mapped[str]=mapped_column(String(16));scoring_key:Mapped[str]=mapped_column(String(80));projection_mode:Mapped[str]=mapped_column(String(24),default='fantasy_points');payload:Mapped[dict]=mapped_column(JSON);median:Mapped[float|None]=mapped_column(Float);floor:Mapped[float|None]=mapped_column(Float);ceiling:Mapped[float|None]=mapped_column(Float);observed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True));effective_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True));schema_version:Mapped[int]=mapped_column(default=2)
    __table_args__=(Index('ix_projection_lookup','player_id','horizon','scoring_key','observed_at'),)
class MarketValueSnapshot(Base):
    __tablename__='market_value_snapshots';id:Mapped[int]=mapped_column(primary_key=True);asset_id:Mapped[str]=mapped_column(String(64),index=True);source:Mapped[str]=mapped_column(String(64));format_key:Mapped[str]=mapped_column(String(80));value:Mapped[float]=mapped_column(Float);observed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True));schema_version:Mapped[int]=mapped_column(default=2)
class ADPSnapshot(Base):
    __tablename__='adp_snapshots';id:Mapped[int]=mapped_column(primary_key=True);player_id:Mapped[str]=mapped_column(String(64),index=True);source:Mapped[str]=mapped_column(String(64));format_key:Mapped[str]=mapped_column(String(80));adp:Mapped[float]=mapped_column(Float);observed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
class RankingSnapshot(Base):
    __tablename__='ranking_snapshots';id:Mapped[int]=mapped_column(primary_key=True);player_id:Mapped[str]=mapped_column(String(64),index=True);source:Mapped[str]=mapped_column(String(64));format_key:Mapped[str]=mapped_column(String(80));rank:Mapped[int]=mapped_column(Integer);observed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
class ModelRunRecord(Base):
    __tablename__='model_runs';id:Mapped[str]=mapped_column(String(64),primary_key=True);account_id:Mapped[str]=mapped_column(String(64),index=True);league_id:Mapped[str|None]=mapped_column(String(32),index=True);model_name:Mapped[str]=mapped_column(String(64));model_version:Mapped[str]=mapped_column(String(32));input_hash:Mapped[str]=mapped_column(String(64));scoring_fingerprint:Mapped[str|None]=mapped_column(String(64));seed:Mapped[int|None]=mapped_column(Integer);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
class DataLineageRecord(Base):
    __tablename__='data_lineage';id:Mapped[int]=mapped_column(primary_key=True);model_run_id:Mapped[str]=mapped_column(ForeignKey('model_runs.id',ondelete='CASCADE'),index=True);source_kind:Mapped[str]=mapped_column(String(48));source_id:Mapped[str]=mapped_column(String(96));observed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
class RecommendationRecord(Base):
    __tablename__='recommendations';id:Mapped[int]=mapped_column(primary_key=True);account_id:Mapped[str|None]=mapped_column(String(64),index=True);league_id:Mapped[str|None]=mapped_column(String(32),index=True);model_run_id:Mapped[str|None]=mapped_column(ForeignKey('model_runs.id',ondelete='SET NULL'));kind:Mapped[str]=mapped_column(String(32));model_version:Mapped[str]=mapped_column(String(32));data_version:Mapped[str]=mapped_column(String(64));seed:Mapped[int|None]=mapped_column(Integer);input_hash:Mapped[str]=mapped_column(String(64));output:Mapped[dict]=mapped_column(JSON);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True));quality_state:Mapped[str]=mapped_column(String(24),default='partial')
class FeatureFlag(Base):
    __tablename__='feature_flags';key:Mapped[str]=mapped_column(String(80),primary_key=True);enabled:Mapped[bool]=mapped_column(Boolean,default=False);updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
