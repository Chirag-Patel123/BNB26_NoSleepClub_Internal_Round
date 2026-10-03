import { Icon } from './ui.jsx'

export function NotFound({ onGoHome }) {
  return (
    <div className="card" style={{ maxWidth: 640, margin: '48px auto', padding: '48px 32px', textAlign: 'center', border: '1px solid var(--ln)' }}>
      <span className="chip big" style={{ background: 'rgba(255, 87, 34, 0.1)', color: 'var(--bad)', width: 64, height: 64, margin: '0 auto 20px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Icon n="radar" style={{ fontSize: 32 }} />
      </span>
      <h1 style={{ fontSize: '2.5rem', color: 'var(--bad)', margin: '0 0 12px 0', fontFamily: 'monospace' }}>
        404 // SIGNAL LOST
      </h1>
      <h2 style={{ fontSize: '1.25rem', color: 'var(--fg)', margin: '0 0 16px 0', fontWeight: 600 }}>
        Telemetry Trajectory Not Found
      </h2>
      <p className="mu" style={{ maxWidth: 480, margin: '0 auto 28px', lineHeight: 1.6 }}>
        The requested span, checkpoint trajectory, or page coordinates do not exist in this Black Box session.
      </p>
      <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
        <button className="btn pri" onClick={onGoHome}>
          <Icon n="dashboard" /> Return to Overview Dashboard
        </button>
      </div>
    </div>
  )
}
