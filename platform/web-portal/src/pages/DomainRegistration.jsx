import { useState } from "react";

// All browser domain traffic stays on the unified API origin. The API service
// forwards to the owning domain-service and preserves its authorization rules.
const API_BASE = import.meta.env.VITE_API_URL || "https://api.shopnoltd.dpdns.org/api/v1";
const COUNTRIES = ["US", "BD", "GB", "CA", "AU", "DE", "FR", "IN", "SG", "AE"];
const EMPTY_CONTACT = { first_name: "", last_name: "", address1: "", city: "", state: "", postal_code: "", country: "US", phone: "", email: "" };

function getToken() { return localStorage.getItem("shopno_token"); }

async function request(path, options = {}) {
  const token = getToken();
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { Accept: "application/json", ...(options.body ? { "Content-Type": "application/json" } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(options.headers || {}) },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || data.message || `Domain request failed (${response.status})`);
  return data;
}

export default function DomainRegistration() {
  const [domain, setDomain] = useState(""); const [years, setYears] = useState(1); const [result, setResult] = useState(null); const [loading, setLoading] = useState(false); const [contact, setContact] = useState(EMPTY_CONTACT); const [showContactForm, setShowContactForm] = useState(false); const [registered, setRegistered] = useState(null);

  async function checkAvailability(e) {
    e.preventDefault();
    const value = domain.trim().toLowerCase().replace(/^https?:\/\//, "").replace(/\/.*$/, "");
    if (!value || !value.includes(".")) { setResult({ type: "error", message: "Enter a valid domain, for example example.com" }); return; }
    setDomain(value); setLoading(true); setResult(null); setShowContactForm(false); setRegistered(null);
    try {
      const data = await request(`/domains/check-availability?domain=${encodeURIComponent(value)}&years=${years}`);
      setResult(data.available ? { type: "available", message: `${data.domain || value} is available!`, data } : { type: "taken", message: `${data.domain || value} is not available.`, data });
    } catch (err) { setResult({ type: "error", message: err.message || "Unable to check domain availability." }); }
    finally { setLoading(false); }
  }

  function startRegistration() {
    if (!getToken()) { window.location.href = `/login?next=${encodeURIComponent(`/domain-registration?domain=${domain}`)}`; return; }
    setShowContactForm(true);
  }

  async function submitRegistration(e) {
    e.preventDefault();
    if (!getToken()) { window.location.href = `/login?next=${encodeURIComponent(`/domain-registration?domain=${domain}`)}`; return; }
    setLoading(true); setRegistered(null);
    try {
      const data = await request("/domains/register", { method: "POST", body: JSON.stringify({ domain, years, contact }) });
      setRegistered({ type: "success", data }); setShowContactForm(false);
    } catch (err) { setRegistered({ type: "error", message: err.message || "Registration failed. Please try again." }); }
    finally { setLoading(false); }
  }

  function updateContact(field, value) { setContact((c) => ({ ...c, [field]: value })); }

  return (
    <main style={{ maxWidth: 1000, margin: "0 auto", padding: "48px 20px 80px", fontFamily: "system-ui, sans-serif" }}>
      <section style={{ textAlign: "center", marginBottom: 40 }}><div style={{ fontSize: 54 }}>🌐</div><h1 style={{ margin: "10px 0", fontSize: "clamp(34px, 6vw, 56px)", color: "#0f172a" }}>Register a Domain</h1><p style={{ maxWidth: 720, margin: "0 auto", color: "#64748b", fontSize: 18, lineHeight: 1.7 }}>Search and register real domains through Shopnoltd's registrar integration. Free <strong>*.shopnoltd.dpdns.org</strong> addresses remain available from Shopnoltd.</p></section>
      <section style={{ padding: 28, borderRadius: 18, background: "linear-gradient(135deg,#0284c7,#075985)" }}>
        <form onSubmit={checkAvailability} style={{ display: "flex", gap: 12, flexWrap: "wrap" }}><input value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="yourcompany.com" aria-label="Domain name" autoComplete="off" autoCapitalize="none" spellCheck={false} style={{ flex: "1 1 400px", height: 56, border: 0, borderRadius: 10, padding: "0 16px", fontSize: 17, boxSizing: "border-box" }} /><select value={years} onChange={(e) => setYears(Number(e.target.value))} aria-label="Registration length" style={{ height: 56, border: 0, borderRadius: 10, padding: "0 14px", fontSize: 16 }}>{[1,2,3,5,10].map((y) => <option key={y} value={y}>{y} year{y > 1 ? "s" : ""}</option>)}</select><button type="submit" disabled={loading} style={{ height: 56, border: 0, borderRadius: 10, padding: "0 24px", background: "#0f172a", color: "white", fontWeight: 700, fontSize: 16 }}>{loading ? "Checking..." : "Check availability"}</button></form>
        {result && <div role="status" aria-live="polite" style={{ marginTop: 20, padding: 18, borderRadius: 12, background: "rgba(255,255,255,.14)", color: "white", lineHeight: 1.6 }}><strong>{result.message}</strong>{result.data?.price != null && <div>Price: {result.data.currency || "USD"} {result.data.price} for {result.data.years} year(s)</div>}{result.type === "available" && !showContactForm && <button type="button" onClick={startRegistration} style={{ marginTop: 14, minHeight: 48, border: 0, borderRadius: 10, padding: "0 20px", background: "white", color: "#075985", fontWeight: 700 }}>Register this domain →</button>}</div>}
        {showContactForm && <form onSubmit={submitRegistration} style={{ marginTop: 20, padding: 20, borderRadius: 12, background: "rgba(255,255,255,.95)", color: "#0f172a", display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 12 }}><div style={{ gridColumn: "1 / -1", fontWeight: 700 }}>Registrant contact info (required by the registrar)</div>{[["first_name","First name"],["last_name","Last name"],["email","Email"],["phone","Phone"],["address1","Address"],["city","City"],["state","State / Province"],["postal_code","Postal code"]].map(([field,label]) => <label key={field} style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>{label}<input required value={contact[field]} onChange={(e) => updateContact(field,e.target.value)} style={{ height: 42, border: "1px solid #cbd5e1", borderRadius: 8, padding: "0 10px", fontSize: 15 }} /></label>)}<label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13 }}>Country<select required value={contact.country} onChange={(e) => updateContact("country",e.target.value)} style={{ height: 42, border: "1px solid #cbd5e1", borderRadius: 8, padding: "0 10px", fontSize: 15 }}>{COUNTRIES.map((c) => <option key={c} value={c}>{c}</option>)}</select></label><div style={{ gridColumn: "1 / -1" }}><button type="submit" disabled={loading} style={{ height: 48, border: 0, borderRadius: 10, padding: "0 24px", background: "#0284c7", color: "white", fontWeight: 700, fontSize: 16 }}>{loading ? "Registering..." : `Confirm & pay — ${result?.data?.currency || "USD"} ${result?.data?.price ?? ""}`}</button></div></form>}
        {registered?.type === "success" && <div style={{ marginTop: 16, padding: 16, borderRadius: 10, background: "rgba(34,197,94,.25)", color: "white" }}><strong>{registered.data.name} registered!</strong><div>Status: {registered.data.status} · Order: {registered.data.order_id || "—"}</div></div>}
        {registered?.type === "error" && <div style={{ marginTop: 16, padding: 16, borderRadius: 10, background: "rgba(248,113,113,.25)", color: "white" }}>{registered.message}</div>}
      </section>
    </main>
  );
}
