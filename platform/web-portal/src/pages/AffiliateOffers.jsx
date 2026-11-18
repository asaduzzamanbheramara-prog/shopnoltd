import React from 'react'
import { Link, useParams } from 'react-router-dom'

const OFFERS = [
 {id:35682,slug:'iphone-18-pro-rewards-us',name:'Rewards US – iPhone 18 Pro',payout:2,category:'Rewards',geo:'United States',trackingUrl:'https://www.af9m8trk.com/ZPC11ES8/UQ711VGP/',description:'Email-submit rewards campaign advertised as an opportunity to get $1,000 towards an iPhone 18 Pro. Reward eligibility and fulfilment are controlled by the advertiser.'},
 {id:35333,slug:'kelly-services-jobs-us',name:'DailyJobs – Kelly Services Jobs',payout:1.30,category:'Jobs',geo:'United States',description:'Email-submit lead campaign associated with Kelly Services job listings. This is not a job offer or a guarantee of employment.'},
 {id:35332,slug:'dollar-tree-jobs-us',name:'JobsListings – Dollar Tree Jobs',payout:2,category:'Jobs',geo:'United States',description:'Email-submit lead campaign associated with Dollar Tree job listings. Verify vacancies and application details with the advertiser.'},
 {id:32421,slug:'ai-jobs-us',name:'DailyJobs – AI Jobs',payout:2,category:'Jobs',geo:'United States',description:'Email-submit lead campaign for AI-related job listings. Openings and hiring decisions are determined by employers.'},
 {id:32419,slug:'fedex-jobs-us',name:'DailyJobs – FedEx Jobs',payout:2,category:'Jobs',geo:'United States',description:'Email-submit lead campaign associated with FedEx job listings. Confirm current openings with the advertiser.'},
 {id:32418,slug:'netflix-jobs-us',name:'DailyJobs – Netflix Jobs',payout:2,category:'Jobs',geo:'United States',description:'Email-submit lead campaign associated with Netflix job listings. It is not an official hiring promise.'},
 {id:31047,slug:'ups-jobs-us',name:'DailyJobs – UPS Jobs',payout:1.30,category:'Jobs',geo:'United States',description:'Email-submit lead campaign associated with UPS job listings. Check openings and requirements on the advertiser page.'},
 {id:30223,slug:'part-time-jobs-us',name:'DailyJobs – Part Time Jobs',payout:2,category:'Jobs',geo:'United States',description:'Email-submit lead campaign for part-time job listings. Availability and requirements are determined by the advertiser.'},
 {id:23038,slug:'housekeeping-jobs-us',name:'JobsListings – Housekeeping Jobs',payout:2.40,category:'Jobs',geo:'United States',description:'Email-submit lead campaign associated with housekeeping job listings. Confirm role details with the advertiser.'},
 {id:22826,slug:'construction-jobs-us',name:'JobsListings – Construction Jobs',payout:2,category:'Jobs',geo:'United States',description:'Email-submit lead campaign associated with construction job listings. The advertiser provides actual vacancy information.'},
 {id:22825,slug:'airport-jobs-us',name:'JobsListings – Airport Jobs',payout:2,category:'Jobs',geo:'United States',description:'Email-submit lead campaign associated with airport job listings. Confirm employers and requirements on the advertiser page.'},
 {id:22103,slug:'amazon-jobs-us',name:'JobsListings – Amazon Jobs',payout:1.30,category:'Jobs',geo:'United States',description:'Email-submit lead campaign associated with Amazon job listings. This campaign does not itself represent an official job offer.'},
 {id:22102,slug:'walmart-work-from-home-us',name:'JobsListings – Walmart Work From Home',payout:1.30,category:'Jobs',geo:'United States',description:'Email-submit lead campaign associated with work-from-home listings. Verify roles and availability before applying.'},
 {id:33617,slug:'costco-100-rewards-us',name:'Rewards US – Costco $100',payout:3,category:'Rewards',geo:'United States',description:'Email-submit rewards campaign advertised with a $100 Costco reward. Terms and fulfilment are controlled by the advertiser.'},
 {id:33616,slug:'paypal-1000-rewards-us',name:'Rewards US – PayPal $1000',payout:3,category:'Rewards',geo:'United States',description:'Email-submit rewards campaign advertised with a $1,000 PayPal reward. The advertised reward is not guaranteed.'},
 {id:33614,slug:'cash-750-rewards-us',name:'Rewards US – Cash $750',payout:3,category:'Rewards',geo:'United States',description:'Email-submit rewards campaign advertised with a $750 cash reward. Eligibility is controlled by the advertiser.'},
 {id:34909,slug:'grocery-750-rewards-us',name:'Rewards US – Grocery $750',payout:2,category:'Rewards',geo:'United States',description:'Email-submit rewards campaign advertised with a $750 grocery reward. Review the advertiser terms.'}
 {id:27283,slug:'costco-750-rewards-us',name:'UpLevelRewards – Costco $750',payout:2.50,category:'Rewards',geo:'United States',previewUrl:'https://www.uplevelrewards.com/?Flow=6b51d955-0748-462e-9eb5-0ccdd7eceb37&isPrePop=true&RBC=1&reward=costco750&bckm=1',description:'Email-submit rewards campaign advertised as $750 towards Costco. Reward eligibility and fulfilment are determined by the advertiser.'},
 {id:27282,slug:'mcdonalds-100-rewards-us',name:'UpLevelRewards – McDonald’s $100',payout:2.50,category:'Rewards',geo:'United States',previewUrl:'https://www.uplevelrewards.com/?Flow=656AE1C3-D3CE-3C2C-D9AE-1CBE7395FA7DE8814900&isPrePop=true&RBC=1&lp=fastfoodreviewer&reward=mcds100foodrvwrbns&bckm=1',description:'Email-submit rewards campaign advertised as $100 for food or drinks at McDonald’s. Review advertiser terms; the reward is not guaranteed.'},
 {id:27281,slug:'target-750-rewards-us',name:'Rewards US – Target $750',payout:2.50,category:'Rewards',geo:'United States',previewUrl:'https://www.uplevelrewards.com/?Flow=656AE1C3-D3CE-3C2C-D9AE-1CBE7395FA7DE8814900&isPrePop=true&RBC=1&lp=flashpolllimitedtime&reward=target750limitedpoll',description:'Email-submit rewards campaign advertised as $750 towards Target shopping. Eligibility and fulfilment are controlled by the advertiser.'},
 {id:27279,slug:'zelle-750-rewards-us',name:'UpLevelRewards – Zelle $750',payout:2.50,category:'Rewards',geo:'United States',previewUrl:'https://www.surveysandpromoonline.com/?Flow=6b51d955-0748-462e-9eb5-0ccdd7eceb37&isPrePop=true&RBC=1&reward=zelle750',description:'Email-submit rewards campaign advertised as $750 on Zelle. Review advertiser terms and eligibility; reward is not guaranteed.'},
 {id:27034,slug:'ebike-1000-rewards-us',name:'UpLevelRewards – $1,000 eBike',payout:2.50,category:'Rewards',geo:'United States',previewUrl:'https://www.uplevelrewards.com/?Flow=656AE1C3-D3CE-3C2C-D9AE-1CBE7395FA7DE8814900&isPrePop=true&RBC=1&lp=flashpollshopping&reward=ebikepoll1000&bckm=1',description:'Email-submit rewards campaign advertised as $1,000 towards an eBike. Review all advertiser conditions; reward is not guaranteed.'},
 {id:21982,slug:'pepsi-jobs-us',name:'JobListings – Pepsi Jobs',payout:2.40,category:'Jobs',geo:'United States',description:'Email-submit lead campaign associated with Pepsi job listings. No specific job availability or interview may be claimed. Any wage claims must be substantiated.',restrictions:['No misleading or incentive traffic.','Do not state or imply that a particular job is currently available.','Do not state or imply that the visitor has an interview scheduled or will be scheduled.','Any claims about hourly wages must be substantiated.']}
]
const money = n => '$' + Number(n).toFixed(2)
const shell = {maxWidth:1120,margin:'0 auto',padding:'36px 18px 80px',fontFamily:'system-ui,sans-serif',color:'#172033'}
const box = {border:'1px solid #e2e8f0',borderRadius:14,padding:18,background:'#fff'}
const cta = {display:'inline-block',background:'#0369a1',color:'#fff',borderRadius:9,padding:'10px 15px',textDecoration:'none',fontWeight:700}
function Card({offer}) {
 return <article style={{...box,display:'flex',flexDirection:'column',gap:10}}>
  <div style={{display:'flex',justifyContent:'space-between',gap:10,flexWrap:'wrap'}}><b style={{color:'#0369a1'}}>{offer.category}</b><b style={{color:'#047857'}}>{money(offer.payout)} per approved lead</b></div>
  <h2 style={{fontSize:19,margin:0}}>{offer.name}</h2>
  <p style={{color:'#64748b',fontSize:13,margin:0}}>Campaign #{offer.id} · {offer.geo} · Email submit</p>
  <p style={{color:'#475569',lineHeight:1.6,margin:0}}>{offer.description}</p>
  <Link to={'/offers/'+offer.slug} style={{...cta,background:'#0f172a',alignSelf:'flex-start',marginTop:5}}>View offer details</Link>
 </article>
}
export default function AffiliateOffers() {
 const {slug} = useParams()
 const offer = OFFERS.find(item=>item.slug===slug)
 if (slug && !offer) return <main style={shell}><h1>Offer not found</h1><Link to="/offers">Browse offers</Link></main>
 if (offer) return <main style={{...shell,maxWidth:850}}>
  <Link to="/offers">← All affiliate offers</Link>
  <article style={{...box,marginTop:22,padding:'clamp(20px,4vw,36px)'}}>
   <b style={{color:'#0369a1'}}>SHOPNOLTD PARTNER OFFER · {offer.category}</b>
   <h1 style={{fontSize:'clamp(30px,5vw,44px)',lineHeight:1.15}}>{offer.name}</h1>
   <p style={{fontSize:22,fontWeight:800,color:'#047857'}}>{money(offer.payout)} potential payout per approved lead</p>
   <p style={{color:'#64748b'}}>Campaign #{offer.id} · Eligible geography: {offer.geo} · Conversion: email submit</p>
   <p style={{lineHeight:1.8}}>{offer.description}</p>
   <aside style={{background:'#f8fafc',padding:15,borderRadius:10,border:'1px solid #e2e8f0'}}>
    <b>Before you continue</b>
    <ul style={{lineHeight:1.8,color:'#475569'}}>
     <li>This campaign is intended for visitors in {offer.geo}; visitors elsewhere may not qualify.</li>
     <li>Review advertiser terms, eligibility, privacy notice and any costs before submitting information.</li>
     <li>Shopnoltd does not guarantee employment, prizes, gift cards, cash or rewards.</li>
     <li>Never provide passwords, payment-card details or government identity numbers through an offer form.</li>
    </ul>
   </aside>
   {offer.previewUrl ? <p><a href={offer.previewUrl} target="_blank" rel="nofollow noopener noreferrer">View advertiser preview ↗</a></p> : null}
   {offer.restrictions?.length ? <aside><b>Mandatory advertiser restrictions</b><ul>{offer.restrictions.map(rule=><li key={rule}>{rule}</li>)}</ul></aside> : null}
   <p style={{fontSize:13,color:'#64748b'}}>Affiliate disclosure: Shopnoltd may earn a commission if the advertiser accepts a qualifying lead. The advertiser's page and terms govern the actual offer.</p>
   {offer.trackingUrl ? <a href={(() => { const url = new URL(offer.trackingUrl); url.searchParams.set('s1','shopnoltd'); url.searchParams.set('s2',String(offer.id)); url.searchParams.set('s3','offer-detail'); return url.toString() })()} target="_blank" rel="sponsored nofollow noopener noreferrer" style={cta}>Continue to advertiser ↗</a> : <p style={{color:'#92400e',background:'#fffbeb',padding:12,borderRadius:8}}>Affiliate tracking link pending. This offer is listed for review, but its advertiser tracking link has not been supplied yet, so applications are not enabled.</p>}
  </article>
 </main>
 return <main style={shell}>
  <header style={{marginBottom:26}}>
   <b style={{color:'#0284c7'}}>SHOPNOLTD · AFFILIATE PARTNERS</b>
   <h1 style={{fontSize:'clamp(32px,5vw,46px)',marginBottom:8}}>Jobs &amp; Rewards Offers</h1>
   <p style={{maxWidth:780,color:'#64748b',lineHeight:1.7}}>Browse partner campaigns. Each offer has its own Shopnoltd information page. When you choose to continue, you go to the advertiser's page to review its terms and submit an email if eligible.</p>
   <small style={{color:'#64748b'}}>Sponsored affiliate links · Campaign terms and eligibility are set by the advertiser.</small>
  </header>
  <section aria-label="Affiliate offers" style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(min(100%,280px),1fr))',gap:16}}>
   {OFFERS.map(item=><Card key={item.id} offer={item}/>)}
  </section>
 </main>
}
