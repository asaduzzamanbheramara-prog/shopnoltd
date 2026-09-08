import { useState } from "react";

const API_BASE = "https://domain.shopnoltd.dpdns.org/api/v1";

function authHeaders() {
  const token =
    localStorage.getItem("shopno_token") ||
    localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export default function DomainRegistration() {
  const [domain, setDomain] = useState("");
  const [years, setYears] = useState(1);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [registering, setRegistering] = useState(false);

  async function checkAvailability(e) {
    e.preventDefault();

    const value = domain
      .trim()
      .toLowerCase()
      .replace(/^https?:\/\//, "")
      .replace(/\/.*$/, "");

    if (!value || !value.includes(".")) {
      setResult({
        type: "error",
        message: "Enter a valid domain, for example example.com",
      });
      return;
    }

    setDomain(value);
    setLoading(true);
    setResult(null);

    try {
      const response = await fetch(
        `${API_BASE}/domains/check?domain=${encodeURIComponent(value)}`,
        {
          headers: { Accept: "application/json", ...authHeaders() },
        }
      );

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.detail || "Domain service unavailable");
      }

      if (data.available) {
        let pricing = null;
        try {
          const tld = value.split(".").pop();
          const priceRes = await fetch(
            `${API_BASE}/domains/pricing?tld=${encodeURIComponent(tld)}&years=${years}`,
            { headers: { Accept: "application/json", ...authHeaders() } }
          );
          if (priceRes.ok) pricing = await priceRes.json();
        } catch {
          /* pricing is best-effort; registration re-fetches it server-side anyway */
        }
        setResult({
          type: "available",
          message: `${value} is available!`,
          data: { ...data, ...pricing },
        });
      } else {
        setResult({
          type: "taken",
          message: `${value} is not available.`,
          data,
        });
      }
    } catch (err) {
      setResult({
        type: "error",
        message: err.message || "Unable to check domain availability.",
      });
    } finally {
      setLoading(false);
    }
  }

  async function registerDomain() {
    const token =
      localStorage.getItem("shopno_token") ||
      localStorage.getItem("access_token");

    if (!token) {
      window.location.href = `/login?next=${encodeURIComponent(
        `/domain-registration?domain=${domain}`
      )}`;
      return;
    }

    setRegistering(true);
    setResult((prev) => ({
      ...prev,
      type: "info",
      message: "Charging your wallet and registering…",
    }));

    try {
      const response = await fetch(
        `${API_BASE}/domains/register?domain=${encodeURIComponent(domain)}&years=${years}`,
        {
          method: "POST",
          headers: { Accept: "application/json", ...authHeaders() },
        }
      );
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.detail || `Registration failed (${response.status})`);
      }

      setResult({
        type: "registered",
        message: `${data.domain} registered! Charged ${data.currency} ${data.charged_amount}.`,
        data,
      });
    } catch (err) {
      setResult({
        type: "error",
        message: err.message || "Domain registration failed.",
      });
    } finally {
      setRegistering(false);
    }
  }

  return (
    <main
      style={{
        maxWidth: 1000,
        margin: "0 auto",
        padding: "48px 20px 80px",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <section style={{ textAlign: "center", marginBottom: 40 }}>
        <div style={{ fontSize: 54 }}>🌐</div>

        <h1
          style={{
            margin: "10px 0",
            fontSize: "clamp(34px, 6vw, 56px)",
            color: "#0f172a",
          }}
        >
          Register a Domain
        </h1>

        <p
          style={{
            maxWidth: 720,
            margin: "0 auto",
            color: "#64748b",
            fontSize: 18,
            lineHeight: 1.7,
          }}
        >
          Search and register real domains through Shopnoltd's registrar
          integration. Free <strong>*.shopnoltd.dpdns.org</strong> addresses
          remain available from the Shopnoltd home page.
        </p>
      </section>

      <section
        style={{
          padding: 28,
          borderRadius: 18,
          background: "linear-gradient(135deg,#0284c7,#075985)",
        }}
      >
        <form
          onSubmit={checkAvailability}
          style={{ display: "flex", gap: 12, flexWrap: "wrap" }}
        >
          <input
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            placeholder="yourcompany.com"
            aria-label="Domain name"
            autoComplete="off"
            autoCapitalize="none"
            spellCheck={false}
            style={{
              flex: "1 1 400px",
              height: 56,
              border: 0,
              borderRadius: 10,
              padding: "0 16px",
              fontSize: 17,
              boxSizing: "border-box",
            }}
          />

          <select
            value={years}
            onChange={(e) => setYears(Number(e.target.value))}
            aria-label="Registration years"
            style={{ height: 56, borderRadius: 10, border: 0, padding: "0 12px" }}
          >
            {[1, 2, 3, 5, 10].map((y) => (
              <option key={y} value={y}>
                {y} year{y > 1 ? "s" : ""}
              </option>
            ))}
          </select>

          <button
            type="submit"
            disabled={loading}
            style={{
              height: 56,
              border: 0,
              borderRadius: 10,
              padding: "0 24px",
              background: "#0f172a",
              color: "white",
              fontWeight: 700,
              fontSize: 16,
              cursor: loading ? "wait" : "pointer",
            }}
          >
            {loading ? "Checking..." : "Check availability"}
          </button>
        </form>

        {result && (
          <div
            role="status"
            aria-live="polite"
            style={{
              marginTop: 20,
              padding: 18,
              borderRadius: 12,
              background: "rgba(255,255,255,.14)",
              color: "white",
              lineHeight: 1.6,
            }}
          >
            <strong>{result.message}</strong>

            {result.data?.price != null && (
              <div>
                Price: {result.data.currency || "USD"} {result.data.price} for {years} year(s)
              </div>
            )}

            {result.type === "available" && (
              <button
                type="button"
                onClick={registerDomain}
                disabled={registering}
                style={{
                  marginTop: 14,
                  minHeight: 48,
                  border: 0,
                  borderRadius: 10,
                  padding: "0 20px",
                  background: "white",
                  color: "#075985",
                  fontWeight: 700,
                  cursor: registering ? "wait" : "pointer",
                }}
              >
                {registering ? "Registering..." : "Register this domain →"}
              </button>
            )}
          </div>
        )}
      </section>

      <section
        style={{
          marginTop: 32,
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))",
          gap: 16,
        }}
      >
        {[
          ["🔎", "Search", "Check real domain availability."],
          ["💳", "Billing", "Pay through Shopnoltd billing before registration."],
          ["⚙️", "Management", "Manage registered domains and DNS from Shopnoltd."],
        ].map(([icon, title, text]) => (
          <div
            key={title}
            style={{
              padding: 22,
              border: "1px solid #e2e8f0",
              borderRadius: 14,
              background: "white",
            }}
          >
            <div style={{ fontSize: 30 }}>{icon}</div>
            <h2 style={{ margin: "10px 0 6px", fontSize: 20 }}>{title}</h2>
            <p style={{ margin: 0, color: "#64748b", lineHeight: 1.5 }}>{text}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
