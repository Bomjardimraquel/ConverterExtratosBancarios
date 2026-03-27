# 📊 ExtratoConverter — Conversor de Extratos Bancários para Prosoft

Converte extratos bancários em PDF para o formato Excel pronto para importar no sistema de gestão contábil **Prosoft**.

---

## 🏗️ Estrutura do Projeto

```
ConverterExtratosBancarios/
├── backend/
│   ├── main.py                  # FastAPI app
│   ├── requirements.txt
│   ├── parsers/
│   │   ├── base.py              # Classe base dos parsers
│   │   ├── sicoob.py            # Parser específico Sicoob
│   │   ├── bb.py                # Parser específico BB
│   │   ├── generico.py          # Parser genérico (Itaú, Bradesco, etc.)
│   │   └── factory.py           # Seletor de parser por banco
│   ├── routes/
│   │   └── extrato.py           # Endpoints da API
│   └── utils/
│       ├── contas.py            # Mapeamento de acessos Prosoft
│       ├── classificador.py     # Motor de classificação automática
│       └── exportar_excel.py    # Geração do Excel formatado
└── frontend/
    ├── package.json
    ├── public/
    │   └── index.html
    └── src/
        ├── App.js
        ├── index.js
        ├── index.css
        ├── components/
        │   ├── Header.js
        │   ├── UploadStep.js    # Tela de upload
        │   └── TabelaRevisao.js # Tela de revisão e edição
        └── utils/
            └── api.js           # Comunicação com o backend
```

---

## 🚀 Como rodar localmente

### Pré-requisitos
- Python 3.10+
- Node.js 18+

### 1. Clone o repositório
```bash
git clone https://github.com/Bomjardimraquel/ConverterExtratosBancarios.git
cd ConverterExtratosBancarios
```

### 2. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. Frontend (outro terminal)
```bash
cd frontend
npm install
npm start
```

Acesse: **http://localhost:3000**

---

## 🏦 Bancos suportados e acessos Prosoft

| Banco | Acesso |
|---|---|
| Banco do Brasil | 11041 |
| BB Rende Fácil (Aplicação) | 11142 |
| Empréstimo BB | 21381 |
| Sicoob | 11120 |
| Empréstimo Sicoob | 21325 |
| Itaú | 11045 |
| Itaú (Aplicação) | 11146 |
| PagBank | 11127 |
| Santander | 11126 |
| Bradesco | 11044 |
| Banco do Nordeste | 11042 |

---

## 📋 Regras de Classificação

### Créditos (entradas)
> **Débita** conta do banco → **Credita** Caixa (11002)

### Débitos (saídas) — Regra Geral
> **Débita** Caixa (11002) → **Credita** conta do banco

### Débitos — Classificações Especiais (por palavra-chave)

| Tipo | Acesso | Palavras-chave detectadas |
|---|---|---|
| Despesas Bancárias | 53502 | pacote serviços, tarifa, tarif, taxa bancária, manutenção conta... |
| IOF | 53514 | iof, imposto sobre operação |
| Juros | 53501 | juros, encargo, mora, multa atraso |
| Impostos/Tributos | 53065 | tributo, darf, gps, simples nacional, inss, fgts, rfb, receita federal... |

> **Nota:** Impostos são classificados como `53065 (Diversos)` para revisão manual posterior, já que o tipo exato do imposto precisa ser conferido na guia/comprovante.

---

## 🔒 Segurança

- O PDF é enviado **apenas para o backend local** (roda na sua máquina)
- **Nenhum dado** é armazenado em banco de dados ou servidor externo
- O Excel é gerado em memória e entregue diretamente para download
- Recomenda-se rodar em rede interna ou localhost

---

## ➕ Adicionar novo banco

1. Adicione o banco em `backend/utils/contas.py` (dicionários `CONTAS` e `BANCO_CONTA`)
2. Se o banco tiver formato muito específico de PDF, crie `backend/parsers/nome_banco.py` herdando de `ParserBase`
3. Registre o novo parser em `backend/parsers/factory.py`
4. Adicione o banco na lista em `frontend/src/components/UploadStep.js`

---

## 📄 Formato do Excel gerado

| Data | Descrição | Tipo | Débito | Crédito | Valor (R$) |
|---|---|---|---|---|---|
| 03/11 | CR ANT VISA - SIPAG Ant. Visa | Crédito | 11120 | 11002 | 380,19 |
| 03/11 | DEB PACOTE SERVIÇOS | Débito | 53502 | 11120 | 29,90 |
