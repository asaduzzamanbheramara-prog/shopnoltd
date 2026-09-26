import os, sqlite3, subprocess, ipaddress, secrets, time, json
from pathlib import Path
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from jwt import PyJWKClient, decode as jwt_decode
from jwt.exceptions import PyJWTError
from pydantic import BaseModel, Field

DATA_DIR=Path(os.getenv('VPN_DATA_DIR','/data')); DATA_DIR.mkdir(parents=True,exist_ok=True)
DB=DATA_DIR/'vpn.db'; SERVER_KEY=DATA_DIR/'server_private.key'; IFACE=os.getenv('WG_INTERFACE','wg0')
NETWORK=ipaddress.ip_network(os.getenv('WG_NETWORK','10.77.0.0/24')); SERVER_ADDR=os.getenv('WG_SERVER_ADDRESS','10.77.0.1/24')
ENDPOINT=os.getenv('WG_SERVER_ENDPOINT','vpn.shopnoltd.dpdns.org:51820'); DNS=os.getenv('WG_DNS','1.1.1.1'); ADMIN_TOKEN=os.getenv('VPN_ADMIN_TOKEN','')
OIDC_ISSUER=os.getenv('OIDC_ISSUER','https://auth.shopnoltd.dpdns.org/realms/shopnoltd'); OIDC_AUDIENCE=os.getenv('OIDC_AUDIENCE','shopnoltd-web'); JWKS_URL=f'{OIDC_ISSUER}/protocol/openid-connect/certs'
ALLOWED_ORIGINS=[x.strip() for x in os.getenv('CORS_ALLOWED_ORIGINS','https://shopnoltd.dpdns.org').split(',') if x.strip()]
DEFAULT_LOCATION=os.getenv('VPN_LOCATION_ID','bd-dhaka'); DEFAULT_COUNTRY=os.getenv('VPN_LOCATION_COUNTRY','Bangladesh'); DEFAULT_CITY=os.getenv('VPN_LOCATION_CITY','Dhaka')
jwk_client=PyJWKClient(JWKS_URL)
app=FastAPI(title='Shopnoltd VPN Provider',version='2.0.0')
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=False, allow_methods=['*'], allow_headers=['*'])

class DeviceIn(BaseModel):
    device_name:str=Field(min_length=1,max_length=80)
    location_id:str=Field(default=DEFAULT_LOCATION,min_length=2,max_length=64)
    persistent_keepalive:int=Field(default=25,ge=0,le=600)
class LocationIn(BaseModel):
    id:str=Field(min_length=2,max_length=64); country:str=Field(min_length=2,max_length=80); city:str=Field(min_length=2,max_length=80); enabled:bool=True
class GatewayIn(BaseModel):
    id:str=Field(min_length=2,max_length=80); location_id:str; name:str=Field(min_length=2,max_length=100); endpoint:str; public_key:str=''; capacity:int=Field(default=100,ge=1,le=100000); enabled:bool=True
class HeartbeatIn(BaseModel):
    gateway_id:str; active_peers:int=Field(default=0,ge=0); rx_bytes:int=Field(default=0,ge=0); tx_bytes:int=Field(default=0,ge=0); healthy:bool=True
class PlanIn(BaseModel):
    id:str=Field(min_length=2,max_length=64); name:str=Field(min_length=2,max_length=100); monthly_price_bdt:int=Field(default=0,ge=0); max_devices:int=Field(default=1,ge=1,max=100); enabled:bool=True
class SubscriptionIn(BaseModel):
    sub:str; plan_id:str; expires_at:str|None=None

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
    c.executescript('''
    create table if not exists peers(id integer primary key,name text not null unique,public_key text not null unique,address text not null unique,created_at text default current_timestamp,owner_sub text,location_id text,gateway_id text,revoked_at text);
    create table if not exists locations(id text primary key,country text not null,city text not null,enabled integer not null default 1);
    create table if not exists gateways(id text primary key,location_id text not null,name text not null,endpoint text not null,public_key text default '',capacity integer not null default 100,active_peers integer not null default 0,rx_bytes integer not null default 0,tx_bytes integer not null default 0,healthy integer not null default 0,enabled integer not null default 1,last_heartbeat text);
    create table if not exists plans(id text primary key,name text not null,monthly_price_bdt integer not null default 0,max_devices integer not null default 1,enabled integer not null default 1);
    create table if not exists subscriptions(id integer primary key,owner_sub text not null unique,plan_id text not null,expires_at text,created_at text default current_timestamp);
    create table if not exists connections(id integer primary key,peer_id integer not null,gateway_id text not null,connected_at text default current_timestamp,last_seen text,disconnected_at text);
    create table if not exists usage(id integer primary key,owner_sub text not null,peer_id integer,gateway_id text,rx_bytes integer not null default 0,tx_bytes integer not null default 0,observed_at text default current_timestamp);
    create table if not exists audit_log(id integer primary key,event text not null,owner_sub text,actor text,details text,created_at text default current_timestamp);
    ''')
    cols={r[1] for r in c.execute('pragma table_info(peers)').fetchall()}
    for name,typ in [('owner_sub','text'),('location_id','text'),('gateway_id','text'),('revoked_at','text')]:
        if name not in cols: c.execute(f'alter table peers add column {name} {typ}')
    c.execute('insert or ignore into locations(id,country,city,enabled) values(?,?,?,1)',(DEFAULT_LOCATION,DEFAULT_COUNTRY,DEFAULT_CITY))
    for row in [('sg-singapore','Singapore','Singapore',0),('jp-tokyo','Japan','Tokyo',0),('de-frankfurt','Germany','Frankfurt',0),('gb-london','United Kingdom','London',0),('us-new-york','United States','New York',0)]: c.execute('insert or ignore into locations(id,country,city,enabled) values(?,?,?,?)',row)
    c.execute('insert or ignore into gateways(id,location_id,name,endpoint,capacity,enabled,healthy,last_heartbeat) values(?,?,?,?,?,?,1,?)',('gw-primary',DEFAULT_LOCATION,'Primary Shopnoltd Gateway',ENDPOINT,100,1,now()))
    c.execute('insert or ignore into plans(id,name,monthly_price_bdt,max_devices,enabled) values(?,?,?,?,1)',('vpn-free','Shopnoltd VPN Free',0,1))
    c.commit(); return c

def now(): return datetime.now(timezone.utc).isoformat()
def run(*args,check=True): return subprocess.run(args,text=True,capture_output=True,check=check)
def get_pub(priv): return subprocess.run(['wg','pubkey'],input=priv,text=True,capture_output=True,check=True).stdout.strip()
def default_iface():
    r=run('sh','-c',"ip route show default | awk 'NR==1{print $5}'",check=False); return r.stdout.strip() or 'eth0'

def admin(x_vpn_admin_token:str|None=Header(default=None)):
    if not ADMIN_TOKEN or not secrets.compare_digest(x_vpn_admin_token or '',ADMIN_TOKEN): raise HTTPException(401,'VPN admin authentication required')

def user_from_request(request:Request):
    value=request.headers.get('authorization','')
    if not value.lower().startswith('bearer '): raise HTTPException(401,'Shopnoltd login required')
    token=value.split(' ',1)[1].strip()
    try:
        key=jwk_client.get_signing_key_from_jwt(token).key
        claims=jwt_decode(token,key,algorithms=['RS256'],issuer=OIDC_ISSUER,options={'verify_aud':False})
        aud=claims.get('aud'); auds=aud if isinstance(aud,list) else [aud]
        if claims.get('azp') != OIDC_AUDIENCE and OIDC_AUDIENCE not in auds: raise HTTPException(403,'Invalid Shopnoltd client')
        if not claims.get('sub'): raise HTTPException(401,'Invalid Shopnoltd identity')
        return claims
    except HTTPException: raise
    except PyJWTError as exc: raise HTTPException(401,'Invalid or expired Shopnoltd session') from exc

def reconcile():
    c=db(); rows=c.execute('select public_key,address from peers where revoked_at is null').fetchall(); c.close()
    if rows:
        args=['wg','set',IFACE]
        for r in rows: args += ['peer',r['public_key'],'allowed-ips',r['address']+'/32','persistent-keepalive','25']
        run(*args,check=False)

def ensure_server():
    if not SERVER_KEY.exists(): SERVER_KEY.write_text(run('wg','genkey').stdout.strip()+'\n'); SERVER_KEY.chmod(0o600)
    try: run('wg','show',IFACE)
    except subprocess.CalledProcessError: run('ip','link','add','dev',IFACE,'type','wireguard'); run('wg','set',IFACE,'private-key',str(SERVER_KEY))
    run('ip','address','replace',SERVER_ADDR,'dev',IFACE); run('ip','link','set','up','dev',IFACE); run('sysctl','-w','net.ipv4.ip_forward=1',check=False)
    out=default_iface()
    rules=[(['iptables','-A','FORWARD','-i',IFACE,'-o',out,'-j','ACCEPT'],['iptables','-C','FORWARD','-i',IFACE,'-o',out,'-j','ACCEPT']),(['iptables','-A','FORWARD','-i',out,'-o',IFACE,'-m','conntrack','--ctstate','ESTABLISHED,RELATED','-j','ACCEPT'],['iptables','-C','FORWARD','-i',out,'-o',IFACE,'-m','conntrack','--ctstate','ESTABLISHED,RELATED','-j','ACCEPT']),(['iptables','-t','nat','-A','POSTROUTING','-s',str(NETWORK),'-o',out,'-j','MASQUERADE'],['iptables','-t','nat','-C','POSTROUTING','-s',str(NETWORK),'-o',out,'-j','MASQUERADE'])]
    for add,check in rules:
        if run(*check,check=False).returncode: run(*add,check=False)
    reconcile()

@app.on_event('startup')
def startup():
    db().close()
    try: ensure_server()
    except Exception as e: print(f'VPN startup deferred: {e}',flush=True)

@app.get('/healthz')
def health(): return {'status':'ok','service':'vpn-service','version':'2.0.0'}
@app.get('/readyz')
def ready():
    try: run('wg','show',IFACE); return {'status':'ready','interface':IFACE}
    except Exception as e: raise HTTPException(503,str(e))

@app.get('/api/v1/vpn/locations')
def locations():
    c=db(); rows=[dict(r) for r in c.execute('select id,country,city,enabled from locations order by country,city')];
    for r in rows:
        g=c.execute('select count(*) n from gateways where location_id=? and enabled=1 and healthy=1',(r['id'],)).fetchone()['n']; r['available']=bool(g)
    c.close(); return rows

@app.get('/api/v1/vpn/locations/{location_id}')
def location(location_id:str):
    c=db(); row=c.execute('select * from locations where id=?',(location_id,)).fetchone();
    if not row: raise HTTPException(404,'VPN location not found')
    gateways=[dict(x) for x in c.execute('select id,name,endpoint,capacity,active_peers,healthy,last_heartbeat from gateways where location_id=? and enabled=1',(location_id,))]; c.close()
    return {'location':dict(row),'gateways':gateways}

@app.get('/api/v1/vpn/plans')
def plans():
    c=db(); rows=[dict(r) for r in c.execute('select id,name,monthly_price_bdt,max_devices,enabled from plans where enabled=1 order by monthly_price_bdt,id')]; c.close(); return rows

@app.get('/api/v1/vpn/me')
def my_vpn(request:Request):
    claims=user_from_request(request); sub=claims['sub']; c=db();
    rows=[dict(r) for r in c.execute('select p.id,p.name,p.address,p.created_at,p.location_id,p.gateway_id,p.revoked_at,l.country,l.city from peers p left join locations l on l.id=p.location_id where p.owner_sub=? and p.revoked_at is null order by p.id',(sub,))]
    s=c.execute('select s.plan_id,s.expires_at,p.name,p.max_devices,p.monthly_price_bdt from subscriptions s join plans p on p.id=s.plan_id where s.owner_sub=?',(sub,)).fetchone()
    if not s: s=c.execute('select id as plan_id,null as expires_at,name,max_devices,monthly_price_bdt from plans where id="vpn-free"').fetchone()
    c.close(); return {'user':{'sub':sub,'email':claims.get('email'),'username':claims.get('preferred_username')},'endpoint':ENDPOINT,'dns':DNS,'network':str(NETWORK),'devices':rows,'peers':rows,'subscription':dict(s) if s else None}

def allocate(c):
    used={r[0] for r in c.execute('select address from peers where revoked_at is null')}
    for host in NETWORK.hosts():
        a=str(host)
        if a==str(NETWORK.network_address+1) or a in used: continue
        return a
    raise HTTPException(409,'VPN address pool exhausted')

def peer_config(address,private,server_pub,keepalive,endpoint=ENDPOINT):
    return f'[Interface]\nPrivateKey = {private}\nAddress = {address}/32\nDNS = {DNS}\n\n[Peer]\nPublicKey = {server_pub}\nAllowedIPs = 0.0.0.0/0\nEndpoint = {endpoint}\nPersistentKeepalive = {keepalive}\n'

def select_gateway(c,location_id):
    row=c.execute('select * from gateways where location_id=? and enabled=1 and healthy=1 order by (active_peers*1.0/capacity),active_peers limit 1',(location_id,)).fetchone()
    if not row: raise HTTPException(409,'No healthy VPN gateway is available in this location yet')
    if row['active_peers'] >= row['capacity']: raise HTTPException(409,'Selected VPN location is at capacity')
    return row

@app.post('/api/v1/vpn/me/devices')
def create_device(request:Request,p:DeviceIn):
    claims=user_from_request(request); sub=claims['sub']; c=db()
    plan=c.execute('select s.plan_id,s.expires_at,p.max_devices from subscriptions s join plans p on p.id=s.plan_id where s.owner_sub=?',(sub,)).fetchone()
    if not plan: plan=c.execute('select id as plan_id,null as expires_at,max_devices from plans where id="vpn-free"').fetchone()
    if plan['expires_at'] and plan['expires_at'] < now(): raise HTTPException(402,'VPN subscription has expired')
    count=c.execute('select count(*) n from peers where owner_sub=? and revoked_at is null',(sub,)).fetchone()['n']
    if count >= plan['max_devices']: raise HTTPException(409,f'Device limit reached for {plan["plan_id"]} plan')
    loc=c.execute('select * from locations where id=? and enabled=1',(p.location_id,)).fetchone()
    if not loc: raise HTTPException(404,'VPN location not found or disabled')
    gateway=select_gateway(c,p.location_id); addr=allocate(c)
    prefix=claims.get('preferred_username') or claims.get('email') or 'user'; name=f'{prefix}-{p.device_name}'[:80]
    if c.execute('select 1 from peers where name=?',(name,)).fetchone(): raise HTTPException(409,'VPN device name already exists')
    priv=run('wg','genkey').stdout.strip(); pub=get_pub(priv)
    c.execute('insert into peers(name,public_key,address,owner_sub,location_id,gateway_id) values(?,?,?,?,?,?)',(name,pub,addr,sub,p.location_id,gateway['id']))
    peer_id=c.execute('select last_insert_rowid()').fetchone()[0]
    c.execute('insert into connections(peer_id,gateway_id,last_seen) values(?,?,?)',(peer_id,gateway['id'],now()))
    c.execute('insert into audit_log(event,owner_sub,actor,details) values(?,?,?,?)',('device_created',sub,'user',json.dumps({'peer_id':peer_id,'location':p.location_id})))
    c.commit(); c.close(); reconcile()
    return {'id':peer_id,'name':name,'address':addr,'location':{'id':p.location_id,'country':loc['country'],'city':loc['city']},'gateway':{'id':gateway['id'],'name':gateway['name'],'endpoint':gateway['endpoint']},'config':peer_config(addr,priv,gateway['public_key'] or get_pub(SERVER_KEY.read_text().strip()),p.persistent_keepalive,gateway['endpoint'])}

@app.post('/api/v1/vpn/me/peers')
def create_my_peer_legacy(request:Request,p:DeviceIn): return create_device(request,p)

@app.delete('/api/v1/vpn/me/devices/{peer_id}')
def delete_my_device(request:Request,peer_id:int):
    claims=user_from_request(request); c=db(); row=c.execute('select * from peers where id=? and owner_sub=? and revoked_at is null',(peer_id,claims['sub'])).fetchone()
    if not row: raise HTTPException(404,'VPN device not found')
    c.execute('update peers set revoked_at=? where id=?',(now(),peer_id)); c.execute('update connections set disconnected_at=? where peer_id=? and disconnected_at is null',(now(),peer_id)); c.execute('insert into audit_log(event,owner_sub,actor,details) values(?,?,?,?)',('device_revoked',claims['sub'],'user',json.dumps({'peer_id':peer_id}))); c.commit(); c.close(); run('wg','set',IFACE,'peer',row['public_key'],'remove',check=False); return {'deleted':peer_id}

@app.delete('/api/v1/vpn/me/peers/{peer_id}')
def delete_my_peer_legacy(request:Request,peer_id:int): return delete_my_device(request,peer_id)

@app.get('/api/v1/vpn/me/usage')
def my_usage(request:Request):
    claims=user_from_request(request); c=db(); row=c.execute('select coalesce(sum(rx_bytes),0) rx_bytes,coalesce(sum(tx_bytes),0) tx_bytes from usage where owner_sub=?',(claims['sub'],)).fetchone(); c.close(); return dict(row)

@app.get('/api/v1/vpn/me/connections')
def my_connections(request:Request):
    claims=user_from_request(request); c=db(); rows=[dict(r) for r in c.execute('select c.id,c.peer_id,c.gateway_id,c.connected_at,c.last_seen,c.disconnected_at,g.name,g.endpoint from connections c left join gateways g on g.id=c.gateway_id join peers p on p.id=c.peer_id where p.owner_sub=? order by c.id desc',(claims['sub'],))]; c.close(); return rows

@app.get('/api/v1/vpn/status',dependencies=[Depends(admin)])
def status():
    try: return {'status':'ready','interface':IFACE,'endpoint':ENDPOINT,'network':str(NETWORK),'raw':run('wg','show',IFACE).stdout}
    except Exception as e: raise HTTPException(503,str(e))

@app.get('/api/v1/vpn/peers',dependencies=[Depends(admin)])
def peers():
    c=db(); rows=[dict(r) for r in c.execute('select * from peers order by id')]; c.close(); return rows

@app.post('/api/v1/vpn/admin/locations',dependencies=[Depends(admin)])
def admin_location(p:LocationIn):
    c=db(); c.execute('insert into locations(id,country,city,enabled) values(?,?,?,?) on conflict(id) do update set country=excluded.country,city=excluded.city,enabled=excluded.enabled',(p.id,p.country,p.city,int(p.enabled))); c.commit(); c.close(); return {'ok':True,'location':p.model_dump()}

@app.post('/api/v1/vpn/admin/gateways',dependencies=[Depends(admin)])
def admin_gateway(p:GatewayIn):
    c=db(); c.execute('insert into gateways(id,location_id,name,endpoint,public_key,capacity,enabled) values(?,?,?,?,?,?,?) on conflict(id) do update set location_id=excluded.location_id,name=excluded.name,endpoint=excluded.endpoint,public_key=excluded.public_key,capacity=excluded.capacity,enabled=excluded.enabled',(p.id,p.location_id,p.name,p.endpoint,p.public_key,p.capacity,int(p.enabled))); c.commit(); c.close(); return {'ok':True,'gateway':p.model_dump()}

@app.post('/api/v1/vpn/gateway/heartbeat',dependencies=[Depends(admin)])
def heartbeat(p:HeartbeatIn):
    c=db(); cur=c.execute('update gateways set active_peers=?,rx_bytes=?,tx_bytes=?,healthy=?,last_heartbeat=? where id=?',(p.active_peers,p.rx_bytes,p.tx_bytes,int(p.healthy),now(),p.gateway_id));
    if not cur.rowcount: raise HTTPException(404,'Gateway not found')
    c.commit(); c.close(); return {'ok':True,'gateway_id':p.gateway_id}

@app.get('/api/v1/vpn/admin/gateways',dependencies=[Depends(admin)])
def admin_gateways():
    c=db(); rows=[dict(r) for r in c.execute('select g.*,l.country,l.city from gateways g left join locations l on l.id=g.location_id order by l.country,g.name')]; c.close(); return rows

@app.get('/api/v1/vpn/admin/audit',dependencies=[Depends(admin)])
def audit(limit:int=100):
    c=db(); rows=[dict(r) for r in c.execute('select * from audit_log order by id desc limit ?',(min(max(limit,1),500),))]; c.close(); return rows

@app.get('/api/v1/vpn/admin/subscriptions',dependencies=[Depends(admin)])
def admin_subscriptions():
    c=db(); rows=[dict(r) for r in c.execute('select s.*,p.name plan_name,p.max_devices from subscriptions s join plans p on p.id=s.plan_id order by s.id desc')]; c.close(); return rows

@app.post('/api/v1/vpn/admin/subscriptions',dependencies=[Depends(admin)])
def admin_subscription(p:SubscriptionIn):
    c=db();
    if not c.execute('select 1 from plans where id=? and enabled=1',(p.plan_id,)).fetchone(): raise HTTPException(404,'VPN plan not found')
    c.execute('insert into subscriptions(owner_sub,plan_id,expires_at) values(?,?,?) on conflict(owner_sub) do update set plan_id=excluded.plan_id,expires_at=excluded.expires_at',(p.sub,p.plan_id,p.expires_at)); c.commit(); c.close(); return {'ok':True}

@app.post('/api/v1/vpn/admin/plans',dependencies=[Depends(admin)])
def admin_plan(p:PlanIn):
    c=db(); c.execute('insert into plans(id,name,monthly_price_bdt,max_devices,enabled) values(?,?,?,?,?) on conflict(id) do update set name=excluded.name,monthly_price_bdt=excluded.monthly_price_bdt,max_devices=excluded.max_devices,enabled=excluded.enabled',(p.id,p.name,p.monthly_price_bdt,p.max_devices,int(p.enabled))); c.commit(); c.close(); return {'ok':True}

@app.delete('/api/v1/vpn/peers/{peer_id}',dependencies=[Depends(admin)])
def delete_peer(peer_id:int):
    c=db(); row=c.execute('select * from peers where id=?',(peer_id,)).fetchone()
    if not row: raise HTTPException(404,'peer not found')
    c.execute('update peers set revoked_at=? where id=?',(now(),peer_id)); c.commit(); c.close(); run('wg','set',IFACE,'peer',row['public_key'],'remove',check=False); return {'deleted':peer_id}

@app.post('/api/v1/vpn/peers/{peer_id}/rotate',dependencies=[Depends(admin)])
def rotate_peer(peer_id:int):
    c=db(); row=c.execute('select * from peers where id=?',(peer_id,)).fetchone()
    if not row: raise HTTPException(404,'peer not found')
    old=row['public_key']; priv=run('wg','genkey').stdout.strip(); pub=get_pub(priv); c.execute('update peers set public_key=? where id=?',(pub,peer_id)); c.commit(); c.close(); run('wg','set',IFACE,'peer',old,'remove',check=False); reconcile()
    return {'name':row['name'],'public_key':pub,'address':row['address'],'config':peer_config(row['address'],priv,get_pub(SERVER_KEY.read_text().strip()),25)}
