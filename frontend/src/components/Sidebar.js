import React from 'react';

const ITENS = [
  { key: '1', label: 'Extrato Simples' },
  { key: '2', label: 'Conciliação Completa' },
];

export default function Sidebar({ modulo, onTrocarModulo }) {
  const nome = localStorage.getItem('ec_nome') || '';
  const iniciais = nome ? nome.trim().split(/\s+/).map(p => p[0]).slice(0, 2).join('').toUpperCase() : '?';

  const handleLogout = async () => {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
    localStorage.removeItem('ec_nome');
    window.location.href = '/login';
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-marca">
        <img src="/logo_concilia.png" alt="Concilia" className="sidebar-marca-icone" />
        <span className="sidebar-marca-texto">Concilia</span>
      </div>

      <nav className="sidebar-nav">
        {ITENS.map(item => (
          <button
            key={item.key}
            className={`sidebar-nav-item ${modulo === item.key ? 'ativo' : ''}`}
            onClick={() => onTrocarModulo(item.key)}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <div className="sidebar-rodape">
        <div className="sidebar-avatar">{iniciais}</div>
        <div>
          <div className="sidebar-usuario-nome">{nome || 'Usuário'}</div>
          <button className="sidebar-sair" onClick={handleLogout}>Sair</button>
        </div>
      </div>
    </aside>
  );
}