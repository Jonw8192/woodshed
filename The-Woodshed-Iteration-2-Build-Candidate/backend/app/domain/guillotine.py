from __future__ import annotations
import math
import numpy as np
from app.schemas.fantasy import GuillotineRequest

def chop_probabilities(req:GuillotineRequest)->dict:
    rng=np.random.default_rng(req.seed); n=len(req.teams)
    current=np.array([t.current_points for t in req.teams]); means=np.array([t.projected_remaining for t in req.teams]); sd=np.array([t.volatility for t in req.teams])
    rem=np.maximum(0,rng.normal(means,sd,size=(req.simulations,n))); totals=rem+current; lows=np.argmin(totals,axis=1); counts=np.bincount(lows,minlength=n)
    rows=[]
    for i,t in enumerate(req.teams):
        p=counts[i]/req.simulations; se=math.sqrt(max(p*(1-p),0)/req.simulations)
        rows.append({"roster_id":t.roster_id,"name":t.name,"chop_probability":round(p,4),"monte_carlo_se":round(se,4),"current_points":t.current_points,
            "projected_total":round(t.current_points+t.projected_remaining,1),"faab_left":t.faab_left})
    rows.sort(key=lambda x:x['chop_probability'],reverse=True)
    return {"chop_watch":rows,"most_likely_chop":rows[0],"simulations":req.simulations,"seed":req.seed,"assumptions":["independent normal remaining-score distributions","remaining score is truncated at zero"]}
