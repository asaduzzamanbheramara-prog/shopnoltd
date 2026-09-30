import React,{useEffect,useState} from 'react'
import {platformApi} from '../lib/platformApi'

export default function ReferralAdmin(){
 const [p,setP]=useState(null),[rewards,setRewards]=useState([]),[saving,setSaving]=useState(false)
 async function load(){try{const [policy,rows]=await Promise.all([platformApi.referralPolicy(),platformApi.referralRewards()]);setP(policy);setRewards(rows)}catch(e){alert(e.message)}}
 useEffect(()=>{load()},[])
 if(!p)return <main style={{padding:32}}>Loading referral settings…</main>
 async function save(){setSaving(true);try{await platformApi.setReferralPolicy(p);await load();alert('Referral policy saved.')}catch(e){alert(e.message)}finally{setSaving(false)}}
 return <main style={{maxWidth:1050,margin:'0 auto',padding:'32px 18px 80px',fontFamily:'system-ui,sans-serif'}}>
  <h1>Referral Rewards</h1><p>Configure the recurring benefit paid to a direct referrer after a referred user's approved task is settled.</p>
  <section style={{padding:20,border:'1px solid #e2e8f0',borderRadius:16,marginBottom:20}}>
   <h2>Policy</h2>
   <label>Mode<select value={p.mode} onChange={e=>setP({...p,mode:e.target.value})}><option value="percent">Percentage of task reward</option><option value="fixed">Fixed amount per completed task</option></select></label>
   <label style={{display:'block',marginTop:12}}>Percentage<input type="number" min="0" max="100" step="0.01" value={p.percent} onChange={e=>setP({...p,percent:e.target.value})}/></label>
   <label style={{display:'block',marginTop:12}}>Fixed amount<input type="number" min="0" step="any" value={p.fixed_amount} onChange={e=>setP({...p,fixed_amount:e.target.value})}/></label>
   <label style={{display:'block',marginTop:12}}>Maximum reward per task (optional)<input type="number" min="0" step="any" value={p.max_amount||''} onChange={e=>setP({...p,max_amount:e.target.value||null})}/></label>
   <label style={{display:'block',marginTop:12}}>Currency<input value={p.currency} onChange={e=>setP({...p,currency:e.target.value.toUpperCase()})}/></label>
   <label style={{display:'block',marginTop:12}}>Fallback referrer ID<input value={p.fallback_referrer_id||'admin_office'} onChange={e=>setP({...p,fallback_referrer_id:e.target.value})}/></label><p style={{fontSize:13,color:'#64748b'}}>If a user has no valid direct or preserved previous referrer, this account receives the referral attribution. Existing direct attribution is never overwritten.</p>
   <label style={{display:'block',marginTop:12}}><input type="checkbox" checked={p.enabled} onChange={e=>setP({...p,enabled:e.target.checked})}/> Enable referral program and recurring rewards</label><label style={{display:'block',marginTop:12}}><input type="checkbox" checked={p.all_users_can_refer} onChange={e=>setP({...p,all_users_can_refer:e.target.checked})}/> Allow all users to be referrers</label><p style={{fontSize:13,color:"#64748b"}}>When enabled, every eligible Shopnoltd user automatically receives a referral code/link and can refer other users. When disabled, only explicitly enabled referrers retain access.</p>
   <button disabled={saving} onClick={save} style={{marginTop:16}}>{saving?'Saving…':'Save policy'}</button>
  </section>
  <section style={{padding:20,border:'1px solid #e2e8f0',borderRadius:16}}>
   <h2>Recent referral settlements</h2>{!rewards.length?<p>No referral settlements yet.</p>:rewards.map(x=><div key={x.id} style={{borderTop:'1px solid #e2e8f0',padding:'10px 0'}}><b>{x.reward_amount} {x.currency}</b> · {x.status} · Referrer {x.referrer_id} · Referred user {x.referred_id}<div><small>Work {x.work_id} · Submission {x.submission_id} · {new Date(x.created_at).toLocaleString()}</small></div></div>)}
  </section>
 </main>
}
