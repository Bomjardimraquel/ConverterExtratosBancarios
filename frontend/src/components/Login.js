import React, { useState, useEffect } from 'react';

export default function Login() {
  const [username, setUsername] = useState('');
  const [senha, setSenha] = useState('');
  const [manterConectado, setManterConectado] = useState(true);
  const [erro, setErro] = useState('');
  const [loading, setLoading] = useState(false);
  const [showSenha, setShowSenha] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('ec_token');
    if (token) window.location.href = '/app';
  }, []);

  const fazerLogin = async (e) => {
    e.preventDefault();
    if (!username || !senha) { setErro('Preencha e-mail e senha'); return; }
    setLoading(true);
    setErro('');
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, senha }),
      });
      const data = await res.json();
      if (!res.ok) { setErro(data.detail || 'E-mail ou senha incorretos'); return; }
      localStorage.setItem('ec_nome', data.nome);
      window.location.href = '/app';
    } catch {
      setErro('Erro ao conectar com o servidor');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-lado-texto">
        <h1 className="login-titulo">Bem-vindo(a) contador(a),</h1>
        <p className="login-subtitulo">Para acessar, faça o login com seu e-mail e senha.</p>
      </div>

      <div className="login-lado-card">
        <div className="login-card">
          {erro && <div className="login-erro">{erro}</div>}

          <form onSubmit={fazerLogin}>
            <label className="login-label" htmlFor="login-email">E-mail</label>
            <input
              id="login-email"
              className="login-input"
              type="email" value={username} onChange={e => setUsername(e.target.value)}
              placeholder="seu.email@escritorio.com.br" autoComplete="username"
            />

            <label className="login-label" htmlFor="login-senha" style={{ marginTop: '1.1rem' }}>Senha</label>
            <div style={{ position: 'relative' }}>
              <input
                id="login-senha"
                className="login-input"
                type={showSenha ? 'text' : 'password'} value={senha} onChange={e => setSenha(e.target.value)}
                placeholder="••••••••" autoComplete="current-password"
                style={{ paddingRight: '3rem' }}
              />
              <button type="button" onClick={() => setShowSenha(!showSenha)} className="login-toggle-senha">
                {showSenha ? 'Ocultar' : 'Ver'}
              </button>
            </div>

            <label className="login-manter">
              <input type="checkbox" checked={manterConectado} onChange={e => setManterConectado(e.target.checked)} />
              Mantenha-me conectado
            </label>

            <button type="submit" disabled={loading} className="login-botao">
              {loading ? 'Entrando...' : 'Entrar'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}