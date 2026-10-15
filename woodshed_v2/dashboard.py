"""THE WOODSHED Control Center. Local use. All external publication manual."""
import os,json,tempfile,csv,io
from pathlib import Path
from datetime import date
import streamlit as st
from woodshed.core import connect,import_csv,export_packet,article_draft,save_decision,add_spend,ledger_remaining
from woodshed import editorial,versus,publishing
st.set_page_config(page_title='THE WOODSHED',layout='wide')
st.title('THE WOODSHED')
st.caption('Process Over Hype | Research, FFToday, VERSUS and The Edge Report | Human approval required')
conn=connect(os.getenv('WOODSHED_DB','woodshed.db'));editorial.init(conn);versus.init(conn);publishing.init(conn)
sections=st.tabs(['Overview','Data & Touch Transfer','FAAB','Favorites & Fades','VERSUS','Edge Report','Business','Audit'])
with sections[0]:
    st.subheader('Research Control Center')
    a,b,c=st.columns(3)
    a.metric('Player weeks',conn.execute('SELECT COUNT(*) FROM player_weeks').fetchone()[0]);b.metric('Remaining FAAB',f'${ledger_remaining(conn,2026)}');c.metric('Newsletter issues',conn.execute('SELECT COUNT(*) FROM newsletter_issues').fetchone()[0])
    st.warning('Imported data is not automatically verified. No article or newsletter is published by this app.')
    st.info('Start by importing normalized data, then record your editorial decisions. Provider-specific NFL datasets require verified mapping and source checks.')
with sections[1]:
    st.subheader('Player data and Touch Transfer')
    file=st.file_uploader('Upload normalized player-week CSV',type='csv')
    if file and st.button('Import player data'):
        try:
            with tempfile.NamedTemporaryFile(suffix='.csv',delete=False) as f:f.write(file.getvalue());path=f.name
            n=import_csv(conn,path);Path(path).unlink(missing_ok=True);st.success(f'{n} rows imported')
        except Exception as e:st.error(str(e))
    s,w=st.columns(2);season=int(s.number_input('Season',2020,2100,2026));week=int(w.number_input('NFL week',1,22,6))
    pkt=export_packet(conn,season,week,f'output/research_{season}_{week}.json')
    st.caption(f'{len(pkt["candidates"])} player rows found. Ranking does not substitute for fantasy editorial judgment.')
    for x in pkt['candidates']:
        with st.expander(f'{x["position"]} {x["name"]} | {x["role_signal"]} | ownership {x["eligibility"]}'):
            st.json({'metrics':x['metrics'],'changes':x['delta'],'flags':x['flags'],'source':x['source'],'observation_date':x['source_date']})
            decision=st.selectbox('Status',['pending','reviewed','approved','rejected'],key='d'+x['player_id']);thesis=st.text_area('Your analysis',key='t'+x['player_id']);bid=st.number_input('FAAB bid',0,max(0,pkt['remaining_faab']),0,key='b'+x['player_id'])
            if st.button('Save decision',key='save'+x['player_id']):
                try:save_decision(conn,x['player_id'],season,week,decision,thesis,bid);st.success('Decision saved')
                except Exception as e:st.error(str(e))
    pkt=export_packet(conn,season,week,f'output/research_{season}_{week}.json')
    st.download_button('Download research JSON',json.dumps(pkt,indent=2),file_name='touch_transfer_research.json')
    st.download_button('Download draft',article_draft(pkt),file_name='touch_transfer_draft.md')
with sections[2]:
    st.subheader('Season-long $200 FAAB')
    yr=int(st.number_input('FAAB season',2020,2100,2026));st.metric('Remaining',f'${ledger_remaining(conn,yr)}')
    wk=int(st.number_input('Acquisition week',1,22,6));player=st.text_input('Acquired player');amount=int(st.number_input('Actual spend ($)',0,200,0))
    if st.button('Record spend'):
        try:add_spend(conn,yr,wk,player,amount);st.success('Saved')
        except Exception as e:st.error(str(e))
    st.dataframe([dict(x) for x in conn.execute('SELECT * FROM faab_ledger ORDER BY id DESC')],use_container_width=True)
with sections[3]:
    st.subheader('Favorites & Fades')
    s1,w1=st.columns(2);ss=int(s1.number_input('FF season',2020,2100,2026));ww=int(w1.number_input('FF week',1,22,6))
    away=st.text_input('Away team abbreviation',value='');home=st.text_input('Home team abbreviation',value='');line=st.text_input('Verified line (optional)');total=st.text_input('Verified total (optional)')
    if st.button('Add assigned matchup'):
        try:editorial.add_game(conn,ss,ww,away.upper(),home.upper(),line,total);st.success('Matchup saved')
        except Exception as e:st.error(str(e))
    games=[dict(x) for x in conn.execute('SELECT * FROM ff_games WHERE season=? AND week=?',(ss,ww))]
    if games:
        sel=st.selectbox('Edit game',games,format_func=lambda x:f'{x["away"]} @ {x["home"]} (#{x["id"]})');team=st.selectbox('Offense',[sel['away'],sel['home']]);player_name=st.text_input('Player full name');cat=st.selectbox('Category',editorial.CATEGORIES);analysis=st.text_area('Your analysis');sources=st.text_area('Source URLs / verification notes');verified=st.checkbox('I verified supporting facts');approved=st.checkbox('I approve this analysis')
        if st.button('Save player analysis'):
            try:editorial.upsert_pick(conn,sel['id'],team,player_name,cat,analysis,sources,verified,approved);st.success('Saved')
            except Exception as e:st.error(str(e))
    st.download_button('Download Favorites & Fades draft',editorial.export_favorites(conn,ss,ww),file_name=f'favorites_fades_w{ww}.md')
    st.caption('Only add assigned games. Fill opponent fantasy points allowed from verified sources before sending.')
with sections[4]:
    st.subheader('VERSUS: DFS Showdown')
    name=st.text_input('Slate name');provider=st.selectbox('Provider',['DraftKings','Splash Sports','Other']);cap=int(st.number_input('Contest salary cap',1,1000000,50000));slots=int(st.number_input('Lineup slots',1,20,6));mult=float(st.number_input('Captain salary multiplier',1.0,5.0,1.5,step=.1))
    if st.button('Create/update slate'):
        try:versus.create_slate(conn,name,provider,cap,slots,mult);st.success('Slate stored')
        except Exception as e:st.error(str(e))
    slates=[dict(r) for r in conn.execute('SELECT * FROM dfs_slates ORDER BY id DESC')]
    if slates:
        sel=st.selectbox('Current slate',slates,format_func=lambda x:f'{x["name"]} ({x["provider"]})');pool=st.file_uploader('Upload verified slate salaries: player_id,name,salary,team',type='csv',key='dfsfile')
        if pool and st.button('Import slate pool'):
            try:st.success(f'{versus.import_players(conn,sel["id"],io.StringIO(pool.getvalue().decode("utf-8-sig")))} salaries imported')
            except Exception as e:st.error(str(e))
        players=[dict(x) for x in conn.execute('SELECT * FROM dfs_players WHERE slate_id=? ORDER BY salary DESC',(sel['id'],))]
        if players:
            label=st.text_input('Lineup label (e.g., Jon)');entries=[]
            for i in range(sel['roster_slots']):
                p=st.selectbox(f'{"Captain" if i==0 else "Flex"} #{i+1}',players,format_func=lambda x:f'{x["name"]} (${x["salary"]:,})',key=f'line_{i}')
                entries.append({'player_id':p['player_id'],'slot':'CAPTAIN' if i==0 else 'FLEX'})
            result=versus.validate_lineup(conn,sel['id'],entries);st.json(result)
            notes=st.text_area('Lineup reasoning')
            if st.button('Save valid lineup'):
                try:versus.save_lineup(conn,sel['id'],label,entries,notes);st.success('Saved')
                except Exception as e:st.error(str(e))
        st.download_button('Download VERSUS show notes',versus.showdown_notes(conn,sel['id']),file_name='versus_show_notes.md')
with sections[5]:
    st.subheader('The Edge Report')
    title=st.text_input('Issue title','The Edge Report — Week 6');day=st.date_input('Issue date',date.today());free=st.text_area('Original free analysis',height=180);paid=st.text_area('Original premium analysis',height=120);sources=st.text_area('Licensing / research source review notes');status=st.selectbox('Editorial status',['draft','reviewed','approved'])
    if st.button('Save issue'):
        try:publishing.save_issue(conn,title,str(day),free,paid,sources,status);st.success('Saved; no publication occurred')
        except Exception as e:st.error(str(e))
    issues=[dict(x) for x in conn.execute('SELECT * FROM newsletter_issues ORDER BY issue_date DESC')]
    if issues:
        issue=st.selectbox('Export an issue',issues,format_func=lambda x:f'{x["title"]} [{x["status"]}]');st.download_button('Download newsletter Markdown',publishing.issue_markdown(issue,include_paid=True),file_name='edge_report.md')
    st.caption('Original material only. Platform publishing and subscriber billing are not integrated.')
with sections[6]:
    st.subheader('Business and monetization ledger')
    st.json(publishing.summary(conn))
    day=st.date_input('Transaction date',date.today(),key='txdate');kind=st.selectbox('Transaction type',['subscription','sponsorship','services','affiliate','expense','other']);description=st.text_input('Transaction description');amount=st.number_input('Amount ($; negative for costs)',value=0.0,step=1.0);confirmed=st.checkbox('Confirmed financial transaction')
    if st.button('Save transaction'):
        try:publishing.record_business(conn,str(day),kind,description,amount,confirmed);st.success('Recorded')
        except Exception as e:st.error(str(e))
    st.dataframe([dict(x) for x in conn.execute('SELECT * FROM business_events ORDER BY id DESC')],use_container_width=True)
with sections[7]:
    st.subheader('Audit history')
    st.dataframe([dict(x) for x in conn.execute('SELECT * FROM audit_log ORDER BY id DESC LIMIT 100')],use_container_width=True)
    st.info('No email integration, auto-posting, contest entry, or recurring billing is included. Use the exported drafts for manual review.')
