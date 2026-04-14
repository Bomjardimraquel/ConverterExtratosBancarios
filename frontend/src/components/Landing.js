import React, { useEffect } from 'react';

const GEO = () => (
  <svg style={{ position: 'fixed', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 0 }} viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice">
    <defs>
      <radialGradient id="lo1" cx="50%" cy="50%" r="50%"><stop offset="0%" stopColor="#4BB8E8" stopOpacity="0.22"/><stop offset="100%" stopColor="#4BB8E8" stopOpacity="0"/></radialGradient>
      <radialGradient id="lo2" cx="50%" cy="50%" r="50%"><stop offset="0%" stopColor="#2196C9" stopOpacity="0.15"/><stop offset="100%" stopColor="#2196C9" stopOpacity="0"/></radialGradient>
    </defs>
    <ellipse cx="100" cy="220" rx="400" ry="400" fill="url(#lo1)"/>
    <ellipse cx="1380" cy="680" rx="440" ry="440" fill="url(#lo2)"/>
    <ellipse cx="750" cy="850" rx="300" ry="300" fill="url(#lo1)"/>
    <polygon points="1150,0 1440,0 1440,300" fill="rgba(75,184,232,0.08)"/>
    <polygon points="1230,0 1440,0 1440,210" fill="rgba(75,184,232,0.05)"/>
    <polygon points="70,380 175,295 280,380 175,465" fill="none" stroke="#4BB8E8" strokeWidth="1.5" strokeOpacity="0.22"/>
    <polygon points="95,380 175,315 255,380 175,445" fill="rgba(75,184,232,0.05)"/>
    <polygon points="0,820 110,900 0,900" fill="rgba(75,184,232,0.09)"/>
    <rect x="1060" y="70" width="88" height="88" rx="12" fill="none" stroke="#4BB8E8" strokeWidth="1.5" strokeOpacity="0.22" transform="rotate(18 1104 114)"/>
    <rect x="1073" y="83" width="62" height="62" rx="8" fill="rgba(75,184,232,0.06)" transform="rotate(18 1104 114)"/>
    <line x1="0" y1="580" x2="480" y2="80" stroke="#4BB8E8" strokeWidth="0.5" strokeOpacity="0.07"/>
    <line x1="1440" y1="180" x2="880" y2="900" stroke="#2196C9" strokeWidth="0.5" strokeOpacity="0.06"/>
    <circle cx="510" cy="110" r="3.5" fill="#4BB8E8" fillOpacity="0.28"/>
    <circle cx="960" cy="55" r="2.5" fill="#2196C9" fillOpacity="0.32"/>
    <circle cx="1310" cy="340" r="3" fill="#4BB8E8" fillOpacity="0.22"/>
    <circle cx="190" cy="690" r="2.5" fill="#2196C9" fillOpacity="0.22"/>
    <circle cx="680" cy="190" r="2" fill="#4BB8E8" fillOpacity="0.3"/>
  </svg>
);

const LandmarkIcon = ({ size = 18, color = 'white' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="3" y1="22" x2="21" y2="22"/>
    <line x1="6" y1="18" x2="6" y2="11"/>
    <line x1="10" y1="18" x2="10" y2="11"/>
    <line x1="14" y1="18" x2="14" y2="11"/>
    <line x1="18" y1="18" x2="18" y2="11"/>
    <polygon points="12 2 20 7 4 7"/>
  </svg>
);

export default function Landing() {
  useEffect(() => {
    const token = localStorage.getItem('ec_token');
    if (token) window.location.href = '/app';
  }, []);

  const s = {
    fadeUp: { animation: 'fadeUp 0.6s ease both' },
    fadeUp1: { animation: 'fadeUp 0.6s ease 0.1s both' },
    fadeUp2: { animation: 'fadeUp 0.6s ease 0.2s both' },
    fadeUp3: { animation: 'fadeUp 0.6s ease 0.3s both' },
    fadeUp4: { animation: 'fadeUp 0.6s ease 0.4s both' },
  };

  return (
    <div style={{ minHeight: '100vh', background: '#EEF7FC', color: '#0d2535', fontFamily: 'Open Sans, sans-serif', overflow: 'hidden' }}>
      <style>{`
        @keyframes fadeUp { from { opacity: 0; transform: translateY(24px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-18px)} }
      `}</style>

      <GEO />

      {/* Nav */}
      <nav style={{ position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1.25rem 3rem', background: 'rgba(238,247,252,0.8)', backdropFilter: 'blur(20px)', borderBottom: '1px solid rgba(75,184,232,0.15)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <div style={{ width: 34, height: 34, borderRadius: 9, background: 'linear-gradient(135deg, #4BB8E8, #1a7aaa)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 12px rgba(75,184,232,0.35)' }}>
            <LandmarkIcon size={17} />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: '1rem', color: '#0d2535', letterSpacing: '-0.01em' }}>ExtratoConverter</div>
            <div style={{ fontSize: '0.58rem', color: '#6a90a8', letterSpacing: '0.1em', textTransform: 'uppercase', marginTop: 1 }}>Prosoft · Gestão Contábil</div>
          </div>
        </div>
        <a href="/login" style={{ padding: '0.5rem 1.4rem', background: 'linear-gradient(135deg, #4BB8E8, #1a7aaa)', color: '#fff', borderRadius: 50, fontWeight: 700, fontSize: '0.82rem', textDecoration: 'none', boxShadow: '0 4px 16px rgba(75,184,232,0.3)' }}>
          Entrar →
        </a>
      </nav>

      {/* Hero */}
      <div style={{ position: 'relative', zIndex: 1, minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: '8rem 2rem 5rem' }}>

        <div style={{ ...s.fadeUp, display: 'inline-flex', alignItems: 'center', gap: '0.5rem', padding: '0.35rem 1.1rem', background: 'rgba(75,184,232,0.12)', border: '1px solid rgba(75,184,232,0.3)', borderRadius: 50, fontSize: '0.72rem', fontWeight: 700, color: '#2196C9', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '2rem' }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#4BB8E8', display: 'inline-block' }}/>
          Automação Contábil
        </div>

        <h1 style={{ ...s.fadeUp1, fontFamily: 'Georgia, serif', fontSize: 'clamp(2.6rem, 6.5vw, 5rem)', fontWeight: 900, lineHeight: 1.08, letterSpacing: '-0.025em', color: '#0d2535', marginBottom: '1.5rem' }}>
          Extratos bancários<br/>prontos para o <em style={{ fontStyle: 'normal', color: '#2196C9' }}>Prosoft</em>
        </h1>

        <p style={{ ...s.fadeUp2, maxWidth: 520, fontSize: '1.05rem', color: '#6a90a8', lineHeight: 1.75, fontWeight: 400, margin: '0 auto 2.75rem' }}>
          Converta PDFs de qualquer banco em planilhas Excel já classificadas e formatadas para importação no sistema contábil. Sem trabalho manual.
        </p>

        <div style={{ ...s.fadeUp3, display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap', marginBottom: '5rem' }}>
          <a href="/login" style={{ padding: '0.9rem 2.2rem', background: 'linear-gradient(135deg, #4BB8E8, #1a7aaa)', color: '#fff', border: 'none', borderRadius: 50, fontWeight: 700, fontSize: '0.95rem', textDecoration: 'none', boxShadow: '0 8px 28px rgba(75,184,232,0.35)' }}>
            Entrar no sistema →
          </a>
          <a href="#stats" style={{ padding: '0.9rem 2.2rem', background: '#fff', color: '#0d2535', border: '1.5px solid rgba(75,184,232,0.3)', borderRadius: 50, fontWeight: 600, fontSize: '0.95rem', textDecoration: 'none', boxShadow: '0 2px 10px rgba(0,0,0,0.05)' }}>
            Saiba mais
          </a>
        </div>

        {/* Stats */}
        <div id="stats" style={{ ...s.fadeUp4, display: 'flex', justifyContent: 'center', flexWrap: 'wrap', maxWidth: 780, width: '100%', background: '#fff', borderRadius: 20, boxShadow: '0 8px 48px rgba(75,184,232,0.14)', border: '1px solid rgba(75,184,232,0.12)', overflow: 'hidden' }}>
          {[
            { num: '7', label: 'Bancos\nsuportados' },
            { num: '100%', label: 'Processado\nlocalmente' },
            { num: '0', label: 'Dados\narmazenados' },
            { num: 'Auto', label: 'Classificação de\nlançamentos' },
          ].map((s, i, arr) => (
            <div key={i} style={{ flex: 1, minWidth: 150, textAlign: 'center', padding: '2.2rem 1.5rem', borderRight: i < arr.length - 1 ? '1px solid rgba(75,184,232,0.1)' : 'none' }}>
              <div style={{ fontFamily: 'Georgia, serif', fontSize: '2.4rem', fontWeight: 700, color: '#2196C9', lineHeight: 1 }}>{s.num}</div>
              <div style={{ fontSize: '0.75rem', color: '#6a90a8', marginTop: '0.45rem', lineHeight: 1.4, fontWeight: 500, whiteSpace: 'pre-line' }}>{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <footer style={{ position: 'relative', zIndex: 1, textAlign: 'center', padding: '2rem', fontSize: '0.78rem', color: '#6a90a8', borderTop: '1px solid rgba(75,184,232,0.1)' }}>
        ExtratoConverter · Dados processados localmente, nenhuma informação enviada a servidores externos
      </footer>
    </div>
  );
}