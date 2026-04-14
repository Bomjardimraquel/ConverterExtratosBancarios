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

  const bancoSelecionado = BANCOS.find(b => b.key === banco);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!arquivo || !banco) return;
    onProcessar(arquivo, banco, nomeEmpresa, mesAno);
  };

  const inputStyle = {
    width: '100%', padding: '0.65rem 0.9rem',
    border: '1.5px solid var(--border)', borderRadius: '8px',
    fontSize: '0.9rem', background: 'var(--surface2)',
    color: 'var(--text)', outline: 'none',
    transition: 'border-color 0.2s',
  };

  return (
    <div style={{ maxWidth: 640, margin: '0 auto', width: '100%' }}>
      <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
        <h1 style={{
          fontFamily: 'var(--font-display)', fontWeight: 800,
          fontSize: 'clamp(1.6rem, 4vw, 2.2rem)',
          color: 'var(--navy)', letterSpacing: '-0.03em', marginBottom: '0.5rem',
        }}>
          Converta extratos bancários
        </h1>
        <p style={{ color: '#6a90a8', fontSize: '1rem' }}>
          Faça upload do PDF e gere o Excel já formatado para o Prosoft
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        <Card>
          {/* Banco */}
          <Label>Banco *</Label>
          <select
            value={banco}
            onChange={e => setBanco(e.target.value)}
            required
            style={{ ...inputStyle, cursor: 'pointer' }}
          >
            <option value="">Selecione o banco...</option>
            {BANCOS.map(b => (
              <option key={b.key} value={b.key}>
                {b.nome} — Acesso {b.conta}
              </option>
            ))}
          </select>

          {bancoSelecionado && (
            <div style={{
              marginTop: '0.5rem', padding: '0.5rem 0.75rem',
              background: '#f0fbff', borderRadius: 6,
              fontSize: '0.8rem', color: '#1a7aaa',
              border: '1px solid var(--credit-border)',
            }}>
              Conta Prosoft: <strong>{bancoSelecionado.conta}</strong> · {bancoSelecionado.nome}
            </div>
          )}

          <div style={{ height: '1.25rem' }} />

          {/* Empresa e Mês/Ano */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div>
              <Label>Empresa</Label>
              <input
                type="text"
                value={nomeEmpresa}
                onChange={e => setNomeEmpresa(e.target.value)}
                placeholder="Nome da empresa"
                style={inputStyle}
              />
            </div>
            <div>
              <Label>Mês/Ano</Label>
              <input
                type="text"
                value={mesAno}
                onChange={e => setMesAno(e.target.value)}
                placeholder="Ex: novembro/2025"
                style={inputStyle}
              />
            </div>
          </div>

          <div style={{ height: '1.25rem' }} />

          {/* Upload */}
          <Label>Arquivo PDF *</Label>
          <div
            {...getRootProps()}
            style={{
              border: `2px dashed ${isDragActive ? '#4BB8E8' : arquivo ? '#4BB8E8' : 'var(--border)'}`,
              borderRadius: 'var(--radius)',
              padding: '2rem',
              textAlign: 'center',
              cursor: 'pointer',
              background: isDragActive ? '#f0fbff' : arquivo ? '#f0f6ff' : 'var(--surface2)',
              transition: 'all 0.2s',
            }}
          >
            <input {...getInputProps()} />
            <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>
              {arquivo ? '✅' : isDragActive ? '📂' : '📄'}
            </div>
            {arquivo ? (
              <>
                <div style={{ fontWeight: 600, color: '#4BB8E8', fontSize: '0.95rem' }}>
                  {arquivo.name}
                </div>
                <div style={{ fontSize: '0.78rem', color: '#6a90a8', marginTop: 4 }}>
                  {(arquivo.size / 1024).toFixed(1)} KB · Clique para trocar
                </div>
              </>
            ) : (
              <>
                <div style={{ fontWeight: 600, color: 'var(--text)', fontSize: '0.95rem' }}>
                  {isDragActive ? 'Solte aqui!' : 'Arraste o PDF ou clique para selecionar'}
                </div>
                <div style={{ fontSize: '0.8rem', color: '#6a90a8', marginTop: 4 }}>
                  Apenas arquivos .pdf
                </div>
              </>
            )}
          </div>

          <div style={{ height: '1.5rem' }} />

          <button
            type="submit"
            disabled={!arquivo || !banco || loading}
            style={{
              width: '100%', padding: '0.9rem',
              background: (!arquivo || !banco || loading)
                ? 'var(--border)' : 'linear-gradient(135deg, #4BB8E8, #1a7aaa)',
              color: (!arquivo || !banco || loading) ? 'var(--text-muted)' : '#fff',
              border: 'none', borderRadius: 'var(--radius)',
              fontFamily: 'var(--font-display)', fontWeight: 700,
              fontSize: '1rem', letterSpacing: '0.01em',
              cursor: (!arquivo || !banco || loading) ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s',
              boxShadow: (!arquivo || !banco || loading) ? 'none' : 'var(--shadow)',
            }}
          >
            {loading ? '⏳ Processando...' : '🚀 Processar Extrato'}
          </button>
        </Card>
      </form>
    </div>
  );
}

function Card({ children }) {
  return (
    <div style={{
      background: 'var(--surface)', borderRadius: 'var(--radius)',
      padding: '1.75rem', boxShadow: 'var(--shadow)',
      border: '1px solid var(--border)',
    }}>
      {children}
    </div>
  );
}

function Label({ children }) {
  return (
    <div style={{
      fontWeight: 600, fontSize: '0.82rem',
      color: 'var(--navy)', marginBottom: '0.4rem',
      letterSpacing: '0.04em', textTransform: 'uppercase',
    }}>
      {children}
    </div>
  );
}