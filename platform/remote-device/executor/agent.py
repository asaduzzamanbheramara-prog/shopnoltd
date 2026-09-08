#!/usr/bin/env python3
"""Shopnoltd outbound-only executor with unified device/network profile reporting."""
from __future__ import annotations
import base64, hashlib, hmac, json, os, platform, re, socket, subprocess, sys, time, uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CONFIG_PATH = Path(os.getenv("SHOPNOLTD_EXECUTOR_CONFIG", r"C:\ProgramData\Shopnoltd\executor.json"))
POLL_SECONDS=5; HEARTBEAT_SECONDS=30; HTTP_TIMEOUT=30; COMMAND_TIMEOUT=60


def load_config():
    if not CONFIG_PATH.exists(): raise RuntimeError(f"Missing executor configuration: {CONFIG_PATH}")
    value=json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if not value.get("gateway_url") or not value.get("device_id"): raise RuntimeError("Missing gateway_url or device_id")
    if not ((value.get("enrollment_token")) or (value.get("agent_id") and value.get("secret"))): raise RuntimeError("Configuration must contain enrollment_token or agent_id + secret")
    return value


def canonical_json(value): return json.dumps(value,separators=(",",":"),sort_keys=True)


def sign(secret,timestamp,nonce,method,path,body):
    raw=base64.b64decode(secret); key=hashlib.sha256(b"shopnoltd-executor-hmac-v1:"+raw).digest()
    msg="\n".join([timestamp,nonce,method.upper(),path,body]).encode()
    return hmac.new(key,msg,hashlib.sha256).hexdigest()


def request(config,method,path,payload=None):
    gateway=config["gateway_url"].rstrip("/"); body=canonical_json(payload) if payload is not None else ""
    ts=str(int(time.time())); nonce=uuid.uuid4().hex
    headers={"Accept":"application/json","Content-Type":"application/json","X-Shopnoltd-Device":config["device_id"],"X-Shopnoltd-Agent":config["agent_id"],"X-Shopnoltd-Timestamp":ts,"X-Shopnoltd-Nonce":nonce,"X-Shopnoltd-Signature":sign(config["secret"],ts,nonce,method,path,body),"User-Agent":"Shopnoltd-Executor/2.0"}
    req=Request(gateway+path,data=body.encode() if body else None,headers=headers,method=method.upper())
    with urlopen(req,timeout=HTTP_TIMEOUT) as response: raw=response.read().decode("utf-8")
    return json.loads(raw) if raw else {}


def run(command,timeout=COMMAND_TIMEOUT):
    try:
        r=subprocess.run(command,capture_output=True,text=True,timeout=timeout,shell=False,check=False)
        return {"returncode":r.returncode,"stdout":r.stdout[-20000:],"stderr":r.stderr[-10000:]}
    except subprocess.TimeoutExpired: return {"returncode":124,"stdout":"","stderr":"command timed out"}
    except Exception as exc: return {"returncode":1,"stdout":"","stderr":str(exc)}


def interface_profile():
    system=platform.system().lower(); local=[]; vpn=[]; vpn_interface=""; provider=""
    try:
        for item in socket.getaddrinfo(socket.gethostname(),None):
            value=item[4][0]
            if value not in local and ":" not in value or (value not in local):
                if value not in ("127.0.0.1","::1") and value not in local: local.append(value)
    except Exception: pass
    if system == "windows":
        r=run(["powershell.exe","-NoProfile","-NonInteractive","-Command","Get-NetIPAddress | Select-Object IPAddress,InterfaceAlias,AddressFamily | ConvertTo-Json -Compress"])
        try:
            rows=json.loads(r.get("stdout") or "[]"); rows=rows if isinstance(rows,list) else [rows]
            for row in rows:
                value=str(row.get("IPAddress") or ""); alias=str(row.get("InterfaceAlias") or "")
                if value and value not in ("127.0.0.1","::1") and value not in local: local.append(value)
                low=alias.lower()
                if any(k in low for k in ("wireguard","tailscale","zerotier","openvpn","vpn","tun","tap")):
                    if value and value not in vpn: vpn.append(value)
                    vpn_interface=alias
                    provider=next((k.title() for k in ("wireguard","tailscale","zerotier","openvpn") if k in low),"VPN")
        except Exception: pass
    else:
        r=run(["sh","-lc","ip -o addr 2>/dev/null || true"])
        for line in (r.get("stdout") or "").splitlines():
            m=re.search(r"\d+:\s+([^ ]+)\s+inet6?\s+([^ /]+)",line)
            if m:
                iface,value=m.group(1),m.group(2)
                if value not in ("127.0.0.1","::1") and value not in local: local.append(value)
                low=iface.lower()
                if any(k in low for k in ("wg","tun","tap","tailscale","zerotier","vpn")):
                    if value not in vpn: vpn.append(value)
                    vpn_interface=iface
                    provider=next((k.title() for k in ("tailscale","zerotier","wireguard") if k in low),"VPN")
    public_ip=None
    for url in ("https://api64.ipify.org","https://api.ipify.org"):
        try:
            value=urlopen(url,timeout=5).read().decode().strip()
            import ipaddress
            ipaddress.ip_address(value); public_ip=value; break
        except Exception: pass
    return {"local_ips":local[:32],"public_ip":public_ip,"vpn_ips":vpn[:32],"vpn_provider":provider,"vpn_interface":vpn_interface}


def system_profile():
    return {"hostname":socket.gethostname(),"system":platform.system(),"platform":platform.platform(),"release":platform.release(),"machine":platform.machine(),"python":platform.python_version(),"time":time.time()}


def operation_system_info(): return system_profile()
def operation_windows_info(): return run(["powershell.exe","-NoProfile","-NonInteractive","-Command","$o=[ordered]@{ComputerName=$env:COMPUTERNAME;OS=(Get-CimInstance Win32_OperatingSystem).Caption;Version=(Get-CimInstance Win32_OperatingSystem).Version;Architecture=(Get-CimInstance Win32_OperatingSystem).OSArchitecture};$o|ConvertTo-Json -Compress"])
def operation_wsl_info(): return run(["wsl.exe","--status"])
def operation_k3s_info(): return run(["wsl.exe","-e","bash","-lc","export KUBECONFIG=/home/shopno/k3s.yaml; kubectl get nodes -o wide"])
def operation_k8s_pods(): return run(["wsl.exe","-e","bash","-lc","export KUBECONFIG=/home/shopno/k3s.yaml; kubectl get pods -A -o wide"],90)
def operation_k8s_services(): return run(["wsl.exe","-e","bash","-lc","export KUBECONFIG=/home/shopno/k3s.yaml; kubectl get svc -A -o wide"],90)
def operation_git_status(): return run(["wsl.exe","-e","bash","-lc","cd /mnt/c/Users/asadu/PROJECTS/shopnoltd && git status --short --branch"])
def operation_shopnoltd_health(): return run(["powershell.exe","-NoProfile","-NonInteractive","-Command","$urls=@('https://api.shopnoltd.dpdns.org/healthz','https://api.shopnoltd.dpdns.org/readyz','https://remote.shopnoltd.dpdns.org/healthz');$urls|%{$r=Invoke-WebRequest -UseBasicParsing -Uri $_ -TimeoutSec 15;$_.ToString()+' '+$r.StatusCode+' '+$r.Content}"],60)
def operation_disk_status(): return run(["powershell.exe","-NoProfile","-NonInteractive","-Command","Get-PSDrive -PSProvider FileSystem|Select-Object Name,Used,Free|ConvertTo-Json -Compress"])
def operation_memory_status(): return run(["powershell.exe","-NoProfile","-NonInteractive","-Command","$o=[ordered]@{TotalPhysicalMemory=(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory;FreePhysicalMemory=(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory};$o|ConvertTo-Json -Compress"])
def operation_remote_device_status(): return run(["wsl.exe","-e","bash","-lc","export KUBECONFIG=/home/shopno/k3s.yaml; kubectl -n shopno-tools get pods,svc -l app=remote-device-gateway -o wide; kubectl -n shopno-tools get pods,svc -l app=remote-device-registry -o wide; kubectl -n shopno-tools get pods,svc -l app=remote-device-ui -o wide"],90)

OPERATIONS={"system.info":operation_system_info,"windows.info":operation_windows_info,"wsl.info":operation_wsl_info,"k3s.info":operation_k3s_info,"k8s.pods":operation_k8s_pods,"k8s.services":operation_k8s_services,"git.status":operation_git_status,"shopnoltd.health":operation_shopnoltd_health,"disk.status":operation_disk_status,"memory.status":operation_memory_status,"remote-device.status":operation_remote_device_status}


def execute(job):
    operation=job.get("operation")
    if operation not in OPERATIONS:return {"ok":False,"error":f"operation_not_allowed: {operation}"}
    started=time.time()
    try:return {"ok":True,"operation":operation,"duration_seconds":round(time.time()-started,3),"result":OPERATIONS[operation]()}
    except Exception as exc:return {"ok":False,"operation":operation,"error":str(exc),"duration_seconds":round(time.time()-started,3)}


def enroll(config):
    gateway=config["gateway_url"].rstrip("/"); path=f"/api/executor/enroll/{config['device_id']}"
    payload={"enrollment_token":config["enrollment_token"],"hostname":socket.gethostname(),"platform":platform.system(),"agent_version":"2.0","profile":system_profile(),"network":interface_profile()}
    body=canonical_json(payload).encode(); req=Request(gateway+path,data=body,headers={"Accept":"application/json","Content-Type":"application/json","User-Agent":"Shopnoltd-Executor/2.0"},method="POST")
    try:
        with urlopen(req,timeout=HTTP_TIMEOUT) as response:return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc: raise RuntimeError(f"executor enrollment HTTP {exc.code}: {exc.read().decode('utf-8',errors='replace')}") from exc
    except URLError as exc: raise RuntimeError(f"executor enrollment connection failed: {exc}") from exc


def heartbeat(config):
    return request(config,"POST",f"/api/executor/heartbeat/{config['device_id']}",{"agent_id":config["agent_id"],"version":"2.0","platform":platform.system(),"hostname":socket.gethostname(),"profile":system_profile(),"network":interface_profile()})
def poll(config): return request(config,"GET",f"/api/executor/jobs/{config['device_id']}")
def submit_result(config,job_id,result): return request(config,"POST",f"/api/executor/jobs/{job_id}/result",result)


def main():
    config=load_config()
    if config.get("enrollment_token") and (not config.get("agent_id") or not config.get("secret")):
        response=enroll(config)
        if not response.get("ok"): raise RuntimeError(f"executor enrollment failed: {response}")
        raise RuntimeError("Enrollment succeeded. Persist returned agent_id and secret securely, remove enrollment_token, then restart.")
    last=0.0
    while True:
        try:
            now=time.time()
            if now-last>=HEARTBEAT_SECONDS: heartbeat(config); last=now
            jobs=poll(config).get("jobs",[])
            if jobs:
                job=jobs[0]; job_id=job.get("id")
                if job_id: submit_result(config,job_id,execute(job))
            time.sleep(POLL_SECONDS)
        except KeyboardInterrupt:return
        except (HTTPError,URLError,TimeoutError,OSError,RuntimeError) as exc: print(f"executor communication error: {exc}",file=sys.stderr); time.sleep(min(POLL_SECONDS*4,30))
        except Exception as exc: print(f"executor error: {exc}",file=sys.stderr); time.sleep(10)

if __name__=="__main__": main()
