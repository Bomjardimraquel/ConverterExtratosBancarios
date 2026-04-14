import React from 'react';

export default function Header() {
  const nome = localStorage.getItem('ec_nome') || '';
  const handleLogout = async () => {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
    localStorage.removeItem('ec_nome');
    window.location.href = '/login';
  };
  return (
    <header style={{ background: 'linear-gradient(135deg, #0d2535 0%, #1a3a52 60%, #2196C9 100%)', padding: '0 2rem', height: 64, display: 'flex', alignItems: 'center', justifyContent: 'space-between', boxShadow: '0 2px 20px rgba(75,184,232,0.2)', position: 'sticky', top: 0, zIndex: 100 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <div style={{ width: 36, height: 36, borderRadius: 10, background: 'linear-gradient(135deg, #4BB8E8, #1a7aaa)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 2px 8px rgba(75,184,232,0.4)' }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="3" y1="22" x2="21" y2="22"/><line x1="6" y1="18" x2="6" y2="11"/><line x1="10" y1="18" x2="10" y2="11"/><line x1="14" y1="18" x2="14" y2="11"/><line x1="18" y1="18" x2="18" y2="11"/><polygon points="12 2 20 7 4 7"/>
          </svg>
        </div>
        <div>
          <div style={{ fontFamily: 'Open Sans, sans-serif', fontWeight: 800, fontSize: '1.05rem', color: '#fff', letterSpacing: '-0.01em' }}>ExtratoConverter</div>
          <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.45)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Prosoft · Gestão Contábil</div>
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        {nome && <span style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.55)' }}>Olá, <strong style={{ color: 'rgba(255,255,255,0.85)' }}>{nome}</strong></span>}
        <button onClick={handleLogout} style={{ padding: '0.4rem 1rem', background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)', borderRadius: 20, color: 'rgba(255,255,255,0.75)', fontSize: '0.78rem', fontWeight: 600, cursor: 'pointer' }}>
          Sair
        </button>
      </div>
    </header>
  );
}