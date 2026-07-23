import React, { useCallback, useEffect, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { toast } from 'react-hot-toast';
import {
  listarEmpresasModulo2, processarCompletoModulo2,
  consultarStatusModulo2, baixarExcelModulo2,
} from '../utils/api';

const INTERVALO_POLLING_MS = 2000;
const MESES = [
  ['01', 'Janeiro'], ['02', 'Fevereiro'], ['03', 'Março'], ['04', 'Abril'],
  ['05', 'Maio'], ['06', 'Junho'], ['07', 'Julho'], ['08', 'Agosto'],
  ['09', 'Setembro'], ['10', 'Outubro'], ['11', 'Novembro'], ['12', 'Dezembro'],
];
const ANO_ATUAL = new Date().getFullYear();
const ANOS = [ANO_ATUAL - 1, ANO_ATUAL, ANO_ATUAL + 1];

export default function UploadModulo2() {
  const [etapa, setEtapa] = useState('form'); // form | processando | resultado | erro
  const [empresas, setEmpresas] = useState([]);
  const [carregandoEmpresas, setCarregandoEmpresas] = useState(true);

  const [empresaId, setEmpresaId] = useState('');
  const [banco, setBanco] = useState('');
  const [mes, setMes] = useState('');
  const [ano, setAno] = useState(String(ANO_ATUAL));
  const [tipoTitulos, setTipoTitulos] = useState('receber');
  const [nomeEmpresa, setNomeEmpresa] = useState('');
  const [mostrarModeloOpcional, setMostrarModeloOpcional] = useState(false);

  const [extrato, setExtrato] = useState(null);
  const [arquivoTitulos, setArquivoTitulos] = useState(null);
  const [arquivoDespesas, setArquivoDespesas] = useState(null);
  const [arquivoModelo, setArquivoModelo] = useState(null);

  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState('');

  useEffect(() => {
    listarEmpresasModulo2()
      .then(res => setEmpresas(res.data.empresas || []))
      .catch(() => toast.error('Não consegui carregar a lista de empresas.'))
      .finally(() => setCarregandoEmpresas(false));
  }, []);

  const empresaSelecionada = empresas.find(e => e.id === empresaId);
  const bancosDaEmpresa = empresaSelecionada?.bancos || [];

  const handleEmpresaChange = (id) => {
    setEmpresaId(id);
    setBanco('');
    const emp = empresas.find(e => e.id === id);
    if (emp) setNomeEmpresa(emp.nome);
  };

  const tudoPreenchido = empresaId && banco && mes && ano && extrato && arquivoTitulos && arquivoDespesas;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!tudoPreenchido) return;

    setEtapa('processando');
    try {
      const res = await processarCompletoModulo2({
        empresa: empresaId, banco, mesAno: `${mes}/${ano}`,
        tipoTitulos, nomeEmpresa,
        extrato, arquivoTitulos, arquivoDespesasOuRazao: arquivoDespesas,
        arquivoModeloClassificado: arquivoModelo,
      });
      iniciarPolling(res.data.job_id);
    } catch (err) {
      setErro(err.response?.data?.detail || 'Erro ao enviar os arquivos.');
      setEtapa('erro');
    }
  };

  const iniciarPolling = (jobId) => {
    const intervalId = setInterval(async () => {
      try {
        const res = await consultarStatusModulo2(jobId);
        const { status, resultado: dados, erro: msgErro } = res.data;
        if (status === 'concluido') {
          clearInterval(intervalId);
          setResultado(dados);
          setEtapa('resultado');
        } else if (status === 'erro') {
          clearInterval(intervalId);
          setErro(msgErro || 'Erro ao processar.');
          setEtapa('erro');
        }
      } catch {
        clearInterval(intervalId);
        setErro('Erro ao consultar o status do processamento.');
        setEtapa('erro');
      }
    }, INTERVALO_POLLING_MS);
  };

  const handleNovoProcessamento = () => {
    setEtapa('form');
    setResultado(null);
    setErro('');
    setExtrato(null);
    setArquivoTitulos(null);
    setArquivoDespesas(null);
    setArquivoModelo(null);
  };

  if (etapa === 'processando') {
    return (
      <>
        <div className="pagina-topbar">
          <div className="pagina-topbar-titulo">Processando</div>
          <div className="pagina-topbar-sub">Extrato, títulos e despesas sendo cruzados — geralmente leva poucos segundos</div>
        </div>
        <div className="pagina-corpo">
          <div className="spinner" style={{ margin: '2rem 0' }} />
        </div>
      </>
    );
  }

  if (etapa === 'erro') {
    return (
      <>
        <div className="pagina-topbar">
          <div className="pagina-topbar-titulo">Não deu certo</div>
        </div>
        <div className="pagina-corpo">
          <div className="box-simples" style={{ borderColor: 'var(--danger)', color: 'var(--danger)', fontSize: '0.85rem' }}>
            {erro}
          </div>
          <button onClick={handleNovoProcessamento} className="btn-pill btn-pill-primario">
            Tentar de novo
          </button>
        </div>
      </>
    );
  }

  if (etapa === 'resultado' && resultado) {
    return (
      <>
        <div className="pagina-topbar">
          <div className="pagina-topbar-titulo">{resultado.nome_empresa}</div>
          <div className="pagina-topbar-sub">Conciliação concluída</div>
        </div>
        <div className="pagina-corpo">
          <div className="eyebrow">Resultado</div>
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-label">Lançamentos</div>
              <div className="metric-value">{resultado.total_lancamentos}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Conciliados</div>
              <div className="metric-value">{resultado.casados}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">% conciliado</div>
              <div className="metric-value">{resultado.percentual_casado}%</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Pendências</div>
              <div className="metric-value">{resultado.linhas_pendencias}</div>
            </div>
          </div>

          {resultado.despesas_brutas_nao_classificadas > 0 && (
            <div className="box-simples" style={{ background: 'var(--debit-bg)', borderColor: 'var(--debit-border)', fontSize: '0.82rem', color: 'var(--navy)' }}>
              {resultado.despesas_brutas_nao_classificadas} despesa(s) do arquivo bruto não foram
              reconhecidas automaticamente — considere revisar e, se for um padrão novo, avisar
              pra virar regra permanente.
            </div>
          )}

          <button onClick={() => baixarExcelModulo2(resultado.arquivo)} className="btn-pill btn-pill-primario">
            Baixar Excel
          </button>
          <button onClick={handleNovoProcessamento} className="btn-pill btn-pill-secundario">
            Processar outro
          </button>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="pagina-topbar">
        <div className="pagina-topbar-titulo">Conciliação completa</div>
        <div className="pagina-topbar-sub">Extrato + títulos + despesas, tudo cruzado de uma vez</div>
      </div>

      <form onSubmit={handleSubmit} className="pagina-corpo">
        <div className="eyebrow">Novo processamento</div>

        <div>
          <Label>Empresa *</Label>
          <select
            value={empresaId}
            onChange={e => handleEmpresaChange(e.target.value)}
            required
            disabled={carregandoEmpresas}
            style={{ ...inputStyle, cursor: 'pointer' }}
          >
            <option value="">
              {carregandoEmpresas ? 'Carregando...' : 'Selecione a empresa...'}
            </option>
            {empresas.map(e => (
              <option key={e.id} value={e.id}>{e.id} — {e.nome}</option>
            ))}
          </select>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div>
            <Label>Banco *</Label>
            <select
              value={banco}
              onChange={e => setBanco(e.target.value)}
              required
              disabled={!empresaId}
              style={{ ...inputStyle, cursor: empresaId ? 'pointer' : 'not-allowed' }}
            >
              <option value="">
                {empresaId ? 'Selecione...' : 'Escolha a empresa primeiro'}
              </option>
              {bancosDaEmpresa.map(b => (
                <option key={b.key} value={b.key}>{b.key} — Acesso {b.conta}</option>
              ))}
            </select>
          </div>
          <div>
            <Label>Títulos são de *</Label>
            <select
              value={tipoTitulos}
              onChange={e => setTipoTitulos(e.target.value)}
              style={{ ...inputStyle, cursor: 'pointer' }}
            >
              <option value="receber">Receber</option>
              <option value="pagar">Pagar</option>
            </select>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div>
            <Label>Mês *</Label>
            <select value={mes} onChange={e => setMes(e.target.value)} required
              style={{ ...inputStyle, cursor: 'pointer' }}>
              <option value="">Selecione...</option>
              {MESES.map(([num, nome]) => <option key={num} value={num}>{nome}</option>)}
            </select>
          </div>
          <div>
            <Label>Ano *</Label>
            <select value={ano} onChange={e => setAno(e.target.value)}
              style={{ ...inputStyle, cursor: 'pointer' }}>
              {ANOS.map(a => <option key={a} value={a}>{a}</option>)}
            </select>
          </div>
        </div>

        <FileField
          label="Extrato do banco *"
          aceita={{ 'application/pdf': ['.pdf'], 'text/plain': ['.txt'] }}
          dica="PDF ou TXT"
          arquivo={extrato}
          onArquivo={setExtrato}
        />

        <FileField
          label="Relatório de títulos *"
          aceita={{ 'application/vnd.ms-excel': ['.xls'] }}
          dica=".xls"
          arquivo={arquivoTitulos}
          onArquivo={setArquivoTitulos}
        />

        <FileField
          label="Despesa classificada / razão do Prosoft / movimento bruto *"
          aceita={{
            'application/vnd.ms-excel': ['.xls'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
          }}
          dica=".xls ou .xlsx — o formato é detectado automaticamente"
          arquivo={arquivoDespesas}
          onArquivo={setArquivoDespesas}
        />

        <button
          type="button"
          onClick={() => setMostrarModeloOpcional(v => !v)}
          style={{
            background: 'none', border: 'none', padding: 0,
            color: 'var(--blue-dark)', fontSize: '0.82rem', fontWeight: 600,
            cursor: 'pointer', textDecoration: 'underline', textAlign: 'left',
          }}
        >
          {mostrarModeloOpcional ? '− Ocultar' : '+ Preciso ensinar fornecedor novo (opcional)'}
        </button>

        {mostrarModeloOpcional && (
          <FileField
            label="Mês já classificado, como referência"
            aceita={{
              'application/vnd.ms-excel': ['.xls'],
              'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
            }}
            dica="só necessário se o arquivo de despesas for o formato bruto e tiver fornecedor que as regras ainda não reconhecem"
            arquivo={arquivoModelo}
            onArquivo={setArquivoModelo}
          />
        )}

        <button type="submit" disabled={!tudoPreenchido} className="btn-pill btn-pill-primario">
          Processar tudo
        </button>
      </form>
    </>
  );
}

function FileField({ label, aceita, dica, arquivo, onArquivo }) {
  const onDrop = useCallback((accepted) => {
    if (accepted.length > 0) onArquivo(accepted[0]);
  }, [onArquivo]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: aceita, multiple: false,
  });

  return (
    <div>
      <Label>{label}</Label>
      <div
        {...getRootProps()}
        className="dropzone"
        style={{
          border: `1.5px dashed ${isDragActive || arquivo ? 'var(--blue)' : 'var(--border)'}`,
          borderRadius: 'var(--radius-sm)', padding: '1.1rem 1rem',
          textAlign: 'center', cursor: 'pointer',
          background: isDragActive || arquivo ? 'var(--credit-bg)' : 'var(--surface)',
          transition: 'all 0.2s',
        }}
      >
        <input {...getInputProps()} />
        {arquivo ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, fontWeight: 600, color: 'var(--blue)', fontSize: '0.85rem' }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
            {arquivo.name}
          </div>
        ) : (
          <>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto 0.4rem', display: 'block' }}>
              <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242" /><path d="M12 12v9" /><path d="m16 16-4-4-4 4" />
            </svg>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {isDragActive ? 'Solte aqui!' : `Arraste ou clique para selecionar (${dica})`}
            </div>
          </>
        )}
      </div>
    </div>
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

const inputStyle = {
  width: '100%', padding: '0.75rem 0.9rem',
  border: '1.5px solid var(--border)', borderRadius: 'var(--radius-sm)',
  fontSize: '0.9rem', background: 'var(--surface)',
  color: 'var(--text)', outline: 'none',
};