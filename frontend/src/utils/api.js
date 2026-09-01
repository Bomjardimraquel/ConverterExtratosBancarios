import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';
export { API_BASE_URL };

const CHAVE_ACCESS = 'ec_access_token';
const CHAVE_REFRESH = 'ec_refresh_token';

function salvarTokens(accessToken, refreshToken) {
  localStorage.setItem(CHAVE_ACCESS, accessToken);
  localStorage.setItem(CHAVE_REFRESH, refreshToken);
}

function limparTokens() {
  localStorage.removeItem(CHAVE_ACCESS);
  localStorage.removeItem(CHAVE_REFRESH);
  localStorage.removeItem('ec_nome');
}

function getAccessToken() {
  return localStorage.getItem(CHAVE_ACCESS);
}

function getRefreshToken() {
  return localStorage.getItem(CHAVE_REFRESH);
}

const api = axios.create({ baseURL: API_BASE_URL });

// Manda o access token em TODO pedido, automaticamente.
api.interceptors.request.use(config => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Se um pedido voltar 401 (access token vencido), tenta renovar
// automaticamente com o refresh token, e repete o pedido original.
api.interceptors.response.use(
  r => r,
  async err => {
    const original = err.config;
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        limparTokens();
        window.location.href = '/login';
        return Promise.reject(err);
      }
      try {
        const { data } = await axios.post(`${API_BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });
        salvarTokens(data.access_token, data.refresh_token);
        return api(original);
      } catch {
        limparTokens();
        window.location.href = '/login';
      }
    }
    return Promise.reject(err);
  }
);

// ── Funções de autenticação ────────────────────────────────────────────

export const login = async (username, senha) => {
  const { data } = await axios.post(`${API_BASE_URL}/auth/login`, { username, senha });
  salvarTokens(data.access_token, data.refresh_token);
  localStorage.setItem('ec_nome', data.nome);
  return data;
};

export const logout = async () => {
  const refreshToken = getRefreshToken();
  try {
    await axios.post(`${API_BASE_URL}/auth/logout`, { refresh_token: refreshToken });
  } catch {
    // mesmo se der erro no servidor, limpa localmente de qualquer jeito
  }
  limparTokens();
};

export const getMe = () => api.get('/auth/me');

export const estaLogado = () => !!getAccessToken();

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
  extrato, arquivoTitulos, arquivoDespesas, arquivoRazao, arquivoModeloClassificado,
}) => {
  const form = new FormData();
  form.append('empresa', empresa);
  form.append('banco', banco);
  form.append('mes_ano', mesAno);
  form.append('tipo_titulos', tipoTitulos);
  form.append('nome_empresa', nomeEmpresa || '');
  form.append('extrato', extrato);
  if (arquivoTitulos) {
    form.append('arquivo_titulos', arquivoTitulos);
  }
  if (arquivoDespesas) {
    form.append('arquivo_despesas', arquivoDespesas);
  }
  if (arquivoRazao) {
    form.append('arquivo_razao', arquivoRazao);
  }
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