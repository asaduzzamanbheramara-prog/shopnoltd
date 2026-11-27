#!/usr/bin/env bash
set -euo pipefail
f="${1:?decrypted Secret JSON required}"
curl -fsSLo "$RUNNER_TEMP/kind" https://kind.sigs.k8s.io/dl/v0.27.0/kind-linux-amd64
chmod +x "$RUNNER_TEMP/kind"
sudo install "$RUNNER_TEMP/kind" /usr/local/bin/kind
curl -fsSLo "$RUNNER_TEMP/kubectl" https://dl.k8s.io/release/v1.32.0/bin/linux/amd64/kubectl
chmod +x "$RUNNER_TEMP/kubectl"
sudo install "$RUNNER_TEMP/kubectl" /usr/local/bin/kubectl
kind create cluster --name shopnoltd-recovery --wait 120s
python3 - "$f" "$RUNNER_TEMP/secrets-import.json" "$RUNNER_TEMP/namespaces.txt" <<'PY'
import base64,binascii,json,re,sys
from pathlib import Path
src,out,nsfile=map(Path,sys.argv[1:])
d=json.loads(src.read_text()); items=d.get("items",[])
if d.get("kind")!="List" or not items: raise SystemExit("Invalid Secret List")
seen=set(); ns=set(); importable=[]; excluded=0
for x in items:
 m=x.get("metadata") or {}; n=m.get("name"); s=m.get("namespace")
 if x.get("kind")!="Secret" or x.get("apiVersion")!="v1" or not n or not s or (s,n) in seen: raise SystemExit("Invalid/duplicate Secret identity")
 if not re.fullmatch(r"[a-z0-9]([-a-z0-9]*[a-z0-9])?",s): raise SystemExit("Invalid namespace")
 seen.add((s,n)); ns.add(s)
 for v in (x.get("data") or {}).values():
  try: base64.b64decode(v,validate=True)
  except (binascii.Error,ValueError,TypeError): raise SystemExit("Invalid Secret base64")
 secret_type=x.get("type","Opaque")
 if secret_type in ("kubernetes.io/service-account-token","bootstrap.kubernetes.io/token") or n.endswith(".node-password.k3s") or m.get("ownerReferences"):
  excluded+=1
  continue
 for k in ("uid","resourceVersion","creationTimestamp","managedFields","selfLink","generation"): m.pop(k,None)
 importable.append(x)
if not importable: raise SystemExit("No application-managed Secrets are eligible for isolated restore")
d["items"]=importable
out.write_text(json.dumps(d)); nsfile.write_text("\n".join(sorted(ns))+"\n")
print(f"PASS: validated {len(seen)} Secret objects across {len(ns)} namespaces; {len(importable)} eligible for restore, {excluded} cluster-bound objects excluded.")
PY
while read -r n; do
  kubectl get ns "$n" >/dev/null 2>&1 || kubectl create ns "$n" >/dev/null
done < "$RUNNER_TEMP/namespaces.txt"
kubectl create -f "$RUNNER_TEMP/secrets-import.json" >/dev/null
python3 - "$RUNNER_TEMP/secrets-import.json" <<'PY'
import json,subprocess,sys
expected=json.load(open(sys.argv[1]))["items"]
actual=json.loads(subprocess.check_output(["kubectl","get","secrets","-A","-o","json"],text=True))["items"]
have={(x["metadata"]["namespace"],x["metadata"]["name"]):x for x in actual}
for x in expected:
 k=(x["metadata"]["namespace"],x["metadata"]["name"])
 if k not in have: raise SystemExit("Secret not restored: "+k[0]+"/"+k[1])
 if set((x.get("data") or {}))-set((have[k].get("data") or {})): raise SystemExit("A restored Secret is missing data keys")
print(f"PASS: all {len(expected)} Kubernetes Secret objects restored into disposable kind cluster.")
PY
