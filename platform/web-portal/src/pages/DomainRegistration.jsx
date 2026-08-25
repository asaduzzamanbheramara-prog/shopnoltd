import { useState } from "react";

const API_BASE = "/api/v1/domains";

export default function DomainRegistration() {
  const [domain, setDomain] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

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
        `${API_BASE}/check-availability?domain=${encodeURIComponent(value)}`,
        {
          headers: {
            Accept: "application/json",
          },
        }
      );

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.detail || "Domain service unavailable");
      }

      if (data.available) {
        setResult({
          type: "available",
          message: `${value} is available!`,
          data,
        });
      } else {
        setResult({
          type: "taken",
          message: data.reason || `${value} is not available.`,
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

  function registerDomain() {
    const token =
      localStorage.getItem("shopno_token") ||
      localStorage.getItem("access_token");

    if (!token) {
      window.location.href =
        `/login?next=${encodeURIComponent(
          `/domain-registration?domain=${domain}`
        )}`;
      return;
    }

    /*
     * Do not silently charge the user.
     * The backend registration endpoint must perform the
     * Shopnoltd billing authorization before Namecheap registration.
     */
    setResult({
      type: "info",
      message:
        "Domain is available. Continue through Shopnoltd billing to complete registration.",
    });
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
          style={{
            display: "flex",
            gap: 12,
            flexWrap: "wrap",
          }}
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
                Price: {result.data.currency || "USD"} {result.data.price}
              </div>
            )}

            {result.type === "available" && (
              <button
                type="button"
                onClick={registerDomain}
                style={{
                  marginTop: 14,
                  minHeight: 48,
                  border: 0,
                  borderRadius: 10,
                  padding: "0 20px",
                  background: "white",
                  color: "#075985",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                Register this domain →
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
            <h2 style={{ margin: "10px 0 6px", fontSize: 20 }}>
              {title}
            </h2>
            <p style={{ margin: 0, color: "#64748b", lineHeight: 1.5 }}>
              {text}
            </p>
          </div>
        ))}
      </section>
    </main>
  );
}
