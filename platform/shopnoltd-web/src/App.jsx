import React from "react";

const host = window.location.hostname;

const APPS = {
  "shopnoltd.dpdns.org": {
    title: "Shopnoltd",
    subtitle: "Shopno Database Firm",
    type: "Platform",
  },

  "billing.shopnoltd.dpdns.org": {
    title: "Shopnoltd Billing",
    subtitle: "Billing, invoices and account transactions",
    type: "Billing",
  },

  "payment.shopnoltd.dpdns.org": {
    title: "Shopnoltd Payment",
    subtitle: "Payments, deposits and payment gateways",
    type: "Payment",
  },

  "exchange.shopnoltd.dpdns.org": {
    title: "Shopnoltd Exchange",
    subtitle: "Exchange, balances and transactions",
    type: "Exchange",
  },

  "admin.shopnoltd.dpdns.org": {
    title: "Shopnoltd Admin",
    subtitle: "Administration and platform management",
    type: "Admin",
  },

  "support.shopnoltd.dpdns.org": {
    title: "Shopnoltd Support",
    subtitle: "Customer support and service management",
    type: "Support",
  },
};

const app =
  APPS[host] || {
    title: "Shopnoltd",
    subtitle: "Shopno Database Firm",
    type: "Platform",
  };

function App() {
  return (
    <main className="page">
      <section className="card">
        <div className="brand">SHOPNO DATABASE FIRM</div>

        <h1>{app.title}</h1>

        <p className="subtitle">{app.subtitle}</p>

        <div className="badge">{app.type}</div>

        <div className="panel">
          <div>
            <strong>Service</strong>
            <span>{app.type}</span>
          </div>

          <div>
            <strong>Domain</strong>
            <span>{host}</span>
          </div>

          <div>
            <strong>Status</strong>
            <span>Shopnoltd Platform</span>
          </div>
        </div>

        <div className="actions">
          <a href="/">Home</a>
          <a href="/api/health">API Health</a>
          <a href="/api/docs">API Docs</a>
        </div>

        <p className="footer">
          Shopnoltd Platform · Shopno Database Firm
        </p>
      </section>
    </main>
  );
}

export default App;
