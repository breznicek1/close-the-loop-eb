# close-the-loop-eb

App de gestão de DSATs e close the loop — EstrelaBet / i9xc.

## Stack
- Python + Streamlit
- Supabase Postgres (projeto: close-the-loop-eb)

## Rodar local
```bash
pip install -r requirements.txt
# criar .streamlit/secrets.toml com base no secrets.toml.template
streamlit run app.py
```

## Deploy (Streamlit Cloud)
1. Subir repositório no GitHub
2. Conectar em share.streamlit.io
3. Em Secrets, colar o conteúdo do secrets.toml.template

## Usuários padrão
| usuário   | senha     |
|-----------|-----------|
| fernanda  | ctl2025   |
| isabel    | ctl2025   |
| marcelo   | ctl2025   |
| mateus    | ctl2025   |
| robert    | ctl2025   |
| admin     | admin2025 |

**Trocar as senhas antes de compartilhar o link.**

## Integração Power BI
A tabela `ctlloop_analise` fica no Supabase e pode ser lida via REST:
```
GET https://pjfyzgnsbvlsmvqncttq.supabase.co/rest/v1/ctlloop_analise
Headers:
  apikey: <anon key>
  Authorization: Bearer <anon key>
```
