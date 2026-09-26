import os, sqlite3, subprocess, ipaddress, secrets
from pathlib import Path
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
jwk_client=PyJWKClient(JWKS_URL)
app=FastAPI(title='Shopnoltd VPN Service',version='1.1.0')
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=False, allow_methods=['*'], allow_headers=['*'])
class PeerIn(BaseModel):
    name:str=Field(min_length=1,max_length=80); address:str|None=None; persistent_keepalive:int=Field(default=25,ge=0,le=600)
def auth(x_vpn_admin_token:str|None=Header(default=None)):
    if not ADMIN_TOKEN or not secrets.compare_digest(x_vpn_admin_token or '',ADMIN_TOKEN): raise HTTPException(401,'VPN admin authentication required')
def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
    c.execute('create table if not exists peers(id integer primary key,name text not null unique,public_key text not null unique,address text not null unique,created_at text default current_timestamp,owner_sub text)')
    cols={r[1] for r in c.execute('pragma table_info(peers)').fetchall()}
    if 'owner_sub' not in cols: c.execute('alter table peers add column owner_sub text')
    return c

def user_from_request(request:Request):
    value=request.headers.get('authorization','')
    if not value.lower().startswith('bearer '): raise HTTPException(401,'Shopnoltd login required')
    token=value.split(' ',1)[1].strip()
    try:
        key=jwk_client.get_signing_key_from_jwt(token).key
        claims=jwt_decode(token,key,algorithms=['RS256'],issuer=OIDC_ISSUER,options={'verify_aud':False})
        if claims.get('azp') != OIDC_AUDIENCE and OIDC_AUDIENCE not in (claims.get('aud') if isinstance(claims.get('aud'),list) else [claims.get('aud')]): raise HTTPException(403,'Invalid Shopnoltd client')
        if not claims.get('sub'): raise HTTPException(401,'Invalid Shopnoltd identity')
        return claims
    except HTTPException: raise
    except PyJWTError as exc: raise HTTPException(401,'Invalid or expired Shopnoltd session') from exc
def run(*args,check=True): return subprocess.run(args,text=True,capture_output=True,check=check)
def get_pub(priv): return subprocess.run(['wg','pubkey'],input=priv,text=True,capture_output=True,check=True).stdout.strip()
def default_iface():
    r=run('sh','-c',"ip route show default | awk 'NR==1{print $5}'",check=False); return r.stdout.strip() or 'eth0'
def reconcile():
    c=db(); rows=c.execute('select public_key,address from peers').fetchall(); c.close()
    if rows:
        args=['wg','set',IFACE]
        for r in rows: args += ['peer',r['public_key'],'allowed-ips',r['address']+'/32','persistent-keepalive','25']
        run(*args)
def ensure_server():
    if not SERVER_KEY.exists(): SERVER_KEY.write_text(run('wg','genkey').stdout.strip()+'\n'); SERVER_KEY.chmod(0o600)
    try: run('wg','show',IFACE)
    except subprocess.CalledProcessError:
        run('ip','link','add','dev',IFACE,'type','wireguard'); run('wg','set',IFACE,'private-key',str(SERVER_KEY))
    run('ip','address','replace',SERVER_ADDR,'dev',IFACE); run('ip','link','set','up','dev',IFACE)
    run('sysctl','-w','net.ipv4.ip_forward=1',check=False)
    out=default_iface()
    for args in [
        ['iptables','-C','FORWARD','-i',IFACE,'-o',out,'-j','ACCEPT'],
        ['iptables','-C','FORWARD','-i',out,'-o',IFACE,'-m','conntrack','--ctstate','ESTABLISHED,RELATED','-j','ACCEPT'],
        ['iptables','-t','nat','-C','POSTROUTING','-s',str(NETWORK),'-o',out,'-j','MASQUERADE']]:
        if run(*args,check=False).returncode: run(*args[:1],check=False) if False else None
    if run('iptables','-C','FORWARD','-i',IFACE,'-o',out,'-j','ACCEPT',check=False).returncode: run('iptables','-A','FORWARD','-i',IFACE,'-o',out,'-j','ACCEPT',check=False)
    if run('iptables','-C','FORWARD','-i',out,'-o',IFACE,'-m','conntrack','--ctstate','ESTABLISHED,RELATED','-j','ACCEPT',check=False).returncode: run('iptables','-A','FORWARD','-i',out,'-o',IFACE,'-m','conntrack','--ctstate','ESTABLISHED,RELATED','-j','ACCEPT',check=False)
    if run('iptables','-t','nat','-C','POSTROUTING','-s',str(NETWORK),'-o',out,'-j','MASQUERADE',check=False).returncode: run('iptables','-t','nat','-A','POSTROUTING','-s',str(NETWORK),'-o',out,'-j','MASQUERADE',check=False)
    reconcile()
@app.on_event('startup')
def startup():
    try: ensure_server()
    except Exception as e: print(f'VPN startup deferred: {e}',flush=True)
@app.get('/healthz')
def health(): return {'status':'ok','service':'vpn-service'}
@app.get('/readyz')
def ready():
    try: run('wg','show',IFACE); return {'status':'ready','interface':IFACE}
    except Exception as e: raise HTTPException(503,str(e))
@app.get('/api/v1/vpn/status',dependencies=[Depends(auth)])
def status():
    try: return {'status':'ready','interface':IFACE,'endpoint':ENDPOINT,'network':str(NETWORK),'raw':run('wg','show',IFACE).stdout}
    except Exception as e: raise HTTPException(503,str(e))
@app.get('/api/v1/vpn/peers',dependencies=[Depends(auth)])
def peers():
    c=db(); rows=[dict(r) for r in c.execute('select id,name,public_key,address,created_at,owner_sub from peers order by id')]; c.close(); return rows
def allocate(c):
    used={r[0] for r in c.execute('select address from peers')}
    for host in NETWORK.hosts():
        a=str(host)
        if a==str(NETWORK.network_address+1) or a in used: continue
        return a
    raise HTTPException(409,'VPN address pool exhausted')
def peer_config(address,private,server_pub,keepalive): return f'[Interface]\nPrivateKey = {private}\nAddress = {address}/32\nDNS = {DNS}\n\n[Peer]\nPublicKey = {server_pub}\nAllowedIPs = 0.0.0.0/0\nEndpoint = {ENDPOINT}\nPersistentKeepalive = {keepalive}\n'
@app.post('/api/v1/vpn/peers',dependencies=[Depends(auth)])
def create_peer(p:PeerIn):
    c=db()
    if c.execute('select 1 from peers where name=?',(p.name,)).fetchone(): raise HTTPException(409,'peer name already exists')
    addr=p.address or allocate(c)
    try: ip=ipaddress.ip_address(addr)
    except ValueError: raise HTTPException(400,'address must be an IPv4 address')
    if ip not in NETWORK or ip==NETWORK.network_address or ip==ipaddress.ip_address(SERVER_ADDR.split('/')[0]): raise HTTPException(400,'address outside available VPN pool')
    if c.execute('select 1 from peers where address=?',(addr,)).fetchone(): raise HTTPException(409,'address already assigned')
    priv=run('wg','genkey').stdout.strip(); pub=get_pub(priv); c.execute('insert into peers(name,public_key,address) values(?,?,?)',(p.name,pub,addr)); c.commit(); c.close(); reconcile()
    return {'name':p.name,'public_key':pub,'address':addr,'config':peer_config(addr,priv,get_pub(SERVER_KEY.read_text().strip()),p.persistent_keepalive)}

class UserPeerIn(BaseModel):
    device_name:str=Field(min_length=1,max_length=80)
    persistent_keepalive:int=Field(default=25,ge=0,le=600)

@app.get('/api/v1/vpn/me')
def my_vpn(request:Request):
    claims=user_from_request(request); sub=claims['sub']; c=db()
    rows=[dict(r) for r in c.execute('select id,name,address,created_at from peers where owner_sub=? order by id',(sub,))]; c.close()
    return {'user':{'sub':sub,'email':claims.get('email')},'endpoint':ENDPOINT,'dns':DNS,'network':str(NETWORK),'peers':rows}

@app.post('/api/v1/vpn/me/peers')
def create_my_peer(request:Request,p:UserPeerIn):
    claims=user_from_request(request); sub=claims['sub']; c=db()
    if c.execute('select 1 from peers where owner_sub=?',(sub,)).fetchone(): raise HTTPException(409,'A VPN device is already provisioned for this account')
    name=f"{claims.get('preferred_username') or claims.get('email') or 'user'}-{p.device_name}"[:80]
    if c.execute('select 1 from peers where name=?',(name,)).fetchone(): raise HTTPException(409,'VPN device name already exists')
    addr=allocate(c); priv=run('wg','genkey').stdout.strip(); pub=get_pub(priv)
    c.execute('insert into peers(name,public_key,address,owner_sub) values(?,?,?,?)',(name,pub,addr,sub)); c.commit(); c.close(); reconcile()
    return {'name':name,'address':addr,'config':peer_config(addr,priv,get_pub(SERVER_KEY.read_text().strip()),p.persistent_keepalive),'endpoint':ENDPOINT}

@app.delete('/api/v1/vpn/me/peers/{peer_id}')
def delete_my_peer(request:Request,peer_id:int):
    claims=user_from_request(request); c=db(); row=c.execute('select * from peers where id=? and owner_sub=?',(peer_id,claims['sub'])).fetchone()
    if not row: raise HTTPException(404,'VPN device not found')
    c.execute('delete from peers where id=?',(peer_id,)); c.commit(); c.close(); run('wg','set',IFACE,'peer',row['public_key'],'remove',check=False)
    return {'deleted':peer_id}

@app.delete('/api/v1/vpn/peers/{peer_id}',dependencies=[Depends(auth)])
def delete_peer(peer_id:int):
    c=db(); row=c.execute('select * from peers where id=?',(peer_id,)).fetchone()
    if not row: raise HTTPException(404,'peer not found')
    c.execute('delete from peers where id=?',(peer_id,)); c.commit(); c.close(); run('wg','set',IFACE,'peer',row['public_key'],'remove',check=False); return {'deleted':peer_id}
@app.post('/api/v1/vpn/peers/{peer_id}/rotate',dependencies=[Depends(auth)])
def rotate_peer(peer_id:int):
    c=db(); row=c.execute('select * from peers where id=?',(peer_id,)).fetchone()
    if not row: raise HTTPException(404,'peer not found')
    old=row['public_key']; priv=run('wg','genkey').stdout.strip(); pub=get_pub(priv); c.execute('update peers set public_key=? where id=?',(pub,peer_id)); c.commit(); c.close(); run('wg','set',IFACE,'peer',old,'remove',check=False); reconcile()
    return {'name':row['name'],'public_key':pub,'address':row['address'],'config':peer_config(row['address'],priv,get_pub(SERVER_KEY.read_text().strip()),25)}
