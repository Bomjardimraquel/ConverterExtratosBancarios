import React, { useState } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import Header from './components/Header';
import UploadStep from './components/UploadStep';
import TabelaRevisao from './components/TabelaRevisao';
import { processarExtrato, exportarExcel } from './utils/api';

export default function App() {
  const [etapa, setEtapa] = useState('upload'); 
  const [lancamentos, setLancamentos] = useState([]);
  const [meta, setMeta] = useState({ banco: '', nomeEmpresa: '', mesAno: '' });
  const [loading, setLoading] = useState(false);

  const handleProcessar = async (arquivo, banco, nomeEmpresa, mesAno) => {
    setLoading(true);
    try {
      const res = await processarExtrato(arquivo, banco, nomeEmpresa, mesAno);
      setLancamentos(res.data.lancamentos);
      setMeta({ banco, nomeEmpresa, mesAno });
      setEtapa('revisao');
      toast.success(`${res.data.total} lançamentos encontrados!`);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Erro ao processar o arquivo.';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleExportar = async () => {
    setLoading(true);
    try {
      await exportarExcel(lancamentos, meta.banco, meta.nomeEmpresa, meta.mesAno);
      toast.success('Excel gerado com sucesso!');
    } catch {
      toast.error('Erro ao gerar o Excel.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            fontFamily: 'var(--font-body)',
            fontSize: '0.9rem',
            borderRadius: '10px',
            boxShadow: 'var(--shadow-lg)',
          },
        }}
      />
      <Header />
      <main style={{
        flex: 1, padding: '2.5rem 1.5rem',
        display: 'flex', flexDirection: 'column', alignItems: 'center',
      }}>
        {/* Etapas */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: '0.5rem',
          marginBottom: '2.5rem',
        }}>
          {[
            { n: 1, label: 'Upload', etapa: 'upload' },
            { n: 2, label: 'Revisão', etapa: 'revisao' },
          ].map((s, i, arr) => (
            <React.Fragment key={s.n}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <div style={{
                  width: 30, height: 30, borderRadius: '50%',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontWeight: 700, fontSize: '0.85rem',
                  background: etapa === s.etapa ? 'var(--primary)' : etapa === 'revisao' && s.etapa === 'upload' ? 'var(--secondary)' : 'var(--border)',
                  color: etapa === s.etapa || (etapa === 'revisao' && s.etapa === 'upload') ? '#fff' : 'var(--text-muted)',
                  transition: 'all 0.3s',
                }}>
                  {etapa === 'revisao' && s.etapa === 'upload' ? '✓' : s.n}
                </div>
                <span style={{
                  fontSize: '0.82rem', fontWeight: 600,
                  color: etapa === s.etapa ? 'var(--navy)' : 'var(--text-muted)',
                  fontFamily: 'var(--font-display)',
                }}>{s.label}</span>
              </div>
              {i < arr.length - 1 && (
                <div style={{
                  width: 40, height: 2,
                  background: etapa === 'revisao' ? 'var(--secondary)' : 'var(--border)',
                  borderRadius: 2, transition: 'background 0.3s',
                }} />
              )}
            </React.Fragment>
          ))}
        </div>

        {etapa === 'upload' && (
          <UploadStep onProcessar={handleProcessar} loading={loading} />
        )}

        {etapa === 'revisao' && (
          <TabelaRevisao
            lancamentos={lancamentos}
            onLancamentosChange={setLancamentos}
            onExportar={handleExportar}
            onVoltar={() => { setEtapa('upload'); setLancamentos([]); }}
            loading={loading}
            banco={meta.banco}
            nomeEmpresa={meta.nomeEmpresa}
            mesAno={meta.mesAno}
          />
        )}
      </main>

      <footer style={{
        textAlign: 'center', padding: '1rem',
        fontSize: '0.75rem', color: 'var(--text-muted)',
        borderTop: '1px solid var(--border)',
      }}>
        ExtratoConverter · Dados processados localmente, nenhuma informação enviada a servidores externos
      </footer>
    </>
  );
}
