import React, { useState, useRef, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster, toast } from 'react-hot-toast';
import Sidebar from './components/Sidebar';
import UploadStep from './components/UploadStep';
import UploadModulo2 from './components/UploadModulo2';
import Login from './components/Login';
import { processarExtrato, consultarStatusJob, exportarExcel } from './utils/api';

const INTERVALO_POLLING_MS = 2000;

function AppContent() {
  const [modulo, setModulo] = useState('1'); // '1' | '2'
  const [etapa, setEtapa] = useState('upload'); // upload | processando | resultado
  const [lancamentos, setLancamentos] = useState([]);
  const [meta, setMeta] = useState({ banco: '', nomeEmpresa: '', mesAno: '' });
  const [loading, setLoading] = useState(false);

  const pollingRef = useRef(null);

  const pararPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  useEffect(() => pararPolling, []);

  const handleTrocarModulo = (novoModulo) => {
    pararPolling();
    setModulo(novoModulo);
    setEtapa('upload');
    setLancamentos([]);
    setLoading(false);
  };

  const handleProcessar = async (arquivo, banco, nomeEmpresa, mesAno) => {
    setLoading(true);
    setEtapa('processando');
    try {
      const res = await processarExtrato(arquivo, banco, nomeEmpresa, mesAno);
      const jobId = res.data.job_id;
      iniciarPolling(jobId, banco, nomeEmpresa, mesAno);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erro ao enviar o arquivo.');
      setLoading(false);
      setEtapa('upload');
    }
  };

  const iniciarPolling = (jobId, banco, nomeEmpresa, mesAno) => {
    pararPolling();

    pollingRef.current = setInterval(async () => {
      try {
        const res = await consultarStatusJob(jobId);
        const { status, resultado, erro } = res.data;

        if (status === 'concluido') {
          pararPolling();
          setLancamentos(resultado.lancamentos);
          setMeta({ banco, nomeEmpresa, mesAno, total: resultado.total });
          setEtapa('resultado');
          setLoading(false);
        } else if (status === 'erro') {
          pararPolling();
          toast.error(erro || 'Erro ao processar o arquivo.');
          setLoading(false);
          setEtapa('upload');
        }
      } catch (err) {
        pararPolling();
        toast.error('Erro ao consultar o status do processamento.');
        setLoading(false);
        setEtapa('upload');
      }
    }, INTERVALO_POLLING_MS);
  };

  const handleExportar = async () => {
    setLoading(true);
    try {
      await exportarExcel(lancamentos, meta.banco, meta.nomeEmpresa, meta.mesAno);
      toast.success('Excel baixado com sucesso!');
    } catch { toast.error('Erro ao gerar o Excel.'); }
    finally { setLoading(false); }
  };

  const handleNovoExtrato = () => {
    setEtapa('upload');
    setLancamentos([]);
  };

  return (
    <div className="app-shell">
      <Sidebar modulo={modulo} onTrocarModulo={handleTrocarModulo} />
      <main className="app-conteudo">
        {modulo === '2' ? (
          <UploadModulo2 />
        ) : (
          <>
            {etapa === 'upload' && <UploadStep onProcessar={handleProcessar} loading={loading} />}

            {etapa === 'processando' && (
              <>
                <div className="pagina-topbar">
                  <div className="pagina-topbar-titulo">Processando extrato</div>
                  <div className="pagina-topbar-sub">Isso roda em segundo plano, geralmente leva poucos segundos</div>
                </div>
                <div className="pagina-corpo" style={{ alignItems: 'flex-start' }}>
                  <div className="spinner" style={{ margin: '2rem 0' }} />
                </div>
              </>
            )}

            {etapa === 'resultado' && (
              <>
                <div className="pagina-topbar">
                  <div className="pagina-topbar-titulo">{meta.nomeEmpresa || 'Extrato processado'}</div>
                  <div className="pagina-topbar-sub">{meta.mesAno}</div>
                </div>
                <div className="pagina-corpo">
                  <div className="eyebrow">Resultado</div>
                  <div className="metrics-grid">
                    <div className="metric-card">
                      <div className="metric-label">Lançamentos</div>
                      <div className="metric-value">{meta.total}</div>
                    </div>
                  </div>
                  <button onClick={handleExportar} disabled={loading} className="btn-pill btn-pill-primario">
                    {loading ? 'Gerando...' : 'Baixar Excel'}
                  </button>
                  <button onClick={handleNovoExtrato} className="btn-pill btn-pill-secundario">
                    Processar outro extrato
                  </button>
                </div>
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}

function RotaProtegida() {
  const [auth, setAuth] = React.useState(null);
  React.useEffect(() => {
    fetch('/api/auth/me', { credentials: "include" })
      .then(r => setAuth(r.ok))
      .catch(() => setAuth(false));
  }, []);
  if (auth === null) return null;
  return auth ? <AppContent /> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" toastOptions={{ style: { fontFamily: 'var(--font-display)', fontSize: '0.9rem', borderRadius: '10px' } }} />
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/login" element={<Login />} />
        <Route path="/app" element={<RotaProtegida />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}