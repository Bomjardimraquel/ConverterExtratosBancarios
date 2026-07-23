import React from 'react';

export default function Header() {
  const nome = localStorage.getItem('ec_nome') || '';
  const handleLogout = async () => {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
    localStorage.removeItem('ec_nome');
    window.location.href = '/login';
  };
  return (
    <header style={{ background: 'linear-gradient(135deg, #3A3630 0%, #52493F 60%, #6B7A5E 100%)', padding: '0 2rem', height: 64, display: 'flex', alignItems: 'center', justifyContent: 'space-between', boxShadow: '0 2px 20px rgba(107,122,94,0.2)', position: 'sticky', top: 0, zIndex: 100 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <img src="/logo_concilia.png" alt="Concilia" style={{ width: 36, height: 36, objectFit: 'contain' }} />
        <div>
          <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: '1.05rem', color: '#fff', letterSpacing: '-0.01em' }}>Concilia</div>
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