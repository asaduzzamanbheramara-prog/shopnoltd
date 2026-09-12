import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Emulator } from "android-emulator-webrtc";
import "./style.css";

const API = import.meta.env.VITE_ANDROID_CLOUD_API || "/api";
const KEYCLOAK_URL = import.meta.env.VITE_KEYCLOAK_URL || "https://auth.shopnoltd.dpdns.org";
const KEYCLOAK_REALM = import.meta.env.VITE_KEYCLOAK_REALM || "shopnoltd";
const KEYCLOAK_CLIENT_ID = import.meta.env.VITE_KEYCLOAK_CLIENT_ID || "shopnoltd-web";
const REDIRECT_URI = `${window.location.origin}/callback`;

function authHeader() {
  const token = localStorage.getItem("shopno_token") || localStorage.getItem("shopnoltd_access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function tokenPresent() {
  return Boolean(localStorage.getItem("shopno_token") || localStorage.getItem("shopnoltd_access_token"));
}

function randomString(length = 64) {
  const bytes = new Uint8Array(length);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("");
}

async function pkceChallenge(verifier) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return btoa(String.fromCharCode(...new Uint8Array(digest))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function clearAuth() {
  localStorage.removeItem("shopno_token");
  localStorage.removeItem("shopnoltd_access_token");
  localStorage.removeItem("shopno_refresh_token");
}

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...authHeader(), ...(options.headers || {}) },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
  return body;
}

function App() {
  const [session, setSession] = useState(null);
  const [state, setState] = useState("idle");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [authenticated, setAuthenticated] = useState(tokenPresent);
  const [authBusy, setAuthBusy] = useState(false);

  const login = async () => {
    setAuthBusy(true); setError("");
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
    const body = new URLSearchParams({ grant_type: "authorization_code", client_id: KEYCLOAK_CLIENT_ID, code, redirect_uri: REDIRECT_URI, code_verifier: verifier });
    fetch(`${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    })
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
        window.history.replaceState({}, "", next && next.startsWith("/") && !next.startsWith("//") ? next : "/");
      })
      .catch((e) => setError(e?.message || "Shopnoltd authentication failed."))
      .finally(() => setAuthBusy(false));
  }, []);

  const start = async () => {
    setBusy(true); setError("");
    try {
      if (!tokenPresent()) {
        setAuthenticated(false);
        throw new Error("Please sign in to Shopnoltd first.");
      }
      const data = await api("/v1/android-cloud/sessions", { method: "POST", body: JSON.stringify({}) });
      setSession(data); setState("starting");
    } catch (e) {
      if (["missing_bearer_token", "invalid_bearer_token", "token_has_no_subject"].includes(e?.message)) {
        clearAuth(); setAuthenticated(false);
      }
      setError(e.message);
    } finally { setBusy(false); }
  };

  const stop = async () => {
    if (!session) return;
    setBusy(true);
    try { await api(`/v1/android-cloud/sessions/${encodeURIComponent(session.session_id)}`, { method: "DELETE" }); }
    catch (e) { setError(e.message); }
    finally { setSession(null); setState("idle"); setBusy(false); }
  };

  useEffect(() => {
    if (!session) return undefined;
    const timer = setInterval(async () => {
      try { setSession(await api(`/v1/android-cloud/sessions/${encodeURIComponent(session.session_id)}`)); }
      catch (e) {
        if (["missing_bearer_token", "invalid_bearer_token", "token_has_no_subject"].includes(e?.message)) {
          clearAuth(); setAuthenticated(false); setSession(null); setState("idle"); setError("Your Shopnoltd session expired. Please sign in again.");
        }
      }
    }, 10000);
    return () => clearInterval(timer);
  }, [session?.session_id]);

  const authLabel = useMemo(() => authBusy ? "Signing in…" : authenticated ? "Signed in" : "Sign in to Shopnoltd", [authBusy, authenticated]);

  return (
    <main className="page">
      <header className="header">
        <div><div className="eyebrow">SHOPNOLTD TOOLBOX</div><h1>Android Cloud</h1><p>Use a real Android emulator from your browser.</p></div>
        <div className="header-actions">
          <div className={`status ${state}`}>{state}</div>
          {!session && (authenticated ? <button className="secondary" onClick={logout}>Sign out</button> : <button className="secondary" onClick={login} disabled={authBusy}>{authLabel}</button>)}
        </div>
      </header>
      {error && <div className="error">{error}</div>}
      {!session ? (
        <section className="start-card">
          <h2>Launch Android</h2>
          <p>Start an isolated Shopnoltd Android device with browser touch, mouse, keyboard, audio, mock GPS and APK testing.</p>
          <button disabled={busy || authBusy || !authenticated} onClick={start}>{busy ? "Starting…" : authenticated ? "Launch Android" : "Sign in to launch"}</button>
          <small>{authenticated ? "You are signed in to Shopnoltd. Sessions are automatically cleaned up after inactivity." : "Sign in to Shopnoltd first. Your session is stored only in this browser and is used to authorize the Android Cloud controller."}</small>
        </section>
      ) : (
        <section className="workspace">
          <div className="toolbar"><button onClick={stop} disabled={busy}>Stop device</button><span>Session {session.session_id.slice(0, 10)}…</span>{session.turn ? <span>TURN enabled</span> : <span>Direct ICE</span>}</div>
          <div className="device-frame">
            <Emulator uri={session.gateway_url} auth={{ authHeader, unauthorized: () => setError("Your Shopnoltd session expired. Please sign in again.") }} muted={false} onStateChange={setState} onError={(e) => setError(e?.message || "Android WebRTC connection failed")} />
          </div>
          <aside className="info"><strong>Shopnoltd Android Cloud</strong><span>Install and test Shopnoltd, Shopnoltd Admin, or ShopnoltdCollect without exposing ADB publicly.</span></aside>
        </section>
      )}
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
