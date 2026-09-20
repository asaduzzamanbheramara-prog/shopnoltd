import { Link } from 'react-router-dom'

const THREECX_URL = 'https://1240.3cx.cloud/'

export default function Phone() {
  return (
    <main
      style={{
        maxWidth: 1180,
        margin: '0 auto',
        padding: 'clamp(24px,6vw,52px) clamp(14px,4vw,24px) 80px',
        boxSizing: 'border-box',
        fontFamily: 'system-ui,sans-serif',
      }}
    >
      <section
        style={{
          padding: 'clamp(28px,6vw,56px)',
          borderRadius: 24,
          background: 'linear-gradient(135deg,#0ea5e9,#0369a1)',
          color: 'white',
        }}
      >
        <div style={{ maxWidth: 820 }}>
          <div style={{ fontSize: 52 }}>📞</div>

          <h1
            style={{
              fontSize: 'clamp(38px,7vw,64px)',
              lineHeight: 1.05,
              margin: '10px 0 18px',
            }}
          >
            Shopnoltd Phone
          </h1>

          <p
            style={{
              fontSize: 'clamp(17px,2.2vw,21px)',
              lineHeight: 1.7,
              opacity: 0.96,
              margin: 0,
            }}
          >
            Business calling, team communication, meetings and
            browser-based phone access through the Shopnoltd
            3CX phone system.
          </p>

          <div
            style={{
              display: 'flex',
              gap: 10,
              flexWrap: 'wrap',
              marginTop: 26,
            }}
          >
            <a
              href={THREECX_URL}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                padding: '13px 20px',
                borderRadius: 10,
                background: 'white',
                color: '#0369a1',
                fontWeight: 800,
                textDecoration: 'none',
              }}
            >
              Open Shopnoltd Phone →
            </a>

            <Link
              to="/services"
              style={{
                padding: '13px 20px',
                borderRadius: 10,
                border: '1px solid rgba(255,255,255,.65)',
                color: 'white',
                fontWeight: 800,
                textDecoration: 'none',
              }}
            >
              All services
            </Link>
          </div>
        </div>
      </section>

      <section
        style={{
          marginTop: 28,
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))',
          gap: 16,
        }}
      >
        <article
          style={{
            background: 'white',
            border: '1px solid #e2e8f0',
            borderRadius: 16,
            padding: 22,
            boxShadow: '0 3px 12px rgba(15,23,42,.06)',
          }}
        >
          <div style={{ fontSize: 30 }}>👥</div>
          <h2 style={{ margin: '10px 0 8px' }}>Team</h2>
          <p
            style={{
              margin: 0,
              color: '#64748b',
              lineHeight: 1.6,
            }}
          >
            Manage Shopnoltd phone users, availability and
            internal communication through the 3CX Web Client.
          </p>
        </article>

        <article
          style={{
            background: 'white',
            border: '1px solid #e2e8f0',
            borderRadius: 16,
            padding: 22,
            boxShadow: '0 3px 12px rgba(15,23,42,.06)',
          }}
        >
          <div style={{ fontSize: 30 }}>📞</div>
          <h2 style={{ margin: '10px 0 8px' }}>Calling</h2>
          <p
            style={{
              margin: 0,
              color: '#64748b',
              lineHeight: 1.6,
            }}
          >
            Use the browser-based 3CX dialer for supported
            internal and external calling.
          </p>
        </article>

        <article
          style={{
            background: 'white',
            border: '1px solid #e2e8f0',
            borderRadius: 16,
            padding: 22,
            boxShadow: '0 3px 12px rgba(15,23,42,.06)',
          }}
        >
          <div style={{ fontSize: 30 }}>💬</div>
          <h2 style={{ margin: '10px 0 8px' }}>Chat</h2>
          <p
            style={{
              margin: 0,
              color: '#64748b',
              lineHeight: 1.6,
            }}
          >
            Access supported 3CX chat and communication
            functions from the Web Client.
          </p>
        </article>

        <article
          style={{
            background: 'white',
            border: '1px solid #e2e8f0',
            borderRadius: 16,
            padding: 22,
            boxShadow: '0 3px 12px rgba(15,23,42,.06)',
          }}
        >
          <div style={{ fontSize: 30 }}>🎥</div>
          <h2 style={{ margin: '10px 0 8px' }}>Meetings</h2>
          <p
            style={{
              margin: 0,
              color: '#64748b',
              lineHeight: 1.6,
            }}
          >
            Start or schedule supported 3CX audio and video
            conferences from the Web Client.
          </p>
        </article>
      </section>

      <section
        style={{
          marginTop: 28,
          padding: 24,
          borderRadius: 16,
          background: '#f8fafc',
          border: '1px solid #e2e8f0',
        }}
      >
        <h2 style={{ marginTop: 0 }}>Current Shopnoltd Phone system</h2>

        <div
          style={{
            display: 'grid',
            gap: 10,
            color: '#475569',
            lineHeight: 1.6,
          }}
        >
          <div>
            <strong>Platform:</strong> 3CX SMB
          </div>

          <div>
            <strong>System:</strong> Shopnoltd Phone
          </div>

          <div>
            <strong>3CX system:</strong> 1240.3cx.cloud
          </div>

          <div>
            <strong>Current user:</strong> AZ / ASAD, ZAMAN16410
          </div>

          <div>
            <strong>Status:</strong> Managed through the 3CX Web Client
          </div>
        </div>

        <div
          style={{
            marginTop: 20,
            padding: 16,
            borderRadius: 12,
            background: '#eff6ff',
            border: '1px solid #bfdbfe',
            color: '#1e40af',
            lineHeight: 1.6,
          }}
        >
          <strong>Telephone numbers:</strong> A normal PSTN/mobile
          telephone number and external telephone calling require
          an appropriate SIP trunk/DID provider. The Shopnoltd
          website integration itself does not create a telephone
          number.
        </div>
      </section>

      <section
        style={{
          marginTop: 28,
          padding: 24,
          borderRadius: 16,
          background: 'white',
          border: '1px solid #e2e8f0',
        }}
      >
        <h2 style={{ marginTop: 0 }}>Open 3CX</h2>

        <p
          style={{
            color: '#64748b',
            lineHeight: 1.6,
            marginBottom: 18,
          }}
        >
          The full 3CX phone interface runs in its own browser
          application. Shopnoltd provides the central entry point,
          while 3CX handles the phone-system interface.
        </p>

        <a
          href={THREECX_URL}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: 'inline-block',
            padding: '12px 18px',
            borderRadius: 10,
            background: '#0284c7',
            color: 'white',
            fontWeight: 800,
            textDecoration: 'none',
          }}
        >
          Launch 3CX Web Client →
        </a>
      </section>
    </main>
  )
}
