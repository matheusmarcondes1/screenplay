# Andon — configuração do Supabase (sem login)

Backend do módulo de andon: **Postgres + Realtime**, sem autenticação. A plataforma é uma
ferramenta interna de piso; a identificação da operadora é apenas **número da mesa + etapa**.
O acesso é feito com a **chave publishable** e as tabelas ficam abertas ao papel anônimo via RLS
(não há dados pessoais — apenas sinais operacionais de chamado).

## 1. Aplicar o esquema

**SQL Editor → New query →** cole [`migrations/0003_andon_sem_login.sql`](migrations/0003_andon_sem_login.sql)
**→ Run**.

Esse arquivo **substitui** os anteriores (0001 e 0002): remove o modelo com login (profiles/PIN) e
recria `andon_events` e `etapa_config` para uso anônimo, com Realtime habilitado. Se você já tinha
aplicado o 0001/0002, tudo bem — o 0003 dá `drop` no que for necessário e recria.

> Os arquivos `0001_*` e `0002_*` ficam no histórico apenas como referência; **não** precisam ser
> aplicados. A Edge Function `admin-manage-user` foi removida (não há mais usuários).

## 1b. Horários das reuniões no banco

**SQL Editor → New query →** cole [`migrations/0004_reunioes_no_banco.sql`](migrations/0004_reunioes_no_banco.sql)
**→ Run**.

Cria as tabelas do cronograma do Painel de Avisos — `meeting_series`, `meeting_windows`,
`n1_periods` e `panel_settings` — com RLS anônima e Realtime, e já faz a carga inicial (turnos da
manhã e da tarde + períodos de N1). A partir daí os horários são cadastrados **uma vez** pela tela
de Configurações do painel e valem para **todas as TVs**, que recebem as alterações na hora.

Os horários deixam de ficar no navegador: cada TV guarda apenas as preferências de exibição
(fonte, fundo do relógio) e uma cópia do último cronograma recebido, usada só se o banco estiver
inacessível.

## 2. Conectar o app

Painel e Andon vivem no mesmo `index.html` e usam o mesmo cliente. A URL e a chave publishable
padrão estão no próprio arquivo; para apontar a outro projeto, troque-as em
**Configurações → Notificações de Andon**, na TV, ou na tela de conexão que o Andon mostra quando
não consegue conectar.

## 3. Pronto

Abra `index.html#andon` e siga o fluxo:
- **Operadora** → escolhe a etapa e a mesa → tela de chamados (Falta de Material, Qualidade,
  Inspeção, Assistente).
- **Material Handler / Coordenação Técnica / Inspeção / Assistente** → veem a fila de chamados do
  seu tipo, em tempo real, e concluem no ✓.
- **Assistente** → além da fila, tem **Estatísticas** (com exportação CSV/Excel) e **Mesas**
  (define quais mesas ficam disponíveis por etapa).

## Modelo de dados

| Tabela            | Papel                                                                 |
|-------------------|-----------------------------------------------------------------------|
| `andon_events`    | chamados: tipo, mesa, etapa, status, horários                         |
| `etapa_config`    | mesas disponíveis por etapa (vazio = todas as 25)                     |
| `meeting_series`  | séries/turnos das Reuniões Escalonadas                                |
| `meeting_windows` | janelas: início, fim, área, supervisor, Cadeia de Ajuda               |
| `n1_periods`      | períodos das Reuniões de N1                                           |
| `panel_settings`  | série ativa e textos/ativação do N1 (linha única)                     |

Tipos de chamado e destino:

| Tipo             | Aciona               | Cor      |
|------------------|----------------------|----------|
| `falta_material` | Material Handler     | amarelo  |
| `qualidade`      | Coordenação Técnica  | roxo     |
| `inspecao`       | Inspeção             | laranja  |
| `assistente`     | Assistentes          | verde    |

Fluxo de status: `aberto → resolvido` (concluído pelo receptor) ou `cancelado` (pela operadora).

## Segurança

Sem login por decisão de uso (piso). As tabelas expõem apenas dados operacionais (tipo, mesa,
etapa, horário) — sem nomes ou informação pessoal. Se no futuro quiser restringir escrita/leitura,
dá para reintroduzir uma camada de autenticação leve; me avise.

---

## Avisos no Microsoft Teams (opcional)

A migração [`0006_andon_teams.sql`](migrations/0006_andon_teams.sql) faz o banco avisar um canal
do Teams quando um chamado fica aberto além do tempo configurado. Requer as extensões `pg_net` e
`pg_cron` ligadas em **Database > Extensions**.

Ela cria:

- `andon_notify_config` — uma linha por tipo de chamado, com a URL do fluxo do Teams, o tempo até
  escalar, se avisa na abertura e se repete. Nasce desligada e sem URL, então nada é enviado até
  você mandar. **RLS fechada e grants revogados**: a chave publishable não lê esta tabela, porque
  a URL é uma credencial.
- `andon_notify_tick()` — roda de minuto em minuto pelo `pg_cron` e envia o que passou do tempo.
- `andon_notify_test(tipo)` — manda um cartão de mentira, sem tocar em `andon_events`.
- `andon_notify_status` — o estado de cada tipo, sem revelar a URL inteira.

As funções têm o `execute` revogado do papel anônimo, senão quem tem a chave publishable
conseguiria encher o canal. O gatilho de abertura continua funcionando, porque roda como o dono.

O passo a passo do lado do Teams e do Power Automate está em
[`docs/teams-andon.pdf`](../docs/teams-andon.pdf).
