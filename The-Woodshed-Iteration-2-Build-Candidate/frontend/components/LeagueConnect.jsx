'use client';
import {useEffect,useState} from 'react';
import {post,get} from '@/lib/api';

export default function LeagueConnect(){
  const[id,setId]=useState('');const[data,setData]=useState(null);const[err,setErr]=useState('');const[busy,setBusy]=useState(false);
  useEffect(()=>{const saved=window.localStorage.getItem('woodshed.league_id');if(saved)setId(saved)},[]);
  async function load(e){e.preventDefault();setBusy(true);setErr('');try{const overview=await get('/league/'+id);const dna=await post('/league/dna',{league_id:id}).catch(()=>null);window.localStorage.setItem('woodshed.league_id',id);setData({overview,dna})}catch(x){setErr(x.message)}finally{setBusy(false)}}
  return <section className="panel"><div className="eyebrow">LEAGUE INTELLIGENCE</div><h2>Connect a Sleeper league</h2><p className="muted">Public league data only. The Woodshed reads settings, rosters and completed draft history; no Sleeper password or token is requested.</p><form className="inline" onSubmit={load}><label className="sr" htmlFor="league">Sleeper league ID</label><input id="league" value={id} onChange={e=>setId(e.target.value.replace(/\D/g,''))} placeholder="Sleeper league ID" required minLength={8}/><button disabled={busy}>{busy?'Loading…':'Analyze League'}</button></form>{err&&<p className="error" role="alert">{err}</p>}{data&&<div className="result"><strong>{data.overview.league?.name||'League loaded'}</strong><p>{data.overview.rosters?.length||0} rosters · {data.dna?.sample_size||0} completed historical picks analyzed</p>{data.dna?.fingerprints?.slice(0,4).map(x=><div className="resultRow" key={x.manager_id+x.draft_purpose}><span>{x.manager_name}</span><b>{x.archetype}</b><small>{x.draft_purpose} · room signal {x.room_relative_signal>0?'+':''}{x.room_relative_signal}% · evidence {x.evidence_strength}</small></div>)}</div>}</section>
}
