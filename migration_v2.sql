-- Adicionar colunas do ticket na tabela ctlloop_analise
ALTER TABLE ctlloop_analise
    ADD COLUMN IF NOT EXISTS ticket_ref   text,
    ADD COLUMN IF NOT EXISTS nota         integer,
    ADD COLUMN IF NOT EXISTS agente       text,
    ADD COLUMN IF NOT EXISTS canal        text,
    ADD COLUMN IF NOT EXISTS nome_cliente text,
    ADD COLUMN IF NOT EXISTS telefone     text,
    ADD COLUMN IF NOT EXISTS data_ticket  timestamptz,
    ADD COLUMN IF NOT EXISTS fila         text,
    ADD COLUMN IF NOT EXISTS assunto      text;
