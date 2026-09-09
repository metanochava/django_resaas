# Motor de dashboards dinâmicos

Backend: `django_resaas.engine.core.dashboards`
Frontend: `quasar_resaas/components/dashboard` + `quasar_resaas/stores/DashboardStore.js`

## Conceito

Qualquer app instalada pode declarar `<app>/dashboard.py` com um dict
`DASHBOARD` (só configuração, sem queries). O motor descobre, valida,
autoriza e serve os dados através de 4 endpoints genéricos - nenhum
endpoint novo é preciso por dashboard ou por widget.

```
configuração (dashboard.py)
    ↓
descoberta (DashboardDiscoveryService)
    ↓
validação (DashboardValidator)
    ↓
autorização (DashboardPermissionService)
    ↓
filtros (DashboardFilterService)
    ↓
provider (DashboardProviderRegistry)
    ↓
queryset tenant-scoped (apply_tenant_scope)
    ↓
resposta normalizada (DashboardResponseService)
    ↓
frontend (DashboardStore → DashboardRenderer → widget registry)
```

## Decisões face à arquitectura já existente

- **`TenantDashboardAPIView`** (`engine/core/base/dashboard.py`), já usada
  pelos 14 dashboards construídos antes deste motor (4 saude + 9 hr + 1
  notifications), continua a existir e a ser válida - é o padrão para um
  dashboard **hand-built** (widgets fixos, código Python próprio). O
  motor novo é para dashboards **declarativos**; as duas formas coexistem
  deliberadamente. `apply_tenant_scope`/`is_module_active` foram
  extraídas dessa classe para funções livres, reutilizadas por ambos.
- **`register_view`/`VIEW_REGISTRY`** não serve os 4 endpoints do motor
  porque só gera prefixos estáticos `{module}/{name}/`, sem parâmetros de
  path. Os 4 endpoints (`<app_name>`, `<widget_name>`, `<filter_name>`)
  estão registados directamente em `django_resaas/urls.py`, mesmo local
  onde já vivem outras rotas com converters (`password/reset/<uidb64>/
  <token>/`).
- **Permissões**: `isPermited(request, role=codename)` já existente
  (`engine/core/base/permissions.py`) - codenames simples, sem prefixo de
  app (`view_paciente`, não `saude.view_paciente`).
- **Paginação da tabela**: reutiliza o contrato real de `ResaasPagination`
  (`count/next/previous`, params `page`/`page_size`), não o
  `{page, rows_per_page, rows_number}` inicialmente sugerido - é o que
  `BaseStore`/`AutoTable` já sabem mapear (`rowsNumber = data.count`).
- **`services/dashboardRegistry.js`/`DashboardComponent.vue`** (`s-dashboard`)
  continuam a existir - são um registry client-side de dashboards
  *totalmente custom* (componentes Vue inteiros auto-registados). O
  motor novo resolve outro caso: dashboards *declarados no backend* e
  renderizados genericamente a partir de schema JSON. Não foram
  tocados.
- **Gráficos sem biblioteca nova**: não há nenhuma lib de charting
  instalada em `quasar_resaas`. `BarChartWidget`/`LineChartWidget`
  reutilizam o padrão CSS/SVG já usado em
  `pages/django_resaas/DashBoard.vue` (barras `var(--q-primary)` etc.).
  `PieChartWidget` usa `conic-gradient`. `CalendarWidget` reutiliza o
  `QDate` nativo do Quasar (`events`/`event-color`). Nenhuma dependência
  nova foi adicionada - troca por uma biblioteca real fica como melhoria
  futura se o volume/õs requisitos justificarem.
- **`entity`/`branch` como tipos de filtro**: nunca aceitam o valor do
  cliente - resolvem sempre a `request.entity_id`/`branch_id`; um valor
  diferente enviado pelo cliente é rejeitado (400), nunca ignorado
  silenciosamente.
- **Opções de filtro, estáticas vs. dinâmicas**: só existe endpoint de
  opções ao nível do *widget*
  (`.../widget/<name>/filters/<filter>/options/`), não ao nível do
  dashboard - por isso um filtro **global** com opções deve declarar
  `"options"` estático directamente em `dashboard.py` quando a lista é
  pequena/fixa (ex.: `saude/dashboard.py`'s `status`, resolvido a
  partir de `Agenda._meta.get_field("estado").choices` - introspecção,
  não query). `options_provider` fica reservado para filtros de âmbito
  **widget** cuja lista é genuinamente dinâmica/específica do tenant
  (ex.: `saude/dashboard.py`'s `medico`, filtro próprio de
  `proximas_consultas`, resolvido por `MedicoOptionsProvider` a partir
  de `hr.Employee` já tenant-scoped).

## `dashboard.py`

Só declarativo - identificação, layout, filtros, widgets (cada um com
`provider`, `permissions`/`permission_mode`, `cols`, `accepts_filters`).
Ver `dev/demo/dashboard.py` (exemplo mínimo, testado em
`django_resaas`) e `back/saude/dashboard.py` (exemplo real com os 7
tipos de widget, modelos `Paciente`/`Agenda`/`Consulta`/`Person.gender`
já existentes).

Descoberta: `importlib.import_module(f"{app_config.name}.dashboard")`
por cada app instalada, com
`except ModuleNotFoundError as exc: if exc.name == module_name: continue; raise`
- nunca esconde um import interno quebrado. App sem `dashboard.py`:
ignorada, sem erro.

## Imutabilidade

`DashboardRegistry` guarda uma cópia (`copy.deepcopy`) e devolve outra
cópia em cada leitura (`get`/`get_all`) - filtrar widgets por permissão
de um utilizador nunca pode mutar o que outro utilizador recebe depois.
Testado explicitamente (`TestRegistryImmutability`, em
`engine/tests/test_dashboard_engine.py`).

## Providers

```python
from django_resaas.engine.core.dashboards.providers import BaseDashboardProvider, register_provider

@register_provider("saude.total_pacientes")
class TotalPacientesProvider(BaseDashboardProvider):
    def resolve(self):
        qs = self.scoped_queryset(Paciente.objects.filter(state="Active"))
        value = qs.count()
        return {"value": value, "formatted_value": str(value)}
```

`resolve_provider(key)` só resolve via este registry - nunca
`import_string()` sobre uma string não controlada.

`scoped_queryset(qs)` aplica sempre `entity_id`/`branch_id` do
contexto do request (ou `entity_id` sozinho com `?scope=entity`,
exigindo `view_consolidated_dashboard_<module>` - mesma regra de
`TenantDashboardAPIView`).

## Contratos de resposta por tipo de widget

```
stat:       {value, formatted_value, variation?, variation_direction?, comparison_label?}
bar_chart:  {labels: [...], series: [{name, data: [...]}]}
line_chart: {labels: [...], series: [{name, data: [...]}]}
pie_chart:  {labels: [...], series: [{name, data: [...]}]}  (só series[0])
table:      {columns: [...], rows: [...], pagination: {count, next, previous}}
list:       {items: [{id, title, description?, icon?, avatar?, date?, status?, route?}]}
calendar:   {start, end, events: [{id, title, start, end, status?, status_color?}]}
```

## Filtros

15 tipos suportados (`validator.py`'s `SUPPORTED_FILTER_TYPES`).
Convenções:

- `multi_select`: chave repetida (`status=a&status=b`), nunca vírgula -
  é o que `services/api.js`'s `url()` já serializa.
- `date_range`/`number_range`: `{name}_from`/`{name}_to` e
  `{name}_min`/`{name}_max` - permite vários filtros deste tipo no
  mesmo dashboard (um par fixo `data_inicio`/`data_fim` não escalava).
- `entity`/`branch`: sempre pinados ao contexto, nunca ao valor do
  cliente.
- Parâmetro desconhecido para o widget → 400 (`invalid_filter`) - nunca
  ignorado em silêncio.
- **Default dinâmico != default estático**: `dashboard.py` é avaliado
  uma vez, no arranque; um filtro que precise de um default "vivo"
  (ex.: "últimos 30 dias") não deve ter `"default"` no dict - deve ser
  calculado no provider, a cada request (ver
  `saude/dashboard_providers.py`'s `_period_bounds()`).

## Endpoints

```
GET /api/django_resaas/dashboards/
GET /api/django_resaas/dashboard/<app_name>/
GET /api/django_resaas/dashboard/<app_name>/widget/<widget_name>/
GET /api/django_resaas/dashboard/<app_name>/widget/<widget_name>/filters/<filter_name>/options/
```

Todos protegidos independentemente uns dos outros - um pedido directo
ao endpoint de um widget sem autorização devolve 403, nunca dados
vazios.

## Frontend

`DashboardStore` (Pinia) - `loadDashboard(name)`, `loadWidget(name)`/
`loadAllWidgets()` (`Promise.allSettled`, uma falha não quebra os
outros), `AbortController` por widget (`markRaw()` - guardar uma
instância não-primitiva no state do Pinia sem isto fica embrulhada
numa Proxy reactiva, quebrando a comparação `===` usada para descartar
respostas antigas), filtros globais/por-widget, `depends_on`,
`startAutoRefresh()`/`stopAutoRefresh()`.

`DashboardRenderer.vue` → `DashboardHeader` + `DashboardFilters` +
grelha de `WidgetContainer` (loading/empty/error/reload, `cols`
responsivo) → componente resolvido por `components/dashboard/
registry.js` (`widgetComponents[type]`). Tipo desconhecido: mensagem
"Unsupported widget type", nunca crash.

Global: `s-dashboard-renderer` (`boot/components.js`) - uso mínimo numa
página:

```vue
<template>
  <s-dashboard-renderer name="saude" />
</template>
```

## Como adicionar um dashboard a uma app nova

1. Criar `<app>/dashboard.py` com `DASHBOARD = {...}`.
2. Criar `<app>/dashboard_providers.py` com `@register_provider(...)`
   para cada widget (import feito de dentro do próprio `dashboard.py`,
   só para correr os decorators).
3. Garantir que as permissões usadas em `permission`/`permissions` já
   existem (normalmente já existem: `view_<model>` é criado
   automaticamente para todo o modelo de `MY_APPS`).
4. Criar uma página com `<s-dashboard-renderer name="..." />` e a
   rota/entrada de sidebar correspondentes.

Nada em `DashboardRenderer.vue`, no registry central, ou noutra app
precisa de mudar.

## Como adicionar um widget do mesmo tipo

Só configuração + provider - nenhuma mudança no motor.

## Como adicionar um novo tipo de widget

1. Criar `components/dashboard/NovoWidget.vue` (props `widget`/`data`/
   `loading`).
2. `registerWidgetType('novo_tipo', NovoWidget)` (exportado de
   `quasar_resaas`) ou editar `components/dashboard/registry.js`.
3. Adicionar `'novo_tipo'` a `KNOWN_WIDGET_TYPES` em `validator.py`
   (opcional - um tipo desconhecido do backend não é erro, só perde a
   garantia de contrato).
4. Definir o contrato de resposta do provider para esse tipo.

## Testes

- Backend: `django_resaas/engine/tests/test_dashboard_engine.py` (33
  testes - discovery, imutabilidade, validator, provider registry,
  filtros, endpoints/segurança) + `back/saude/tests/
  test_dashboard_engine.py` (19 testes - os 7 widgets com dados reais,
  opções estáticas vs. dinâmicas, isolamento de tenant, os 4 perfis de
  exemplo).
- Frontend: `stores/DashboardStore.spec.js` (race conditions,
  Promise.allSettled, serialização de filtros, filtros dependentes,
  auto-refresh) + `components/dashboard/registry.spec.js`.

## Limitações actuais / melhorias futuras

- Sem layout persistido por utilizador (ordem/drag-and-drop) - a
  estrutura (`widget.order`, componentização) não bloqueia adicionar
  isto depois.
- Sem conceito real de Plano/Feature no projecto - os campos `feature`/
  `plan` do schema são aceites mas não têm enforcement (não existe
  nenhum modelo `Plan`/`Feature` para verificar).
- Gráficos são CSS/SVG feitos à mão (sem biblioteca) - suficiente para
  os contratos actuais, mas limitado para necessidades avançadas
  (zoom, exportação de imagem, animações complexas).
- `date_range`/`number_range` não suportam ainda um "default dinâmico"
  declarado em `dashboard.py` (ex.: `"default": "current_month"`) - por
  agora a resolução dinâmica fica sempre a cargo do provider.
