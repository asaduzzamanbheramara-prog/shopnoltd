import json,os,sys,urllib.error,urllib.parse,urllib.request
BASE=os.environ.get("KEYCLOAK_URL","http://keycloak.shopno-identity.svc.cluster.local").rstrip("/")
REALM=os.environ.get("KEYCLOAK_REALM","shopnoltd")
CLIENT=os.environ.get("KEYCLOAK_SYNC_CLIENT_ID","shopnoltd-keycloak-readiness-audit")
SECRET=os.environ.get("KEYCLOAK_SYNC_CLIENT_SECRET","")
PROVIDERS={
"google":("google","GOOGLE_CLIENT_ID","GOOGLE_CLIENT_SECRET","openid profile email"),
"google-signup":("google","GOOGLE_CLIENT_ID","GOOGLE_CLIENT_SECRET","openid profile email"),
"facebook":("facebook","FACEBOOK_LOGIN_APP_ID","FACEBOOK_LOGIN_APP_SECRET","email public_profile"),
"facebook-signup":("facebook","FACEBOOK_APP_ID","FACEBOOK_APP_SECRET","email public_profile"),
"github":("github","GITHUB_CLIENT_ID","GITHUB_CLIENT_SECRET","user:email read:user"),
"github-signup":("github","GITHUB_CLIENT_ID","GITHUB_CLIENT_SECRET","user:email read:user")}
def request(method,path,token,body=None):
 data=None if body is None else json.dumps(body).encode()
 req=urllib.request.Request(BASE+path,data=data,method=method)
 req.add_header("Authorization","Bearer "+token); req.add_header("Content-Type","application/json")
 try:
  with urllib.request.urlopen(req,timeout=20) as r:
   raw=r.read(); return r.status,json.loads(raw) if raw else None
 except urllib.error.HTTPError as e: return e.code,None
def get_token():
 if not SECRET: raise RuntimeError("service-account secret missing")
 form=urllib.parse.urlencode({"grant_type":"client_credentials","client_id":CLIENT,"client_secret":SECRET}).encode()
 req=urllib.request.Request(BASE+"/realms/"+REALM+"/protocol/openid-connect/token",data=form)
 req.add_header("Content-Type","application/x-www-form-urlencoded")
 with urllib.request.urlopen(req,timeout=20) as r: token=json.load(r).get("access_token")
 if not token: raise RuntimeError("no access token returned")
 return token
def main():
 token=get_token()
 for alias,(pid,ide,se,scope) in PROVIDERS.items():
  cid=os.environ.get(ide,"").strip(); cs=os.environ.get(se,"").strip()
  if not cid or not cs: print("[SKIP]",alias,"credentials missing"); continue
  path="/admin/realms/"+REALM+"/identity-provider/instances/"+alias
  code,old=request("GET",path,token)
  payload={"alias":alias,"providerId":pid,"enabled":True,"trustEmail":True,"storeToken":False,"firstBrokerLoginFlowAlias":"first broker login","config":{"clientId":cid,"clientSecret":cs,"defaultScope":scope}}
  if code==200:
   for k in ("displayName","authenticateByDefault","linkOnly","hideOnLogin","guiOrder","postBrokerLoginFlowAlias"):
    if k in old: payload[k]=old[k]
   code,_=request("PUT",path,token,payload)
   if code not in (200,204): raise RuntimeError("update "+alias+" HTTP "+str(code))
   print("[OK] updated",alias)
  elif code==404:
   code,_=request("POST","/admin/realms/"+REALM+"/identity-provider/instances",token,payload)
   if code!=201: raise RuntimeError("create "+alias+" HTTP "+str(code))
   print("[OK] created",alias)
  else: raise RuntimeError("read "+alias+" HTTP "+str(code))
 print("[OK] only social identity providers processed")
if __name__=="__main__":
 try: main()
 except Exception as e: print("[FAIL]",type(e).__name__,str(e),file=sys.stderr); sys.exit(1)
