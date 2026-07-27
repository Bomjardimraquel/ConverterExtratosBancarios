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
              <option key={b.key} value={b.key}>{b.nome}: Acesso {b.conta}</option>
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
              placeholder="Ex: 01/2026" style={inputStyle} />
          </div>
        </div>

        <div>
          <Label>Arquivo PDF *</Label>
          <div
            {...getRootProps()}
            className="dropzone"
            style={{
              border: `1.5px dashed ${isDragActive || arquivo ? 'var(--musgo)' : 'var(--border)'}`,
              borderRadius: 'var(--radius-sm)', padding: '1.1rem 1rem',
              textAlign: 'center', cursor: 'pointer',
              background: isDragActive || arquivo ? 'var(--credit-bg)' : 'var(--surface)',
              transition: 'all 0.2s',
            }}
          >
            <input {...getInputProps()} />
            {arquivo ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, fontWeight: 600, color: 'var(--musgo)', fontSize: '0.85rem' }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                {arquivo.name}
              </div>
            ) : (
              <>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto 0.4rem', display: 'block' }}>
                  <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242" /><path d="M12 12v9" /><path d="m16 16-4-4-4 4" />
                </svg>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {isDragActive ? 'Solte aqui!' : 'Arraste ou clique para selecionar (PDF)'}
                </div>
              </>
            )}
          </div>
        </div>

        <button type="submit" disabled={!arquivo || !banco || loading} className="btn-pill btn-pill-primario">
          {loading ? 'Processando...' : 'Processar extrato'}
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