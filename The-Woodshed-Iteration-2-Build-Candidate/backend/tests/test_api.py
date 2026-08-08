from fastapi.testclient import TestClient
from app.main import app
from app.domain.scoring import scoring_fingerprint
from app.schemas.fantasy import ScoringSettings

def test_health_and_ready():
 with TestClient(app) as c:
  assert c.get('/live').status_code==200
  assert c.get('/ready').json()['ok'] is True
def test_bad_league_id():
 with TestClient(app) as c:
  r=c.get('/api/v1/league/notanid');assert r.status_code==422
def test_wrong_ros_horizon_returns_422():
 with TestClient(app) as c:
  r=c.post('/api/v1/tools/rankings/ros',json={'projections':[{'projection_mode':'fantasy_points','player_id':'x','name':'X','position':'WR','horizon':'week','median':10,'scoring_fingerprint':scoring_fingerprint(ScoringSettings())}]});assert r.status_code==422
def test_ai_is_protected_by_default():
 with TestClient(app) as c:
  r=c.post('/api/v1/tools/insights/player/ai',json={'player':{'projection_mode':'fantasy_points','player_id':'x','name':'X','position':'WR','horizon':'ros','median':10,'scoring_fingerprint':scoring_fingerprint(ScoringSettings())}});assert r.status_code in {503,401}
def test_guillotine_max_teams_validation():
 with TestClient(app) as c:
  teams=[{'roster_id':str(i),'name':str(i)} for i in range(33)];assert c.post('/api/v1/tools/guillotine/chop',json={'teams':teams}).status_code==422
