# KoBoCAT Kubernetes Deployment - SSL/Proxy Configuration Fix

## Summary of Changes

### Issue
The KoBoCAT and KPI deployments running behind an HTTPS reverse proxy (nginx Ingress) were missing critical proxy and SSL configuration settings, causing:
- Django to treat HTTPS connections as HTTP
- Potential redirect loops from HTTP to HTTPS
- Cookie security validation failures
- Host header mismatches (seeing container port instead of external domain)

### Root Cause
Required environment variables for reverse proxy support were not configured in the Kubernetes deployments.

---

## Deployments Updated

### 1. KPI Deployment (kc)
**File:** `06-kpi-deployment.yaml`

**Environment Variables Added:**
```yaml
- name: PUBLIC_DOMAIN_NAME
  value: shopnoltd.dpdns.org
- name: KOBOFORM_URL
  value: https://kobo.shopnoltd.dpdns.org
- name: KOBOCAT_URL
  value: https://kf.shopnoltd.dpdns.org
- name: SECURE_PROXY_SSL_HEADER
  value: HTTP_X_FORWARDED_PROTO, https
- name: USE_X_FORWARDED_HOST
  value: "true"
- name: PUBLIC_REQUEST_SCHEME
  value: https
```

**Why:**
- `SECURE_PROXY_SSL_HEADER`: Tells Django to trust the `X-Forwarded-Proto: https` header from the proxy
- `USE_X_FORWARDED_HOST`: Uses the proxy's `Host` header instead of container hostname
- `PUBLIC_REQUEST_SCHEME`: Ensures internal URLs are generated as HTTPS

---

### 2. KoBoCAT Deployment (kf)
**File:** `07-kobocat-deployment.yaml`

**Environment Variables Added:**
```yaml
- name: USE_X_FORWARDED_HOST
  value: "True"  # Note: KoBoCAT expects capital "True"
- name: PUBLIC_REQUEST_SCHEME
  value: https
```

**Note:** KoBoCAT automatically enables `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` when `PUBLIC_REQUEST_SCHEME=https` is set.

---

## Django Settings (KPI - kobo.settings.base)

```python
# Line 38: Parses from environment variable
SECURE_PROXY_SSL_HEADER = env.tuple('SECURE_PROXY_SSL_HEADER', str, None)

# Lines 42-46: Automatically enable secure cookies when proxy or HTTPS is detected
if public_request_scheme == 'https' or SECURE_PROXY_SSL_HEADER:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Line 55: Trust proxy's Host header
USE_X_FORWARDED_HOST = env.bool('USE_X_FORWARDED_HOST', False)
```

---

## Django Settings (KoBoCAT - onadata.settings.base)

```python
# Line 306-307: Case-sensitive check for capital "True"
if os.getenv("USE_X_FORWARDED_HOST", "False") == "True":
    USE_X_FORWARDED_HOST = True

# Lines 316-318: Secure cookies enabled via PUBLIC_REQUEST_SCHEME
if os.environ.get('PUBLIC_REQUEST_SCHEME', '').lower() == 'https':
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
```

---

## Deployment Commands Used

### KPI (kc) Patch
```bash
kubectl -n toolbox patch deployment kc --type='json' -p='[
  {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"SECURE_PROXY_SSL_HEADER","value":"HTTP_X_FORWARDED_PROTO, https"}},
  {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"USE_X_FORWARDED_HOST","value":"true"}},
  {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"PUBLIC_REQUEST_SCHEME","value":"https"}}
]'
```

### KoBoCAT (kf) Patch
```bash
kubectl -n toolbox patch deployment kf --type='json' -p='[
  {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"USE_X_FORWARDED_HOST","value":"True"}},
  {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"PUBLIC_REQUEST_SCHEME","value":"https"}}
]'
```

---

## Verification

### KPI Deployment Settings
```
SECURE_PROXY_SSL_HEADER: ('HTTP_X_FORWARDED_PROTO', ' https')
USE_X_FORWARDED_HOST: true
SESSION_COOKIE_SECURE: true
CSRF_COOKIE_SECURE: true
```

### KoBoCAT Deployment Settings
```
USE_X_FORWARDED_HOST: true
SESSION_COOKIE_SECURE: true
CSRF_COOKIE_SECURE: true
```

---

## Ingress Configuration

**Current Routing:**
- `kobo.shopnoltd.dpdns.org` → `kc-service:80` → Pod `kc:8000`
- `kf.shopnoltd.dpdns.org` → `kf-service:80` → Pod `kf:8000`
- `kobo.local/kc` → `kc-service:80` → Pod `kc:8000`
- `kobo.local/kf` → `kf-service:80` → Pod `kf:8000`

**Note:** Ingress provides HTTP-to-HTTPS termination via nginx, with X-Forwarded-Proto header forwarding.

---

## Next Steps

1. **Test External Access:**
   - Access `https://kobo.shopnoltd.dpdns.org` and verify no redirect loops
   - Access `https://kf.shopnoltd.dpdns.org` and verify form data uploads work

2. **Monitor Logs:**
   - Check pod logs for any SSL/cookie-related errors
   - Verify `X-Forwarded-Proto` headers are being processed

3. **Verify Cookies:**
   - Test cross-domain session sharing between KPI and KoBoCAT
   - Confirm secure flag is set on cookies in browser dev tools

4. **Consider Additional Hardening:**
   - Add `SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD` for HSTS headers
   - Review `ALLOWED_HOSTS` configuration (currently set to `*`)
   - Implement rate limiting at ingress level

---

## Files Modified

- `C:\Users\asadu\PROJECTS\shopnoltd\toolbox\06-kpi-deployment.yaml` - Added proxy/SSL env vars
- `C:\Users\asadu\PROJECTS\shopnoltd\toolbox\07-kobocat-deployment.yaml` - Added proxy/SSL env vars (newly created)
- Cluster deployments `kc` and `kf` - Live patches applied and rolled out

---

## References

- [Django SECURE_PROXY_SSL_HEADER](https://docs.djangoproject.com/en/stable/ref/settings/#secure-proxy-ssl-header)
- [Django USE_X_FORWARDED_HOST](https://docs.djangoproject.com/en/stable/ref/settings/#use-x-forwarded-host)
- [KoBoToolbox Documentation](https://docs.kobotoolbox.org/)
