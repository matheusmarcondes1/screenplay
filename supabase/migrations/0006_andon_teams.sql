-- ============================================================
-- Avisos de chamado no Microsoft Teams
--
-- O banco empurra o aviso; nada é consultado de fora. Um chamado que fica
-- aberto além do tempo configurado vira uma mensagem no canal do Teams.
--
-- O caminho é:
--   andon_events  ->  net.http_post  ->  URL do Workflows (Teams)  ->  canal
--
-- A URL do Workflows é a credencial: quem a tem consegue postar no canal.
-- Por isso ela vive AQUI, em andon_notify_config, com RLS fechada para o
-- papel anônimo. Ela nunca entra no index.html que as TVs baixam.
--
-- Aplicar:  SQL Editor do Supabase > cole este arquivo > Run.
-- Depois:   siga o guia docs/teams-andon.pdf para montar o lado do Teams.
--
-- Requer as extensões pg_net e pg_cron (Dashboard > Database > Extensions).
-- ============================================================

create extension if not exists pg_net;
create extension if not exists pg_cron;

-- ------------------------------------------------------------
-- 1. Controle do que já foi avisado
--    Fica na própria linha do chamado, então o aviso não repete se a função
--    rodar duas vezes nem se o pg_cron atrasar.
-- ------------------------------------------------------------
alter table public.andon_events
  add column if not exists notified_at   timestamptz,
  add column if not exists notify_count  integer not null default 0;

-- ------------------------------------------------------------
-- 2. Configuração, um registro por tipo de chamado
--
--    webhook_url             URL do fluxo no Teams. Vazio = não avisa.
--    enabled                 liga/desliga sem perder a URL.
--    notify_on_open          avisar já na abertura do chamado.
--    escalate_after_seconds  avisar quando passar desse tempo sem atendimento.
--                            0 junto com notify_on_open = avisa só na abertura.
--    repeat_after_seconds    repetir o aviso a cada tanto, enquanto aberto.
--                            NULL = avisa uma vez e para.
--
--    Canal único: a mesma URL nas quatro linhas.
--    Um canal por perfil: uma URL diferente em cada linha.
-- ------------------------------------------------------------
create table if not exists public.andon_notify_config (
  tipo                    text primary key
                          check (tipo in ('falta_material','qualidade','inspecao','assistente')),
  label                   text not null,
  destino                 text not null,
  cor                     text not null,
  enabled                 boolean not null default false,
  webhook_url             text,
  notify_on_open          boolean not null default false,
  escalate_after_seconds  integer not null default 180 check (escalate_after_seconds >= 0),
  repeat_after_seconds    integer check (repeat_after_seconds is null or repeat_after_seconds >= 60),
  updated_at              timestamptz not null default now()
);

comment on table public.andon_notify_config is
  'Avisos de chamado no Teams. Contém a URL do webhook: não expor ao papel anônimo.';

-- Carga inicial. Desligado, sem URL: ligar depois de montar o fluxo no Teams.
-- As cores são as mesmas que o painel usa para cada tipo.
insert into public.andon_notify_config (tipo, label, destino, cor, escalate_after_seconds)
values
  ('falta_material', 'Falta de Material', 'Material Handler',    '#C08A46', 180),
  ('qualidade',      'Qualidade',         'Coordenação Técnica', '#3E86C9', 300),
  ('inspecao',       'Inspeção',          'Inspeção',            '#2E747B', 300),
  ('assistente',     'Assistente',        'Assistentes',         '#22303A', 300)
on conflict (tipo) do nothing;

-- RLS fechada: a chave publishable não lê nem escreve esta tabela.
-- Sem política nenhuma, só o service_role e o SQL Editor chegam aqui.
alter table public.andon_notify_config enable row level security;
revoke all on public.andon_notify_config from anon, authenticated;

-- ------------------------------------------------------------
-- 3. O corpo enviado ao Teams
--
--    Os campos vão prontos para uso — titulo, resumo e cor já montados —
--    para o fluxo no Power Automate não precisar calcular nada. Quem monta
--    o cartão só referencia os campos.
-- ------------------------------------------------------------
create or replace function public.andon_notify_payload(
  ev    public.andon_events,
  cfg   public.andon_notify_config,
  motivo text
) returns jsonb
language sql
stable
as $$
  select jsonb_build_object(
    'evento',        motivo,                                 -- 'abertura' | 'escalonamento'
    'evento_label',  case motivo
                       when 'abertura' then 'Novo chamado'
                       else 'Sem atendimento'
                     end,
    'id',            ev.id,
    'tipo',          ev.type,
    'tipo_label',    cfg.label,
    'destino',       cfg.destino,
    'cor',           cfg.cor,
    'mesa',          ev.mesa,
    'mesa_label',    coalesce(lpad(ev.mesa::text, 2, '0'), '—'),
    'etapa',         coalesce(ev.etapa, '—'),
    'aberto_em',     to_char(ev.created_at, 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
    'minutos_aberto', greatest(0, floor(extract(epoch from (now() - ev.created_at)) / 60))::int,
    'aviso_numero',  cfg_count.n,
    'titulo',        cfg.label || ' · Mesa ' || coalesce(lpad(ev.mesa::text, 2, '0'), '—'),
    'resumo',        case
                       when motivo = 'abertura'
                         then coalesce(ev.etapa, 'sem etapa') || ' · chamado aberto agora'
                       else coalesce(ev.etapa, 'sem etapa') || ' · aberto há ' ||
                            greatest(1, floor(extract(epoch from (now() - ev.created_at)) / 60))::int ||
                            ' min sem atendimento'
                     end
  )
  from (select ev.notify_count + 1 as n) cfg_count;
$$;

-- ------------------------------------------------------------
-- 4. Envio
--    Uma função só, usada tanto pelo gatilho de abertura quanto pelo
--    escalonamento. Marca a linha do chamado depois de enfileirar o POST.
-- ------------------------------------------------------------
create or replace function public.andon_notify_send(
  ev_id  uuid,
  motivo text
) returns bigint
language plpgsql
security definer
set search_path = public, net, extensions
as $$
declare
  ev       public.andon_events;
  cfg      public.andon_notify_config;
  req_id   bigint;
begin
  select * into ev  from public.andon_events        where id = ev_id;
  if not found then return null; end if;

  select * into cfg from public.andon_notify_config where tipo = ev.type;
  if not found or not cfg.enabled or coalesce(cfg.webhook_url, '') = '' then
    return null;
  end if;

  select net.http_post(
           url     := cfg.webhook_url,
           body    := public.andon_notify_payload(ev, cfg, motivo),
           headers := jsonb_build_object('Content-Type', 'application/json')
         ) into req_id;

  update public.andon_events
     set notified_at  = now(),
         notify_count = notify_count + 1
   where id = ev_id;

  return req_id;
end;
$$;

-- ------------------------------------------------------------
-- 5. Aviso na abertura (opcional, por tipo)
--    pg_net é assíncrono, então o POST não segura o insert da operadora.
-- ------------------------------------------------------------
create or replace function public.andon_notify_on_insert()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if exists (
    select 1 from public.andon_notify_config
     where tipo = new.type and enabled and notify_on_open
       and coalesce(webhook_url, '') <> ''
  ) then
    perform public.andon_notify_send(new.id, 'abertura');
  end if;
  return null;
end;
$$;

drop trigger if exists andon_notify_open on public.andon_events;
create trigger andon_notify_open
  after insert on public.andon_events
  for each row execute function public.andon_notify_on_insert();

-- ------------------------------------------------------------
-- 6. Escalonamento
--    Roda de minuto em minuto. Pega os chamados ainda abertos que passaram
--    do tempo e ainda não foram avisados — ou cujo último aviso já venceu o
--    intervalo de repetição. Devolve quantos avisos enviou.
-- ------------------------------------------------------------
create or replace function public.andon_notify_tick()
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  alvo  record;
  n     integer := 0;
begin
  for alvo in
    select e.id
      from public.andon_events e
      join public.andon_notify_config c on c.tipo = e.type
     where e.status = 'aberto'
       and c.enabled
       and coalesce(c.webhook_url, '') <> ''
       and now() - e.created_at >= make_interval(secs => c.escalate_after_seconds)
       and (
             e.notified_at is null
             or (c.repeat_after_seconds is not null
                 and now() - e.notified_at >= make_interval(secs => c.repeat_after_seconds))
           )
     order by e.created_at
     limit 50                                  -- teto de segurança por rodada
  loop
    perform public.andon_notify_send(alvo.id, 'escalonamento');
    n := n + 1;
  end loop;
  return n;
end;
$$;

-- Agenda de minuto em minuto. Rodar de novo é seguro: substitui a anterior.
select cron.unschedule('andon-notify')
 where exists (select 1 from cron.job where jobname = 'andon-notify');

select cron.schedule('andon-notify', '* * * * *', $$select public.andon_notify_tick()$$);

-- ------------------------------------------------------------
-- 7. Teste
--    Manda um chamado de mentira para a URL configurada, sem tocar em
--    andon_events. Serve para conferir o fluxo do Teams antes de ligar nada.
--
--      select public.andon_notify_test('falta_material');
--
--    Depois, para ver o que o Teams respondeu:
--
--      select status_code, content from net._http_response
--       order by created desc limit 5;
-- ------------------------------------------------------------
create or replace function public.andon_notify_test(p_tipo text default 'falta_material')
returns bigint
language plpgsql
security definer
set search_path = public, net, extensions
as $$
declare
  cfg    public.andon_notify_config;
  req_id bigint;
begin
  select * into cfg from public.andon_notify_config where tipo = p_tipo;
  if not found then
    raise exception 'Tipo % não existe em andon_notify_config', p_tipo;
  end if;
  if coalesce(cfg.webhook_url, '') = '' then
    raise exception 'Sem webhook_url para %. Cole a URL do Teams antes de testar.', p_tipo;
  end if;

  select net.http_post(
    url  := cfg.webhook_url,
    body := jsonb_build_object(
      'evento',        'teste',
      'evento_label',  'Teste de configuração',
      'id',            gen_random_uuid(),
      'tipo',          cfg.tipo,
      'tipo_label',    cfg.label,
      'destino',       cfg.destino,
      'cor',           cfg.cor,
      'mesa',          7,
      'mesa_label',    '07',
      'etapa',         'SVE',
      'aberto_em',     to_char(now(), 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
      'minutos_aberto', 4,
      'aviso_numero',  1,
      'titulo',        cfg.label || ' · Mesa 07',
      'resumo',        'SVE · teste de configuração, nenhum chamado real'
    ),
    headers := jsonb_build_object('Content-Type', 'application/json')
  ) into req_id;

  return req_id;
end;
$$;

-- ------------------------------------------------------------
-- 8. Painel de conferência
--    Mostra o estado de cada tipo sem revelar a URL inteira.
--
--      select * from public.andon_notify_status;
-- ------------------------------------------------------------
create or replace view public.andon_notify_status as
  select c.tipo,
         c.label,
         c.destino,
         c.enabled,
         coalesce(c.webhook_url, '') <> ''                       as tem_url,
         case when coalesce(c.webhook_url, '') = '' then null
              else left(c.webhook_url, 38) || '…' end            as url_inicio,
         c.notify_on_open,
         c.escalate_after_seconds,
         c.repeat_after_seconds,
         (select count(*) from public.andon_events e
           where e.type = c.tipo and e.status = 'aberto')        as abertos_agora,
         (select max(e.notified_at) from public.andon_events e
           where e.type = c.tipo)                                as ultimo_aviso
    from public.andon_notify_config c
   order by c.tipo;

revoke all on public.andon_notify_status from anon, authenticated;

-- ------------------------------------------------------------
-- 9. Fechar as funções
--
--    O Postgres concede EXECUTE a PUBLIC por padrão, e estas funções são
--    SECURITY DEFINER. Sem o revoke abaixo, quem tem a chave publishable
--    conseguiria chamar andon_notify_test e encher o canal do Teams, ou
--    disparar avisos de qualquer chamado por andon_notify_send.
--
--    O gatilho de abertura continua funcionando: o Postgres só confere o
--    EXECUTE de quem cria o gatilho, não de quem dispara, e a função do
--    gatilho é SECURITY DEFINER — dentro dela quem chama andon_notify_send
--    é o dono, não a operadora.
-- ------------------------------------------------------------
revoke all on function public.andon_notify_send(uuid, text)                             from public, anon, authenticated;
revoke all on function public.andon_notify_tick()                                       from public, anon, authenticated;
revoke all on function public.andon_notify_test(text)                                   from public, anon, authenticated;
revoke all on function public.andon_notify_on_insert()                                  from public, anon, authenticated;
revoke all on function public.andon_notify_payload(public.andon_events,
                                                   public.andon_notify_config, text)    from public, anon, authenticated;
