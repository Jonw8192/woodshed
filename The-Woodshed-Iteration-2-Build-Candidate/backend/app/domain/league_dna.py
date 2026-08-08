from __future__ import annotations
from collections import Counter,defaultdict
from statistics import mean,pstdev
from app.schemas.fantasy import DraftPick

PURPOSES={'startup','rookie','supplemental','veteran','other','unknown'}

def _norm_purpose(v:str)->str:
    x=(v or 'unknown').lower()
    for k in PURPOSES:
        if k in x:return k
    return 'other'

def analyze_dna(picks:list[DraftPick])->list[dict]:
    completed=[p for p in picks if p.draft_status=='complete']
    by_type:dict[str,list[DraftPick]]=defaultdict(list)
    for p in completed: by_type[_norm_purpose(p.draft_purpose)].append(p)
    results=[]
    for purpose,pool in by_type.items():
        league_early=Counter(p.position for p in pool if p.position and (p.round or 99)<=3)
        league_early_total=sum(league_early.values()) or 1
        by_manager:dict[str,list[DraftPick]]=defaultdict(list)
        for p in pool: by_manager[p.manager_id].append(p)
        for mid,rows in by_manager.items():
            seasons=sorted({p.season for p in rows});early=[p for p in rows if (p.round or 99)<=3];firsts=[p for p in rows if p.round==1]
            pos=Counter(p.position for p in early if p.position);first_pos=Counter(p.position for p in firsts if p.position)
            leader,n=pos.most_common(1)[0] if pos else ('',0);rate=n/len(early) if early else 0
            baseline=league_early.get(leader,0)/league_early_total if leader else 0;diff=rate-baseline
            k=8;shrunk=(len(early)*rate+k*baseline)/(len(early)+k) if early else baseline
            tendency=max(0,min(100,shrunk*100));archetype='Balanced Drafter'
            if len(early)>=6 and diff>=.15:
                archetype={'QB':'QB Aggressor','RB':'RB Heavy','WR':'WR Heavy','TE':'TE Aggressor'}.get(leader,'Position Aggressor')
            adp=[p.adp-p.pick_no for p in rows if p.adp is not None and p.pick_no and p.adp_source]
            first_cons=(first_pos.most_common(1)[0][1]/len(firsts)) if firsts else 0
            adp_sd=pstdev(adp) if len(adp)>1 else None
            pred=100*(.7*first_cons+.3*(1/(1+adp_sd/10) if adp_sd is not None else .5))
            evidence=min(100,20+12*len(seasons)+min(35,len(rows)*1.5))
            exploit=max(0,min(100,.5*abs(diff)*100+.3*pred+.2*evidence));avg=mean(adp) if adp else None
            attribution_counts=Counter(p.attribution_quality for p in rows)
            results.append({'manager_id':mid,'manager_name':rows[0].manager_name or mid,'draft_purpose':purpose,
                'draft_mechanics':sorted({p.draft_mechanic for p in rows}),'seasons':seasons,'sample_size':len(rows),'early_sample_size':len(early),
                'archetype':archetype,'dominant_early_position':leader or None,'manager_early_rate':round(rate,3),'league_early_rate':round(baseline,3),
                'room_relative_signal':round(diff*100,1),'tendency_strength':round(tendency,1),'predictability':round(pred,1),
                'evidence_strength':round(evidence,1),'exploitability':round(exploit,1),'favorite_nfl_team':None,
                'favorite_team_status':'unavailable_without_historical_team_at_event','adp_delta':round(avg,1) if avg is not None else None,
                'market_style':('reaches' if avg and avg>3 else 'falls' if avg and avg<-3 else 'near market') if avg is not None else 'unavailable',
                'data_coverage':{'historical_team':False,'historical_adp':bool(adp),'attribution':dict(attribution_counts)}})
    return sorted(results,key=lambda x:x['exploitability'],reverse=True)
