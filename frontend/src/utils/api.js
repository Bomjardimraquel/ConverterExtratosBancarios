import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
});

api.interceptors.response.use(
  r => r,
  async err => {
    const original = err.config;
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        await axios.post('/api/auth/refresh', {}, { withCredentials: true });
        return api(original);
      } catch {
        window.location.href = '/login';
      }
    }
    return Promise.reject(err);
  }
);

export const processarExtrato = (arquivo, banco, nomeEmpresa, mesAno) => {
  const form = new FormData();
  form.append('arquivo', arquivo);
  form.append('banco', banco);
  form.append('nome_empresa', nomeEmpresa);
  form.append('mes_ano', mesAno);
  return api.post('/processar', form, { headers: { 'Content-Type': 'multipart/form-data' } });
};

// Consulta o status de um job assíncrono (fila RQ).
// Resposta esperada: { status: 'processando' | 'concluido' | 'erro', resultado?, erro? }
export const consultarStatusJob = (jobId) => {
  return api.get(`/status/${jobId}`);
};

export const exportarExcel = async (lancamentos, banco, nomeEmpresa, mesAno) => {
  const res = await api.post(
    '/exportar',
    { lancamentos, banco, nome_empresa: nomeEmpresa, mes_ano: mesAno },
    { responseType: 'blob' }
  );
  const url = window.URL.createObjectURL(new Blob([res.data]));
  const link = document.createElement('a');
  link.href = url;
  const cd = res.headers['content-disposition'] || '';
  const match = cd.match(/filename="?([^"]+)"?/);
  link.download = match ? match[1] : 'lancamentos.xlsx';
  link.click();
  window.URL.revokeObjectURL(url);
};

// ── Módulo 2 (extrato + título + despesa/razão, cruzamento completo) ──────

export const listarEmpresasModulo2 = () => api.get('/modulo2/empresas');

export const processarCompletoModulo2 = ({
  empresa, banco, mesAno, tipoTitulos, nomeEmpresa,
  extrato, arquivoTitulos, arquivoDespesasOuRazao, arquivoModeloClassificado,
}) => {
  const form = new FormData();
  form.append('empresa', empresa);
  form.append('banco', banco);
  form.append('mes_ano', mesAno);
  form.append('tipo_titulos', tipoTitulos);
  form.append('nome_empresa', nomeEmpresa || '');
  form.append('extrato', extrato);
  form.append('arquivo_titulos', arquivoTitulos);
  form.append('arquivo_despesas_ou_razao', arquivoDespesasOuRazao);
  if (arquivoModeloClassificado) {
    form.append('arquivo_modelo_classificado', arquivoModeloClassificado);
  }
  return api.post('/modulo2/processar_completo', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const consultarStatusModulo2 = (jobId) => api.get(`/modulo2/status_completo/${jobId}`);

export const baixarExcelModulo2 = async (nomeArquivo) => {
  const res = await api.get(`/modulo2/download/${nomeArquivo}`, { responseType: 'blob' });
  const url = window.URL.createObjectURL(new Blob([res.data]));
  const link = document.createElement('a');
  link.href = url;
  link.download = nomeArquivo;
  link.click();
  window.URL.revokeObjectURL(url);
};

export default api;