import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster, toast } from 'react-hot-toast';
import Header from './components/Header';
import UploadStep from './components/UploadStep';
import TabelaRevisao from './components/TabelaRevisao';
import Login from './components/Login';
import Landing from './components/Landing';
import { processarExtrato, exportarExcel } from './utils/api';

function AppContent() {
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
      toast.success(res.data.total + ' lançamentos encontrados!');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erro ao processar o arquivo.');
    } finally { setLoading(false); }
  };

  const handleExportar = async () => {
    setLoading(true);
    try {
      await exportarExcel(lancamentos, meta.banco, meta.nomeEmpresa, meta.mesAno);
      toast.success('Excel gerado com sucesso!');
    } catch { toast.error('Erro ao gerar o Excel.'); }
    finally { setLoading(false); }
  };

  return (
    <>
      <Header />
      <main style={{ flex: 1, padding: '2.5rem 1.5rem', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '2.5rem' }}>
          {[{ n: 1, label: 'Upload', e: 'upload' }, { n: 2, label: 'Revisão', e: 'revisao' }].map((s, i, arr) => (
            <React.Fragment key={s.n}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <div style={{ width: 30, height: 30, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.85rem', transition: 'all 0.3s', background: etapa === s.e ? '#2196C9' : etapa === 'revisao' && s.e === 'upload' ? '#4BB8E8' : '#d0e8f5', color: etapa === s.e || (etapa === 'revisao' && s.e === 'upload') ? '#fff' : '#6a90a8' }}>
                  {etapa === 'revisao' && s.e === 'upload' ? '✓' : s.n}
                </div>
                <span style={{ fontSize: '0.82rem', fontWeight: 600, color: etapa === s.e ? '#0d2535' : '#6a90a8' }}>{s.label}</span>
              </div>
              {i < arr.length - 1 && <div style={{ width: 40, height: 2, borderRadius: 2, transition: 'background 0.3s', background: etapa === 'revisao' ? '#4BB8E8' : '#d0e8f5' }} />}
            </React.Fragment>
          ))}
        </div>
        {etapa === 'upload' && <UploadStep onProcessar={handleProcessar} loading={loading} />}
        {etapa === 'revisao' && <TabelaRevisao lancamentos={lancamentos} onLancamentosChange={setLancamentos} onExportar={handleExportar} onVoltar={() => { setEtapa('upload'); setLancamentos([]); }} loading={loading} banco={meta.banco} nomeEmpresa={meta.nomeEmpresa} mesAno={meta.mesAno} />}
      </main>
      <footer style={{ textAlign: 'center', padding: '1rem', fontSize: '0.75rem', color: '#6a90a8', borderTop: '1px solid #d0e8f5' }}>
        ExtratoConverter · Dados processados localmente
      </footer>
    </>
  );
}

function RotaProtegida() {
  const [auth, setAuth] = React.useState(null);
  React.useEffect(() => {
    fetch('/api/auth/me', { credentials: "include" })
      .then(r => setAuth(r.ok))
      .catch(() => setAuth(false));
  }, []);
  if (auth === null) return null; // carregando
  return auth ? <AppContent /> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" toastOptions={{ style: { fontFamily: 'Open Sans, sans-serif', fontSize: '0.9rem', borderRadius: '10px' } }} />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/app" element={<RotaProtegida />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}