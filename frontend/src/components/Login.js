import React, { useState, useEffect } from 'react';

export default function Login() {
  const [username, setUsername] = useState('');
  const [senha, setSenha] = useState('');
  const [erro, setErro] = useState('');
  const [loading, setLoading] = useState(false);
  const [showSenha, setShowSenha] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('ec_token');
    if (token) window.location.href = '/';
  }, []);

  const fazerLogin = async (e) => {
    e.preventDefault();
    if (!username || !senha) { setErro('Preencha usuário e senha'); return; }
    setLoading(true);
    setErro('');
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, senha }),
      });
      const data = await res.json();
      if (!res.ok) { setErro(data.detail || 'Usuário ou senha incorretos'); return; }
      localStorage.setItem('ec_nome', data.nome); 
      window.location.href = '/app';
    } catch {
      setErro('Erro ao conectar com o servidor');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: '#EEF7FC', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1.5rem', position: 'relative', overflow: 'hidden' }}>
      {/* Geometric background */}
      <svg style={{ position: 'fixed', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 0 }} viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice">
        <defs>
          <radialGradient id="o1" cx="50%" cy="50%" r="50%"><stop offset="0%" stopColor="#4BB8E8" stopOpacity="0.22"/><stop offset="100%" stopColor="#4BB8E8" stopOpacity="0"/></radialGradient>
          <radialGradient id="o2" cx="50%" cy="50%" r="50%"><stop offset="0%" stopColor="#2196C9" stopOpacity="0.15"/><stop offset="100%" stopColor="#2196C9" stopOpacity="0"/></radialGradient>
        </defs>
        <ellipse cx="100" cy="220" rx="400" ry="400" fill="url(#o1)"/>
        <ellipse cx="1380" cy="680" rx="440" ry="440" fill="url(#o2)"/>
        <polygon points="1150,0 1440,0 1440,300" fill="rgba(75,184,232,0.08)"/>
        <polygon points="70,380 175,295 280,380 175,465" fill="none" stroke="#4BB8E8" strokeWidth="1.5" strokeOpacity="0.22"/>
        <polygon points="0,820 110,900 0,900" fill="rgba(75,184,232,0.09)"/>
        <line x1="0" y1="580" x2="480" y2="80" stroke="#4BB8E8" strokeWidth="0.5" strokeOpacity="0.07"/>
        <line x1="1440" y1="180" x2="880" y2="900" stroke="#2196C9" strokeWidth="0.5" strokeOpacity="0.06"/>
        <circle cx="510" cy="110" r="3.5" fill="#4BB8E8" fillOpacity="0.28"/>
        <circle cx="960" cy="55" r="2.5" fill="#2196C9" fillOpacity="0.32"/>
      </svg>

      {/* Card */}
      <div style={{ position: 'relative', zIndex: 1, width: '100%', maxWidth: 420 }}>
        <div style={{ background: '#fff', borderRadius: 24, boxShadow: '0 20px 60px rgba(75,184,232,0.16)', border: '1px solid rgba(75,184,232,0.14)', padding: '2.75rem 2.5rem' }}>

          {/* Logo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '2rem', justifyContent: 'center' }}>
            <div style={{ width: 42, height: 42, borderRadius: 11, background: 'linear-gradient(135deg, #4BB8E8, #1a7aaa)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 6px 16px rgba(75,184,232,0.35)' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="3" y1="22" x2="21" y2="22"/><line x1="6" y1="18" x2="6" y2="11"/>
                <line x1="10" y1="18" x2="10" y2="11"/><line x1="14" y1="18" x2="14" y2="11"/>
                <line x1="18" y1="18" x2="18" y2="11"/><polygon points="12 2 20 7 4 7"/>
              </svg>
            </div>
            <div>
              <div style={{ fontWeight: 800, fontSize: '1.1rem', color: '#0d2535', letterSpacing: '-0.01em' }}>ExtratoConverter</div>
              <div style={{ fontSize: '0.6rem', color: '#6a90a8', letterSpacing: '0.1em', textTransform: 'uppercase', marginTop: 1 }}>Prosoft · Gestão Contábil</div>
            </div>
          </div>

          <h1 style={{ fontFamily: 'Georgia, serif', fontSize: '1.75rem', fontWeight: 700, color: '#0d2535', marginBottom: '0.4rem', textAlign: 'center' }}>Bem-vindo</h1>
          <p style={{ fontSize: '0.85rem', color: '#6a90a8', textAlign: 'center', marginBottom: '2rem' }}>Entre com suas credenciais para acessar o sistema</p>

          {erro && (
            <div style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)', borderRadius: 10, padding: '0.75rem 1rem', fontSize: '0.82rem', color: '#ef4444', marginBottom: '1.25rem' }}>
              {erro}
            </div>
          )}

          <form onSubmit={fazerLogin}>
            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: '#0d2535', letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: '0.45rem' }}>Usuário</label>
              <input
                type="text" value={username} onChange={e => setUsername(e.target.value)}
                placeholder="seu.usuario" autoComplete="username"
                style={{ width: '100%', padding: '0.8rem 0.9rem', border: '1.5px solid rgba(75,184,232,0.25)', borderRadius: 12, fontSize: '0.9rem', color: '#0d2535', background: 'rgba(75,184,232,0.03)', outline: 'none', fontFamily: 'Open Sans, sans-serif' }}
              />
            </div>

            <div style={{ marginBottom: '0.5rem' }}>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: '#0d2535', letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: '0.45rem' }}>Senha</label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showSenha ? 'text' : 'password'} value={senha} onChange={e => setSenha(e.target.value)}
                  placeholder="••••••••" autoComplete="current-password"
                  style={{ width: '100%', padding: '0.8rem 2.5rem 0.8rem 0.9rem', border: '1.5px solid rgba(75,184,232,0.25)', borderRadius: 12, fontSize: '0.9rem', color: '#0d2535', background: 'rgba(75,184,232,0.03)', outline: 'none', fontFamily: 'Open Sans, sans-serif' }}
                />
                <button type="button" onClick={() => setShowSenha(!showSenha)}
                  style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#6a90a8', fontSize: '0.8rem', fontWeight: 600, padding: 0 }}>
                  {showSenha ? 'Ocultar' : 'Ver'}
                </button>
              </div>
            </div>

            <button
              type="submit" disabled={loading}
              style={{ width: '100%', padding: '0.9rem', marginTop: '1.25rem', background: 'linear-gradient(135deg, #4BB8E8, #1a7aaa)', color: '#fff', border: 'none', borderRadius: 12, fontFamily: 'Open Sans, sans-serif', fontWeight: 700, fontSize: '0.95rem', cursor: loading ? 'not-allowed' : 'pointer', boxShadow: '0 6px 24px rgba(75,184,232,0.35)', opacity: loading ? 0.7 : 1 }}
            >
              {loading ? 'Entrando...' : 'Entrar'}
            </button>
          </form>

          <a href="/" style={{ display: 'block', textAlign: 'center', marginTop: '1.5rem', fontSize: '0.8rem', color: '#6a90a8', textDecoration: 'none' }}>
            ← Voltar para a página inicial
          </a>
        </div>
      </div>
    </div>
  );
}