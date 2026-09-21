import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Emulator } from "android-emulator-webrtc";
import "./style.css";

const API = import.meta.env.VITE_ANDROID_CLOUD_API || "/android-cloud/api";
const KEYCLOAK_URL = import.meta.env.VITE_KEYCLOAK_URL || "https://auth.shopnoltd.dpdns.org";
const KEYCLOAK_REALM = import.meta.env.VITE_KEYCLOAK_REALM || "shopnoltd";
const KEYCLOAK_CLIENT_ID = import.meta.env.VITE_KEYCLOAK_CLIENT_ID || "shopnoltd-web";
const TOKEN_URL = `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token`;
const REDIRECT_URI = `${window.location.origin}/android-cloud/callback`;

function token() { return localStorage.getItem("shopno_token"); }
function refreshToken() { return localStorage.getItem("shopno_refresh_token"); }
function authHeader() { const value = token(); return value ? { Authorization: `Bearer ${value}` } : {}; }
function tokenPresent() { return Boolean(token()); }

function randomString(length = 64) {
  const bytes = new Uint8Array(length);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("");
}

async function pkceChallenge(verifier) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return btoa(String.fromCharCode(...new Uint8Array(digest))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function tryRefresh() {
  const refresh = refreshToken();
  if (!refresh) return false;
  try {
    const response = await fetch(TOKEN_URL, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ grant_type: "refresh_token", client_id: KEYCLOAK_CLIENT_ID, refresh_token: refresh }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.access_token) return false;
    localStorage.setItem("shopno_token", data.access_token);
    if (data.refresh_token) localStorage.setItem("shopno_refresh_token", data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

function clearAuth() {
  localStorage.removeItem("shopno_token");
  localStorage.removeItem("shopnoltd_access_token");
  localStorage.removeItem("shopno_refresh_token");
}

async function api(path, options = {}, retry = true) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...authHeader(), ...(options.headers || {}) },
  });
  const body = await response.json().catch(() => ({}));
  if (response.status === 401 && retry && await tryRefresh()) return api(path, options, false);
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
  return body;
}

async function apiForm(path, formData, retry = true) {
  const response = await fetch(`${API}${path}`, {
    method: "POST",
    headers: authHeader(),
    body: formData,
  });
  const body = await response.json().catch(() => ({}));
  if (response.status === 401 && retry && await tryRefresh()) return apiForm(path, formData, false);
  if (!response.ok) throw new Error(body.detail || `Upload failed (${response.status})`);
  return body;
}

function App() {
  const [session, setSession] = useState(null);
  const [state, setState] = useState("idle");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [authenticated, setAuthenticated] = useState(tokenPresent);
  const [authBusy, setAuthBusy] = useState(false);
  const [officialApps, setOfficialApps] = useState([]);
  const [installedApps, setInstalledApps] = useState([]);
  const [appBusy, setAppBusy] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState("");
  const fileRef = useRef(null);

  const login = async () => {
    setAuthBusy(true);
    setError("");
    try {
      const verifier = randomString(48);
      const stateValue = randomString(24);
      const challenge = await pkceChallenge(verifier);
      sessionStorage.setItem("android_cloud_pkce_verifier", verifier);
      sessionStorage.setItem("android_cloud_oidc_state", stateValue);
      sessionStorage.setItem("android_cloud_post_login_next", window.location.pathname + window.location.search);
      const params = new URLSearchParams({
        client_id: KEYCLOAK_CLIENT_ID,
        redirect_uri: REDIRECT_URI,
        response_type: "code",
        scope: "openid profile email",
        state: stateValue,
        code_challenge: challenge,
        code_challenge_method: "S256",
      });
      window.location.assign(`${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/auth?${params}`);
    } catch (e) {
      setError(e?.message || "Unable to start Shopnoltd sign in.");
      setAuthBusy(false);
    }
  };

  const logout = () => {
    if (session) return;
    clearAuth();
    setAuthenticated(false);
    setError("");
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const returnedState = params.get("state");
    const oauthError = params.get("error");
    const oauthErrorDescription = params.get("error_description");
    if (!code && !oauthError) return;
    const verifier = sessionStorage.getItem("android_cloud_pkce_verifier");
    const expectedState = sessionStorage.getItem("android_cloud_oidc_state");
    if (oauthError) {
      setError(oauthErrorDescription || oauthError);
      sessionStorage.removeItem("android_cloud_pkce_verifier");
      sessionStorage.removeItem("android_cloud_oidc_state");
      window.history.replaceState({}, "", window.location.pathname);
      return;
    }
    if (!code || !verifier || !expectedState || returnedState !== expectedState) {
      setError("Shopnoltd authentication could not be validated. Please sign in again.");
      sessionStorage.removeItem("android_cloud_pkce_verifier");
      sessionStorage.removeItem("android_cloud_oidc_state");
      window.history.replaceState({}, "", window.location.pathname);
      return;
    }
    setAuthBusy(true);
    const body = new URLSearchParams({
      grant_type: "authorization_code",
      client_id: KEYCLOAK_CLIENT_ID,
      code,
      redirect_uri: REDIRECT_URI,
      code_verifier: verifier,
    });
    fetch(TOKEN_URL, { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body })
      .then(async (response) => {
        const data = await response.json().catch(() => ({}));
        if (!response.ok || !data.access_token) throw new Error(data.error_description || data.error || "Shopnoltd authentication failed.");
        return data;
      })
      .then((data) => {
        localStorage.setItem("shopno_token", data.access_token);
        if (data.refresh_token) localStorage.setItem("shopno_refresh_token", data.refresh_token);
        setAuthenticated(true);
        const next = sessionStorage.getItem("android_cloud_post_login_next");
        sessionStorage.removeItem("android_cloud_pkce_verifier");
        sessionStorage.removeItem("android_cloud_oidc_state");
        sessionStorage.removeItem("android_cloud_post_login_next");
        window.history.replaceState({}, "", next && next.startsWith("/") && !next.startsWith("//") ? next : "/android-cloud");
      })
      .catch((e) => setError(e?.message || "Shopnoltd authentication failed."))
      .finally(() => setAuthBusy(false));
  }, []);

  const refreshApps = useCallback(async () => {
    if (!session) return;
    try {
      const data = await api(`/v1/android-cloud/sessions/${encodeURIComponent(session.session_id)}/apps`);
      setInstalledApps(data.packages || []);
    } catch (e) {
      if ([ "missing_bearer_token", "invalid_bearer_token", "token_has_no_subject" ].includes(e?.message)) {
        clearAuth();
        setAuthenticated(false);
      }
    }
  }, [session]);

  const start = async () => {
    setBusy(true);
    setError("");
    try {
      if (!tokenPresent() && !(await tryRefresh())) {
        setAuthenticated(false);
        throw new Error("Please sign in to Shopnoltd first.");
      }
      setAuthenticated(true);
      const data = await api("/v1/android-cloud/sessions", { method: "POST", body: JSON.stringify({}) });
      setSession(data);
      setState("starting");
      const capabilities = await api("/v1/android-cloud/capabilities");
      setOfficialApps(capabilities.official_apps || []);
    } catch (e) {
      if ([ "missing_bearer_token", "invalid_bearer_token", "token_has_no_subject" ].includes(e?.message)) {
        clearAuth();
        setAuthenticated(false);
      }
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const stop = async () => {
    if (!session) return;
    setBusy(true);
    try {
      await api(`/v1/android-cloud/sessions/${encodeURIComponent(session.session_id)}`, { method: "DELETE" });
    } catch (e) {
      setError(e.message);
    } finally {
      setSession(null);
      setState("idle");
      setInstalledApps([]);
      setOfficialApps([]);
      setSelectedFile(null);
      setBusy(false);
    }
  };

  const installOfficial = async (app) => {
    setAppBusy(app.id);
    setError("");
    try {
      await api(`/v1/android-cloud/sessions/${encodeURIComponent(session.session_id)}/apps/official/${encodeURIComponent(app.id)}/install`, { method: "POST" });
      await refreshApps();
    } catch (e) {
      setError(e.message);
    } finally {
      setAppBusy("");
    }
  };

  const uploadApk = async () => {
    if (!selectedFile || !session) return;
    if (!selectedFile.name.toLowerCase().endsWith(".apk")) {
      setError("Please select an APK file.");
      return;
    }
    setAppBusy("upload");
    setUploadProgress(`Uploading ${selectedFile.name}…`);
    setError("");
    try {
      const form = new FormData();
      form.append("file", selectedFile, selectedFile.name);
      const result = await apiForm(`/v1/android-cloud/sessions/${encodeURIComponent(session.session_id)}/apps/upload`, form);
      setUploadProgress(`Installed ${result.filename} (${result.sha256.slice(0, 12)}…)`);
      setSelectedFile(null);
      if (fileRef.current) fileRef.current.value = "";
      await refreshApps();
    } catch (e) {
      setError(e.message);
      setUploadProgress("");
    } finally {
      setAppBusy("");
    }
  };

  const launchApp = async (packageName) => {
    setAppBusy(`launch:${packageName}`);
    setError("");
    try {
      await api(`/v1/android-cloud/sessions/${encodeURIComponent(session.session_id)}/apps/launch`, {
        method: "POST",
        body: JSON.stringify({ package_name: packageName }),
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setAppBusy("");
    }
  };

  const uninstallApp = async (packageName) => {
    setAppBusy(`uninstall:${packageName}`);
    setError("");
    try {
      await api(`/v1/android-cloud/sessions/${encodeURIComponent(session.session_id)}/apps/uninstall`, {
        method: "POST",
        body: JSON.stringify({ package_name: packageName }),
      });
      await refreshApps();
    } catch (e) {
      setError(e.message);
    } finally {
      setAppBusy("");
    }
  };

  useEffect(() => {
    if (!session) return undefined;
    refreshApps();
    const timer = setInterval(async () => {
      try {
        setSession(await api(`/v1/android-cloud/sessions/${encodeURIComponent(session.session_id)}`));
        await refreshApps();
      } catch (e) {
        if ([ "missing_bearer_token", "invalid_bearer_token", "token_has_no_subject" ].includes(e?.message)) {
          clearAuth();
          setAuthenticated(false);
          setSession(null);
          setState("idle");
          setError("Your Shopnoltd session expired. Please sign in again.");
        }
      }
    }, 10000);
    return () => clearInterval(timer);
  }, [session?.session_id]);

  const authLabel = useMemo(
    () => authBusy ? "Signing in…" : authenticated ? "Signed in" : "Sign in to Shopnoltd",
    [authBusy, authenticated],
  );

  return (
    <main className="page">
      <header className="header">
        <div>
          <div className="eyebrow">SHOPNOLTD TOOLBOX</div>
          <h1>Android Cloud</h1>
          <p>Use a private Android emulator from your browser.</p>
        </div>
        <div className="header-actions">
          <div className={`status ${state}`}>{state}</div>
          {!session && (authenticated
            ? <button className="secondary" onClick={logout}>Sign out</button>
            : <button className="secondary" onClick={login} disabled={authBusy}>{authLabel}</button>)}
        </div>
      </header>

      {error && <div className="error">{error}</div>}

      {!session ? (
        <section className="start-card">
          <h2>Launch Android</h2>
          <p>Start an isolated Android device with browser touch, mouse, keyboard and APK testing.</p>
          <button disabled={busy || authBusy || !authenticated} onClick={start}>
            {busy ? "Starting…" : authenticated ? "Launch Android" : "Sign in to launch"}
          </button>
          <small>{authenticated
            ? "Your emulator is private to this session. ADB is never exposed publicly."
            : "Sign in to Shopnoltd first."}</small>
        </section>
      ) : (
        <section className="workspace">
          <div className="toolbar">
            <button onClick={stop} disabled={busy}>Stop device</button>
            <span>Session {session.session_id.slice(0, 10)}…</span>
            {session.turn ? <span className="network-ok">TURN enabled</span> : <span className="network-warn">Direct ICE</span>}
          </div>

          <div className="device-frame">
            <Emulator
              uri={session.gateway_url}
              auth={{ authHeader, unauthorized: () => setError("Your Shopnoltd session expired. Please sign in again.") }}
              muted={false}
              onStateChange={setState}
              onError={(e) => setError(e?.message || "Android WebRTC connection failed")}
            />
          </div>

          <section className="apps-panel">
            <div className="panel-heading">
              <div><h2>Install an Android app</h2><p>Official Shopnoltd apps are downloaded from the current Shopnoltd release routes.</p></div>
            </div>

            <div className="official-grid">
              {officialApps.map((app) => (
                <article className="app-card" key={app.id}>
                  <div><strong>{app.name}</strong><small>Official Shopnoltd APK</small></div>
                  <button disabled={Boolean(appBusy)} onClick={() => installOfficial(app)}>
                    {appBusy === app.id ? "Installing…" : "Install"}
                  </button>
                </article>
              ))}
            </div>

            <div className="upload-card">
              <div>
                <strong>Other APK</strong>
                <small>Upload an APK from your computer. Maximum size: 100 MB.</small>
              </div>
              <div className="upload-controls">
                <input ref={fileRef} type="file" accept=".apk,application/vnd.android.package-archive" onChange={(e) => setSelectedFile(e.target.files?.[0] || null)} />
                <button disabled={!selectedFile || Boolean(appBusy)} onClick={uploadApk}>
                  {appBusy === "upload" ? "Installing…" : "Install APK"}
                </button>
              </div>
              {uploadProgress && <small className="success">{uploadProgress}</small>}
            </div>

            <div className="installed-card">
              <div className="panel-heading">
                <div><h3>Installed third-party apps</h3><p>Only user-installed packages are listed here.</p></div>
                <button className="secondary" onClick={refreshApps} disabled={Boolean(appBusy)}>Refresh</button>
              </div>
              {installedApps.length === 0
                ? <div className="empty">No third-party apps installed yet.</div>
                : <div className="installed-list">
                  {installedApps.map((pkg) => (
                    <div className="installed-row" key={pkg}>
                      <code>{pkg}</code>
                      <div>
                        <button disabled={Boolean(appBusy)} onClick={() => launchApp(pkg)}>Launch</button>
                        <button className="danger" disabled={Boolean(appBusy)} onClick={() => uninstallApp(pkg)}>
                          {appBusy === `uninstall:${pkg}` ? "Removing…" : "Uninstall"}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>}
            </div>
          </section>

          <aside className="info">
            <strong>Private Android Cloud</strong>
            <span>Browser → HTTPS/WebRTC → session gateway → private emulator. Public ADB is disabled.</span>
          </aside>
        </section>
      )}
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
