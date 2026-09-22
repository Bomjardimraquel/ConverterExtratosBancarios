import React, { useCallback, useEffect, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { toast } from 'react-hot-toast';
import {
  listarEmpresasModulo3, listarAcessosSugeridos,
  processarModulo3, consultarStatusModulo3, baixarExcelModulo3,
} from '../utils/api';

const INTERVALO_POLLING_MS = 2000;

const GRUPOS = [
  { key: 'ativo', label: 'Ativo' },
  { key: 'passivo', label: 'Passivo' },
  { key: 'despesas', label: 'Despesas' },
  { key: 'receitas', label: 'Receitas' },
];

const SEVERIDADE_COR = {
  Alto: { bg: 'var(--review-bg)', border: 'var(--review-border)' },
  Médio: { bg: 'var(--credit-bg)', border: 'var(--tea-rose)' },
  Baixo: { bg: 'var(--debit-bg)', border: 'var(--debit-border)' },
  OK: { bg: 'var(--surface2)', border: 'var(--border)' },
};

// mesmo motivo do extrairMensagemErro que já existe no UploadModulo2 e no App —
// FastAPI manda o "detail" de validação (422) como lista de objetos, não string
function extrairMensagemErro(err) {
  const detail = err.response?.data?.detail;
  if (!detail) return 'Erro ao enviar o arquivo.';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map(d => `${(d.loc || []).join(' → ')}: ${d.msg}`).join(' | ');
  }
  return 'Erro ao enviar o arquivo.';
}

export default function AnaliseRazao() {
  const [etapa, setEtapa] = useState('form'); // form | processando | resultado | erro

  const [empresas, setEmpresas] = useState([]);
  const [carregandoEmpresas, setCarregandoEmpresas] = useState(true);
  const [empresaId, setEmpresaId] = useState('');

  const [grupo, setGrupo] = useState('');
  const [acessosSugeridos, setAcessosSugeridos] = useState([]);
  const [carregandoAcessos, setCarregandoAcessos] = useState(false);
  const [acessosSelecionados, setAcessosSelecionados] = useState([]);

  const [arquivoRazao, setArquivoRazao] = useState(null);

  const [resultado, setResultado] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [erro, setErro] = useState('');

  useEffect(() => {
    listarEmpresasModulo3()
      .then(res => setEmpresas(res.data.empresas || []))
      .catch(() => toast.error('Não consegui carregar a lista de empresas.'))
      .finally(() => setCarregandoEmpresas(false));
  }, []);

  const empresaSelecionada = empresas.find(e => e.id === empresaId);

  const handleEmpresaChange = (id) => {
    setEmpresaId(id);
    setGrupo('');
    setAcessosSugeridos([]);
    setAcessosSelecionados([]);
  };

  const handleGrupoChange = (g) => {
    setGrupo(g);
    setAcessosSelecionados([]);
    setCarregandoAcessos(true);
    listarAcessosSugeridos(empresaId, g)
      .then(res => setAcessosSugeridos(res.data.acessos || []))
      .catch(() => toast.error('Não consegui carregar os acessos dessa empresa.'))
      .finally(() => setCarregandoAcessos(false));
  };

  const toggleAcesso = (codigo) => {
    setAcessosSelecionados(prev => {
      if (prev.includes(codigo)) return prev.filter(c => c !== codigo);
      // no máximo 2 acessos por vez (ex: um par Passivo + Despesa conexo)
      if (prev.length >= 2) {
        toast.error('Selecione no máximo 2 acessos por vez.');
        return prev;
      }
      return [...prev, codigo];
    });
  };

  const tudoPreenchido = empresaId && grupo && acessosSelecionados.length > 0 && arquivoRazao;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!tudoPreenchido) return;

    setEtapa('processando');
    try {
      const res = await processarModulo3({
        empresaId, grupo, acessos: acessosSelecionados, arquivoRazao,
      });
      setJobId(res.data.job_id);
      iniciarPolling(res.data.job_id);
    } catch (err) {
      setErro(extrairMensagemErro(err));
      setEtapa('erro');
    }
  };

  const iniciarPolling = (id) => {
    const intervalId = setInterval(async () => {
      try {
        const res = await consultarStatusModulo3(id);
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

  const handleBaixar = async () => {
    try {
      await baixarExcelModulo3(jobId, resultado.arquivo);
    } catch (err) {
      toast.error(
        err.response?.status === 401
          ? 'Sessão expirada, faça login de novo.'
          : 'Erro ao baixar o Excel. Tenta de novo.'
      );
    }
  };

  const handleNovaAnalise = () => {
    setEtapa('form');
    setResultado(null);
    setJobId(null);
    setErro('');
    setArquivoRazao(null);
    setAcessosSelecionados([]);
  };

  if (etapa === 'processando') {
    return (
      <>
        <div className="pagina-topbar">
          <div className="pagina-topbar-titulo">Analisando razão</div>
          <div className="pagina-topbar-sub">Isso roda em segundo plano, geralmente leva poucos segundos</div>
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
          <button onClick={handleNovaAnalise} className="btn-pill btn-pill-primario">
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
          <div className="pagina-topbar-sub">{resultado.acessos_analisados?.join(' + ')}</div>
        </div>
        <div className="pagina-corpo">
          <div className="eyebrow">Achados</div>
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-label">Lançamentos analisados</div>
              <div className="metric-value">{resultado.total_lancamentos}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Achados</div>
              <div className="metric-value">{resultado.achados?.length || 0}</div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', marginTop: '0.5rem' }}>
            {(resultado.achados || []).map((a, i) => (
              <div
                key={i}
                className="box-simples"
                style={{
                  background: SEVERIDADE_COR[a.severidade]?.bg || 'var(--surface2)',
                  borderColor: SEVERIDADE_COR[a.severidade]?.border || 'var(--border)',
                  fontSize: '0.85rem',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                  <span>{a.acesso} — {a.nome_conta} {a.terceiro ? `— ${a.terceiro}` : ''}</span>
                  <span>{a.valor != null ? `R$ ${a.valor.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}` : ''}</span>
                </div>
                <div style={{ color: 'var(--text-muted)', marginBottom: '0.25rem' }}>{a.tipo}</div>
                <div>{a.descricao}</div>
              </div>
            ))}
          </div>

          <button onClick={handleBaixar} className="btn-pill btn-pill-primario">
            Baixar Excel
          </button>
          <button onClick={handleNovaAnalise} className="btn-pill btn-pill-secundario">
            Analisar outro razão
          </button>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="pagina-topbar">
        <div className="pagina-topbar-titulo">Análise de Razão</div>
        <div className="pagina-topbar-sub">Consistência de saldos, provisões e lançamentos por conta</div>
      </div>

      <form onSubmit={handleSubmit} className="pagina-corpo">
        <div className="eyebrow">Nova análise</div>

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
              <option key={e.id} value={e.id}>{e.id} ({e.nome})</option>
            ))}
          </select>
        </div>

        {empresaId && (
          <div>
            <Label>Grupo *</Label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.6rem' }}>
              {GRUPOS.map(g => (
                <button
                  type="button"
                  key={g.key}
                  onClick={() => handleGrupoChange(g.key)}
                  className={`btn-pill ${grupo === g.key ? 'btn-pill-primario' : 'btn-pill-secundario'}`}
                  style={{ width: '100%', justifyContent: 'center' }}
                >
                  {g.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {grupo && (
          <div>
            <Label>Acessos sugeridos (até 2) *</Label>
            {carregandoAcessos ? (
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Carregando...</div>
            ) : acessosSugeridos.length === 0 ? (
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                Nenhum acesso sugerido para esse grupo nessa empresa.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                {acessosSugeridos.map(a => (
                  <label
                    key={a.codigo}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '0.5rem',
                      padding: '0.6rem 0.75rem', borderRadius: 'var(--radius-sm)',
                      border: `1.5px solid ${acessosSelecionados.includes(a.codigo) ? 'var(--musgo)' : 'var(--border)'}`,
                      background: acessosSelecionados.includes(a.codigo) ? 'var(--credit-bg)' : 'var(--surface)',
                      cursor: 'pointer', fontSize: '0.85rem',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={acessosSelecionados.includes(a.codigo)}
                      onChange={() => toggleAcesso(a.codigo)}
                    />
                    <span style={{ fontWeight: 600 }}>{a.codigo}</span>
                    <span style={{ color: 'var(--text-muted)' }}>{a.nome}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        )}

        {acessosSelecionados.length > 0 && (
          <FileField
            label="Razão do(s) acesso(s) selecionado(s) *"
            aceita={{ 'application/vnd.ms-excel': ['.xls'] }}
            dica=".xls, formato razão do Prosoft"
            arquivo={arquivoRazao}
            onArquivo={setArquivoRazao}
          />
        )}

        <button type="submit" disabled={!tudoPreenchido} className="btn-pill btn-pill-primario">
          Analisar
        </button>
      </form>
    </>
  );
}

// FileField e Label idênticos aos de UploadModulo2.js — considerar extrair
// pra um arquivo compartilhado (components/FormFields.js) já que agora tem
// 2 telas usando exatamente o mesmo padrão.
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