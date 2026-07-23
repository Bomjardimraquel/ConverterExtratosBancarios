import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';

const BANCOS = [
  { key: 'bb', nome: 'Banco do Brasil', conta: '11041' },
  { key: 'sicoob', nome: 'Sicoob', conta: '11120' },
  { key: 'sicoob_aplic', nome: 'Sicoob Aplicação', conta: '11161' },
  { key: 'itau', nome: 'Itaú', conta: '11045' },
  { key: 'pagbank', nome: 'PagBank', conta: '11127' },
  { key: 'santander', nome: 'Santander', conta: '11126' },
  { key: 'bradesco', nome: 'Bradesco', conta: '11044' },
  { key: 'nordeste', nome: 'Banco do Nordeste', conta: '11042' },
];

export default function UploadStep({ onProcessar, loading }) {
  const [arquivo, setArquivo] = useState(null);
  const [banco, setBanco] = useState('');
  const [nomeEmpresa, setNomeEmpresa] = useState('');
  const [mesAno, setMesAno] = useState('');

  const onDrop = useCallback((accepted) => {
    if (accepted.length > 0) setArquivo(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false,
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!arquivo || !banco) return;
    onProcessar(arquivo, banco, nomeEmpresa, mesAno);
  };

  const inputStyle = {
    width: '100%', padding: '0.75rem 0.9rem',
    border: '1.5px solid var(--border)', borderRadius: 'var(--radius-sm)',
    fontSize: '0.9rem', background: 'var(--surface)',
    color: 'var(--text)', outline: 'none',
  };

  return (
    <>
      <div className="pagina-topbar">
        <div className="pagina-topbar-titulo">Converta extratos bancários</div>
        <div className="pagina-topbar-sub">Faça upload do PDF e gere o Excel já formatado para o Prosoft</div>
      </div>

      <form onSubmit={handleSubmit} className="pagina-corpo">
        <div className="eyebrow">Novo extrato</div>

        <div>
          <Label>Banco *</Label>
          <select value={banco} onChange={e => setBanco(e.target.value)} required
            style={{ ...inputStyle, cursor: 'pointer' }}>
            <option value="">Selecione o banco...</option>
            {BANCOS.map(b => (
              <option key={b.key} value={b.key}>{b.nome} — Acesso {b.conta}</option>
            ))}
          </select>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div>
            <Label>Empresa</Label>
            <input type="text" value={nomeEmpresa} onChange={e => setNomeEmpresa(e.target.value)}
              placeholder="Nome da empresa" style={inputStyle} />
          </div>
          <div>
            <Label>Mês/Ano</Label>
            <input type="text" value={mesAno} onChange={e => setMesAno(e.target.value)}
              placeholder="Ex: novembro/2025" style={inputStyle} />
          </div>
        </div>

        <div>
          <Label>Arquivo PDF *</Label>
          <div
            {...getRootProps()}
            className="dropzone"
            style={{
              border: `1.5px dashed ${isDragActive || arquivo ? 'var(--blue)' : 'var(--border)'}`,
              borderRadius: 'var(--radius-sm)',
              padding: '2rem',
              textAlign: 'center',
              cursor: 'pointer',
              background: isDragActive || arquivo ? 'var(--credit-bg)' : 'var(--surface)',
              transition: 'all 0.2s',
            }}
          >
            <input {...getInputProps()} />
            <div style={{ marginBottom: '0.75rem', color: arquivo ? 'var(--blue)' : 'var(--text-muted)' }}>
              {arquivo ? (
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto', display: 'block' }}>
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />
                </svg>
              ) : (
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto', display: 'block' }}>
                  <path d="M12 3v12" /><path d="m7 8 5-5 5 5" /><path d="M5 21h14" />
                </svg>
              )}
            </div>
            {arquivo ? (
              <div style={{ fontWeight: 600, color: 'var(--blue)', fontSize: '0.9rem' }}>{arquivo.name}</div>
            ) : (
              <>
                <div style={{ fontWeight: 500, color: 'var(--navy)', fontSize: '0.9rem' }}>
                  {isDragActive ? 'Solte aqui!' : 'Arraste o PDF ou clique para selecionar'}
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 4 }}>
                  Apenas arquivos .pdf
                </div>
              </>
            )}
          </div>
        </div>

        <button type="submit" disabled={!arquivo || !banco || loading} className="btn-pill btn-pill-primario">
          {loading ? 'Processando...' : 'Processar Extrato'}
        </button>
      </form>
    </>
  );
}

function Label({ children }) {
  return (
    <div style={{
      fontWeight: 600, fontSize: '0.78rem', color: 'var(--navy)',
      marginBottom: '0.4rem', letterSpacing: '0.03em', textTransform: 'uppercase',
    }}>
      {children}
    </div>
  );
}