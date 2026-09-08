import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { Emulator } from "android-emulator-webrtc";
import "./style.css";

const API = import.meta.env.VITE_ANDROID_CLOUD_API || "/api";

function authHeader() {
  const token = localStorage.getItem("shopno_token") || localStorage.getItem("shopnoltd_access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
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

  const start = async () => {
    setBusy(true);
    setError("");
    try {
      const data = await api("/v1/android-cloud/sessions", { method: "POST", body: JSON.stringify({}) });
      setSession(data);
      setState("starting");
    } catch (e) {
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
      setBusy(false);
    }
  };

  useEffect(() => {
    if (!session) return undefined;
    const timer = setInterval(async () => {
      try {
        const next = await api(`/v1/android-cloud/sessions/${encodeURIComponent(session.session_id)}`);
        setSession(next);
      } catch {
        // The device may still be booting; the emulator component handles reconnects.
      }
    }, 10000);
    return () => clearInterval(timer);
  }, [session?.session_id]);

  return (
    <main className="page">
      <header className="header">
        <div>
          <div className="eyebrow">SHOPNOLTD TOOLBOX</div>
          <h1>Android Cloud</h1>
          <p>Use a real Android emulator from your browser.</p>
        </div>
        <div className={`status ${state}`}>{state}</div>
      </header>

      {error && <div className="error">{error}</div>}

      {!session ? (
        <section className="start-card">
          <h2>Launch Android</h2>
          <p>Start an isolated Shopnoltd Android device with browser touch, mouse, keyboard, audio, mock GPS and APK testing.</p>
          <button disabled={busy} onClick={start}>{busy ? "Starting…" : "Launch Android"}</button>
          <small>Sign in to Shopnoltd first. Sessions are automatically cleaned up after inactivity.</small>
        </section>
      ) : (
        <section className="workspace">
          <div className="toolbar">
            <button onClick={stop} disabled={busy}>Stop device</button>
            <span>Session {session.session_id.slice(0, 10)}…</span>
            {session.turn ? <span>TURN enabled</span> : <span>Direct ICE</span>}
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
          <aside className="info">
            <strong>Shopnoltd Android Cloud</strong>
            <span>Install and test Shopnoltd, Shopnoltd Admin, or ShopnoltdCollect without exposing ADB publicly.</span>
          </aside>
        </section>
      )}
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
