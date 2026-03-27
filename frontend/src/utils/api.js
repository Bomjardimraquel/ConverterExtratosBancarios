import axios from 'axios';

const api = axios.create({ baseURL: '/api' });

export const listarBancos = () => api.get('/bancos');

export const processarExtrato = (arquivo, banco, nomeEmpresa, mesAno) => {
  const form = new FormData();
  form.append('arquivo', arquivo);
  form.append('banco', banco);
  form.append('nome_empresa', nomeEmpresa);
  form.append('mes_ano', mesAno);
  return api.post('/processar', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
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

export default api;
