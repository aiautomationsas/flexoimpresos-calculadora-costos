-- Tabla de configuración editable para fundas/mangas termoencogibles.
-- Fila única (id=1). Con RLS: cualquier usuario autenticado lee (las comerciales
-- necesitan los valores para cotizar); solo el rol 'administrador' actualiza.
-- No hay políticas de insert/delete: la fila se crea aquí y no se borra.
--
-- Los valores por defecto son los aprobados por Flexo (solicitud 2026-09):
--   - rentabilidad = 50.0 (antes 45.0)
--   - costo_troquel_base = 825000, fijo y sin dividir para cualquier grafado
--     (antes (125.000 + max(700.000, tamaño)) / 2, salvo grafado 4)
-- Ejecutar manualmente en el SQL Editor de Supabase (proyecto eibcmxhzoxpayqalyhdo).

create table if not exists public.config_mangas_termoencogibles (
  id smallint primary key default 1,
  rentabilidad numeric not null default 50.0,
  costo_troquel_base numeric not null default 825000,
  actualizado_en timestamptz not null default now(),
  constraint config_mangas_singleton check (id = 1),
  constraint rentabilidad_valida check (rentabilidad > 0 and rentabilidad < 100),
  constraint costo_troquel_valido check (costo_troquel_base > 0)
);

insert into public.config_mangas_termoencogibles (id, rentabilidad, costo_troquel_base)
values (1, 50.0, 825000)
on conflict (id) do nothing;

alter table public.config_mangas_termoencogibles enable row level security;

create policy config_mangas_select_autenticados
  on public.config_mangas_termoencogibles
  for select to authenticated
  using (true);

create policy config_mangas_update_administrador
  on public.config_mangas_termoencogibles
  for update to authenticated
  using (exists (
    select 1 from public.perfiles p
    join public.roles r on r.id = p.rol_id
    where p.id = auth.uid() and r.nombre = 'administrador'
  ))
  with check (exists (
    select 1 from public.perfiles p
    join public.roles r on r.id = p.rol_id
    where p.id = auth.uid() and r.nombre = 'administrador'
  ));
