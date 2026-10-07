import React, { useEffect, useMemo, useState } from 'react'
import { platformApi } from '../lib/platformApi'

const card={background:'#fff',border:'1px solid #e2e8f0',borderRadius:16,padding:20,marginBottom:16}
const input={width:'100%',boxSizing:'border-box',padding:11,border:'1px solid #cbd5e1',borderRadius:9,marginTop:6}
const CATEGORIES=[
  {slug:'data-management',label:'Data Management & Research',path:'/profile/data-management'},
  {slug:'interior-business',label:'Business & Interior Design',path:'/profile/interior-business'},
]
function qrUrl(url){return 'https://api.qrserver.com/v1/create-qr-code/?size=320x320&margin=12&data='+encodeURIComponent(url)}
function referralUrl(code, category){const path=category ? CATEGORIES.find(x=>x.slug===category)?.path : '/register'; const u=new URL(path||'/register',window.location.origin); u.searchParams.set('ref',code); if(category)u.searchParams.set('category',category); return u.toString()}

export default function ReferralHub(){
  const [data,setData]=useState(null); const [code,setCode]=useState(''); const [busy,setBusy]=useState(false)
  async function load(){try{setData(await platformApi.referralMe())}catch(e){alert(e.message)}}
  useEffect(()=>{load()},[])
  const userLink=useMemo(()=>data?.referral_code?referralUrl(data.referral_code,null):'', [data?.referral_code])
  async function copy(url){try{await navigator.clipboard.writeText(url);alert('Referral link copied.')}catch{window.prompt('Copy referral link:',url)}}
  async function share(url,title){try{if(navigator.share)await navigator.share({title,text:'Join Shopnoltd through my referral link.',url});else await copy(url)}catch(e){if(e?.name!=='AbortError')alert(e.message)}}
  async function claim(){setBusy(true);try{await platformApi.claimReferral(code);setCode('');await load();alert('Referral linked successfully.')}catch(e){alert(e.message)}finally{setBusy(false)}}
  if(!data)return <main style={{maxWidth:900,margin:'0 auto',padding:40,fontFamily:'system-ui,sans-serif'}}>Loading referrals…</main>
  return <main style={{maxWidth:1000,margin:'0 auto',padding:'32px 18px 80px',fontFamily:'system-ui,sans-serif'}}>
    <h1>Refer & Earn</h1>
    <p style={{color:'#64748b'}}>Each account has one referral code. Admin sharing is separated by customer profile category; normal users have one account referral link.</p>
    {data.is_admin ? <section style={card}>
      <h2>Admin referral links by customer category</h2>
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(280px,1fr))',gap:16}}>
        {CATEGORIES.map(c=>{const url=referralUrl(data.referral_code,c.slug);return <article key={c.slug} style={{border:'1px solid #e2e8f0',borderRadius:14,padding:16}}>
          <h3>{c.label}</h3><input readOnly value={url} style={input}/>
          <div style={{display:'flex',gap:8,flexWrap:'wrap',marginTop:10}}><button onClick={()=>copy(url)}>Copy referral link</button><button onClick={()=>share(url,c.label)}>Share</button></div>
          <img src={qrUrl(url)} alt={'QR code for '+c.label+' referral'} width="220" height="220" style={{display:'block',margin:'16px auto 8px',maxWidth:'100%'}}/>
          <small>QR opens this category profile and preserves Admin referral attribution.</small>
        </article>})}
      </div>
    </section> : <section style={card}>
      <h2>Your referral link</h2><input readOnly value={userLink} style={input}/>
      <div style={{display:'flex',gap:10,flexWrap:'wrap',marginTop:10}}><button onClick={()=>copy(userLink)}>Copy link</button><button onClick={()=>share(userLink,'Join Shopnoltd')}>Share</button></div>
      <img src={qrUrl(userLink)} alt="QR code for your Shopnoltd referral link" width="220" height="220" style={{display:'block',margin:'16px auto 8px',maxWidth:'100%'}}/>
      <p><b>Referral code:</b> {data.referral_code}</p>
    </section>}
    <section style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(180px,1fr))',gap:12}}><div style={card}><b>Referred users</b><div style={{fontSize:28}}>{data.referred_users}</div></div><div style={card}><b>Confirmed referral earnings</b><div style={{fontSize:28}}>{data.confirmed_amount}</div></div><div style={card}><b>Pending referral earnings</b><div style={{fontSize:28}}>{data.pending_amount}</div></div></section>
    <section style={card}><h2>Use a referral code</h2><input placeholder="SNO-XXXXXXXXXXXX" value={code} onChange={e=>setCode(e.target.value.toUpperCase())} style={input}/><button disabled={!code||busy} onClick={claim} style={{marginTop:10}}>{busy?'Linking…':'Link referral'}</button></section>
    <section style={card}><h2>Referral earnings history</h2>{!data.rewards?.length?<p>No referral task earnings yet.</p>:data.rewards.map(x=><div key={x.id} style={{borderTop:'1px solid #e2e8f0',padding:'10px 0'}}><b>{x.amount} {x.currency}</b> · {x.status} · Task {x.work_id}<div><small>{new Date(x.created_at).toLocaleString()}</small></div></div>)}</section>
  </main>
}
