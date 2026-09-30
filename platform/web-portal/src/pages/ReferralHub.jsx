import React, { useEffect, useState } from 'react'
import { platformApi } from '../lib/platformApi'

const card={background:'#fff',border:'1px solid #e2e8f0',borderRadius:16,padding:20,marginBottom:16}
const input={width:'100%',boxSizing:'border-box',padding:11,border:'1px solid #cbd5e1',borderRadius:9,marginTop:6}

export default function ReferralHub(){
  const [data,setData]=useState(null); const [code,setCode]=useState(''); const [busy,setBusy]=useState(false)
  async function load(){try{setData(await platformApi.referralMe())}catch(e){alert(e.message)}}
  useEffect(()=>{load()},[])
  function link(){return window.location.origin+'/register?ref='+data.referral_code}
  async function copy(){if(!data?.referral_code)return; const url=link(); try{await navigator.clipboard.writeText(url);alert('Referral link copied.')}catch{window.prompt('Copy referral link:',url)}}
  async function share(){if(!data?.referral_code)return; const url=link(); try{if(navigator.share)await navigator.share({title:'Join Shopnoltd',text:'Join Shopnoltd with my referral link.',url});else await copy()}catch(e){if(e?.name!=='AbortError')alert(e.message)}}
  async function claim(){setBusy(true);try{await platformApi.claimReferral(code);setCode('');await load();alert('Referral linked successfully.')}catch(e){alert(e.message)}finally{setBusy(false)}}
  if(!data)return <main style={{maxWidth:900,margin:'0 auto',padding:'40px 18px',fontFamily:'system-ui,sans-serif'}}>Loading referrals…</main>
  return <main style={{maxWidth:900,margin:'0 auto',padding:'32px 18px 80px',fontFamily:'system-ui,sans-serif'}}>
    <h1>Refer & Earn</h1><p style={{color:'#64748b'}}>Your referral benefit is earned again when an eligible referred user's task is approved and settled.</p>
    <section style={card}><h2>Your referral link</h2><input readOnly value={link()} style={input}/><div style={{display:'flex',gap:10,flexWrap:'wrap',marginTop:10}}><button onClick={copy}>Copy link</button><button onClick={share}>Share</button></div><p><b>Referral code:</b> {data.referral_code}</p></section>
    <section style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(180px,1fr))',gap:12}}><div style={card}><b>Referred users</b><div style={{fontSize:28}}>{data.referred_users}</div></div><div style={card}><b>Confirmed referral earnings</b><div style={{fontSize:28}}>{data.confirmed_amount}</div></div><div style={card}><b>Pending referral earnings</b><div style={{fontSize:28}}>{data.pending_amount}</div></div></section>
    <section style={card}><h2>Use a referral code</h2><input placeholder="SNO-XXXXXXXXXXXX" value={code} onChange={e=>setCode(e.target.value.toUpperCase())} style={input}/><button disabled={!code||busy} onClick={claim} style={{marginTop:10}}>{busy?'Linking…':'Link referral'}</button></section>
    <section style={card}><h2>Referral earnings history</h2>{!data.rewards?.length?<p>No referral task earnings yet.</p>:data.rewards.map(x=><div key={x.id} style={{borderTop:'1px solid #e2e8f0',padding:'10px 0'}}><b>{x.amount} {x.currency}</b> · {x.status} · Task {x.work_id}<div><small>{new Date(x.created_at).toLocaleString()}</small></div></div>)}</section>
  </main>
}
