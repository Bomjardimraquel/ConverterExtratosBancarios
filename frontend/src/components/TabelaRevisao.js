import React, { useState } from 'react';

const CONTAS = {
  '11041': 'BB', '11142': 'BB Rende Fácil', '21381': 'Empréstimo BB',
  '11120': 'Sicoob', '21325': 'Empréstimo Sicoob',
  '11045': 'Itaú', '11146': 'Itaú Aplic.', '11127': 'PagBank',
  '11126': 'Santander', '11044': 'Bradesco', '11042': 'Nordeste',
  '11002': 'Caixa',
  '53502': 'Desp. Bancárias', '53514': 'IOF', '53501': 'Juros',
  '53065': 'Diversos/Impostos',
};

const TODAS_CONTAS = Object.entries(CONTAS).map(([k, v]) => ({ codigo: k, nome: v }));

export default function TabelaRevisao({ lancamentos, onLancamentosChange, onExportar, onVoltar, loading, banco, nomeEmpresa, mesAno }) {
  const [filtro, setFiltro] = useState('todos');
  const [busca, setBusca] = useState('');
  const [editandoIdx, setEditandoIdx] = useState(null);

  const atualizarLancamento = (idx, campo, valor) => {
    const novos = [...lancamentos];
    novos[idx] = { ...novos[idx], [campo]: valor };
    // Recalcula tipo se mudar contas
    if (campo === 'conta_debito' || campo === 'conta_credito') {
      novos[idx].requer_revisao = false;
    }
    onLancamentosChange(novos);
  };

  const removerLancamento = (idx) => {
    onLancamentosChange(lancamentos.filter((_, i) => i !== idx));
  };

  const filtrados = lancamentos.filter(l => {
    const matchFiltro =
      filtro === 'todos' ? true :
      filtro === 'credito' ? l.tipo === 'Crédito' :
      filtro === 'debito' ? l.tipo === 'Débito' :
      filtro === 'revisao' ? l.requer_revisao : true;
    const matchBusca = busca === '' || l.descricao.toLowerCase().includes(busca.toLowerCase());
    return matchFiltro && matchBusca;
  });

  const totalCreditos = lancamentos.filter(l => l.tipo === 'Crédito').reduce((s, l) => s + l.valor, 0);
  const totalDebitos = lancamentos.filter(l => l.tipo === 'Débito').reduce((s, l) => s + l.valor, 0);
  const revisoes = lancamentos.filter(l => l.requer_revisao).length;

  const fmt = (v) => v.toLocaleString('pt-BR', { minimumFractionDigits: 2 });

  return (
    <div style={{ width: '100%', maxWidth: 1100, margin: '0 auto' }}>
      {/* Cabeçalho */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: '1.5rem', color: 'var(--navy)', letterSpacing: '-0.02em' }}>
            Revisar Lançamentos
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: 2 }}>
            {nomeEmpresa && <><strong>{nomeEmpresa}</strong> · </>}{banco} {mesAno && `· ${mesAno}`}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button onClick={onVoltar} style={btnSecondary}>← Novo extrato</button>
          <button onClick={onExportar} disabled={loading} style={btnPrimary}>
            {loading ? 'Gerando...' : 'Exportar Excel'}
          </button>
        </div>
      </div>

      {/* Cards resumo */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        <ResumoCard label="Total de Lançamentos" valor={lancamentos.length} cor="var(--blue)" />
        <ResumoCard label="Total Créditos" valor={`R$ ${fmt(totalCreditos)}`} cor="var(--accent-dark)" bg="var(--credit-bg)" />
        <ResumoCard label="Total Débitos" valor={`R$ ${fmt(totalDebitos)}`} cor="#b45309" bg="var(--debit-bg)" />
        {revisoes > 0 && <ResumoCard label="Para Revisão" valor={revisoes} cor="var(--danger)" bg="var(--review-bg)" />}
      </div>

      {/* Filtros e busca */}
      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
        {['todos', 'credito', 'debito', 'revisao'].map(f => (
          <button key={f} onClick={() => setFiltro(f)} style={{
            padding: '0.4rem 1rem', borderRadius: 20,
            border: '1.5px solid', fontSize: '0.82rem', fontWeight: 600,
            cursor: 'pointer', transition: 'all 0.15s',
            borderColor: filtro === f ? 'var(--blue)' : 'var(--border)',
            background: filtro === f ? 'var(--blue)' : 'var(--surface)',
            color: filtro === f ? '#fff' : 'var(--text-muted)',
          }}>
            {{ todos: 'Todos', credito: '⬆ Créditos', debito: '⬇ Débitos', revisao: '⚠ Revisão' }[f]}
          </button>
        ))}
        <input
          type="text"
          placeholder="🔍 Buscar descrição..."
          value={busca}
          onChange={e => setBusca(e.target.value)}
          style={{
            marginLeft: 'auto', padding: '0.4rem 0.9rem',
            border: '1.5px solid var(--border)', borderRadius: 20,
            fontSize: '0.85rem', outline: 'none', background: 'var(--surface)',
            minWidth: 200,
          }}
        />
      </div>

      {/* Tabela */}
      <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius)', boxShadow: 'var(--shadow)', border: '1px solid var(--border)', overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ background: 'var(--navy)' }}>
                {['Data', 'Descrição', 'Tipo', 'Débito', 'Crédito', 'Valor (R$)', ''].map(h => (
                  <th key={h} style={{
                    padding: '0.75rem 0.85rem', textAlign: h === 'Valor (R$)' ? 'right' : 'left',
                    color: 'rgba(255,255,255,0.85)', fontFamily: 'var(--font-display)',
                    fontWeight: 700, fontSize: '0.75rem', letterSpacing: '0.06em',
                    whiteSpace: 'nowrap',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtrados.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                    Nenhum lançamento encontrado.
                  </td>
                </tr>
              ) : filtrados.map((l, i) => {
                const idxReal = lancamentos.indexOf(l);
                const editando = editandoIdx === idxReal;
                const rowBg = l.requer_revisao ? 'var(--review-bg)' :
                  l.tipo === 'Crédito' ? 'var(--credit-bg)' : 'var(--debit-bg)';
                const borderLeft = l.requer_revisao ? '3px solid var(--danger)' :
                  l.tipo === 'Crédito' ? '3px solid var(--credit-border)' : '3px solid var(--debit-border)';

                return (
                  <tr key={idxReal} style={{
                    background: editando ? '#f0f6ff' : (i % 2 === 0 ? rowBg : 'var(--surface)'),
                    borderLeft,
                    borderBottom: '1px solid var(--border)',
                    transition: 'background 0.15s',
                  }}>
                    {/* Data */}
                    <td style={{ padding: '0.6rem 0.85rem', whiteSpace: 'nowrap', fontWeight: 500 }}>
                      {editando ? (
                        <input value={l.data} onChange={e => atualizarLancamento(idxReal, 'data', e.target.value)}
                          style={tdInput} />
                      ) : l.data}
                    </td>
                    {/* Descrição */}
                    <td style={{ padding: '0.6rem 0.85rem', maxWidth: 320 }}>
                      {editando ? (
                        <input value={l.descricao} onChange={e => atualizarLancamento(idxReal, 'descricao', e.target.value)}
                          style={{ ...tdInput, width: '100%' }} />
                      ) : (
                        <span title={l.descricao} style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 300 }}>
                          {l.requer_revisao && <span style={{ color: 'var(--danger)', marginRight: 4 }}>⚠</span>}
                          {l.descricao}
                        </span>
                      )}
                    </td>
                    {/* Tipo */}
                    <td style={{ padding: '0.6rem 0.85rem', whiteSpace: 'nowrap' }}>
                      {editando ? (
                        <select value={l.tipo} onChange={e => atualizarLancamento(idxReal, 'tipo', e.target.value)} style={tdInput}>
                          <option>Crédito</option>
                          <option>Débito</option>
                        </select>
                      ) : (
                        <span style={{
                          padding: '0.2rem 0.6rem', borderRadius: 12, fontSize: '0.75rem', fontWeight: 700,
                          background: l.tipo === 'Crédito' ? '#dcfce7' : '#fef3c7',
                          color: l.tipo === 'Crédito' ? '#166534' : '#92400e',
                        }}>{l.tipo}</span>
                      )}
                    </td>
                    {/* Débito */}
                    <td style={{ padding: '0.6rem 0.85rem', whiteSpace: 'nowrap' }}>
                      {editando ? (
                        <select value={l.conta_debito} onChange={e => atualizarLancamento(idxReal, 'conta_debito', e.target.value)} style={tdInput}>
                          {TODAS_CONTAS.map(c => <option key={c.codigo} value={c.codigo}>{c.codigo} - {c.nome}</option>)}
                        </select>
                      ) : (
                        <span title={CONTAS[l.conta_debito] || ''}>
                          <strong>{l.conta_debito}</strong>
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginLeft: 4 }}>
                            {CONTAS[l.conta_debito] || ''}
                          </span>
                        </span>
                      )}
                    </td>
                    {/* Crédito */}
                    <td style={{ padding: '0.6rem 0.85rem', whiteSpace: 'nowrap' }}>
                      {editando ? (
                        <select value={l.conta_credito} onChange={e => atualizarLancamento(idxReal, 'conta_credito', e.target.value)} style={tdInput}>
                          {TODAS_CONTAS.map(c => <option key={c.codigo} value={c.codigo}>{c.codigo} - {c.nome}</option>)}
                        </select>
                      ) : (
                        <span title={CONTAS[l.conta_credito] || ''}>
                          <strong>{l.conta_credito}</strong>
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginLeft: 4 }}>
                            {CONTAS[l.conta_credito] || ''}
                          </span>
                        </span>
                      )}
                    </td>
                    {/* Valor */}
                    <td style={{ padding: '0.6rem 0.85rem', textAlign: 'right', fontWeight: 600, whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums' }}>
                      {editando ? (
                        <input type="number" step="0.01" value={l.valor}
                          onChange={e => atualizarLancamento(idxReal, 'valor', parseFloat(e.target.value) || 0)}
                          style={{ ...tdInput, width: 110, textAlign: 'right' }} />
                      ) : (
                        <span style={{ color: l.tipo === 'Crédito' ? 'var(--accent-dark)' : '#b45309' }}>
                          R$ {fmt(l.valor)}
                        </span>
                      )}
                    </td>
                    {/* Ações */}
                    <td style={{ padding: '0.6rem 0.75rem', whiteSpace: 'nowrap' }}>
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button onClick={() => setEditandoIdx(editando ? null : idxReal)}
                          title={editando ? 'Salvar' : 'Editar'}
                          style={btnIcon(editando ? 'var(--accent)' : 'var(--blue-light)')}>
                          {editando ? '✓' : '✏️'}
                        </button>
                        <button onClick={() => removerLancamento(idxReal)} title="Remover"
                          style={btnIcon('var(--danger)')}>🗑</button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div style={{ padding: '0.75rem 1rem', borderTop: '1px solid var(--border)', background: 'var(--surface2)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Mostrando {filtrados.length} de {lancamentos.length} lançamentos
        </div>
      </div>
    </div>
  );
}

function ResumoCard({ label, valor, icon, cor, bg }) {
  return (
    <div style={{
      background: bg || 'var(--surface)', borderRadius: 'var(--radius-sm)',
      padding: '1rem 1.25rem', boxShadow: 'var(--shadow)',
      border: '1px solid var(--border)',
    }}>
      <div style={{ fontSize: '1.3rem', marginBottom: 4 }}>{icon}</div>
      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 2 }}>{label}</div>
      <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '1.1rem', color: cor || 'var(--text)' }}>{valor}</div>
    </div>
  );
}

const tdInput = {
  padding: '0.3rem 0.5rem', border: '1.5px solid var(--blue-light)',
  borderRadius: 6, fontSize: '0.82rem', outline: 'none',
  background: '#fff', color: 'var(--text)',
};

const btnPrimary = {
  padding: '0.6rem 1.3rem',
  background: 'linear-gradient(135deg, #4BB8E8, #1a7aaa)',
  color: '#fff', border: 'none', borderRadius: 'var(--radius-sm)',
  fontFamily: 'var(--font-display)', fontWeight: 700,
  fontSize: '0.9rem', cursor: 'pointer', boxShadow: 'var(--shadow)',
};

const btnSecondary = {
  padding: '0.6rem 1.1rem',
  background: 'var(--surface)', color: 'var(--navy)',
  border: '1.5px solid var(--border)', borderRadius: 'var(--radius-sm)',
  fontFamily: 'var(--font-display)', fontWeight: 600,
  fontSize: '0.9rem', cursor: 'pointer',
};

const btnIcon = (cor) => ({
  width: 28, height: 28, display: 'flex', alignItems: 'center', justifyContent: 'center',
  background: 'transparent', border: `1px solid ${cor}`, borderRadius: 6,
  fontSize: '0.8rem', cursor: 'pointer', color: cor, transition: 'all 0.15s',
});
