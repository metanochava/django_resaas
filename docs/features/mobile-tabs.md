# Phone bottom tabs

On a phone-sized screen (Quasar `xs`, below 600px) the bottom tab bar replaces the
footer. It shows up to **5** tabs; there is no "More" tab, because the header's ☰
(top left) already opens the drawer with every menu.

## Where the tabs come from

| Level | Model | Who edits it | Where |
|---|---|---|---|
| Entity Type (template) | `EntityTypeMobileTab` | Root (`*_entitytypemobiletab`, platform permissions) | menu **Engine → Phone tabs** (`list_entitytypemobiletab`), or the **Phone tabs** panel of the Entity Type's page (`change_entitytype`) |
| Entity (override) | `EntityMobileTab` | the Entity's Admin (`*_entitymobiletab`) | menu **Engine → My phone tabs** (`list_entitymobiletab`) |

When an Entity has any active tab of its own, those replace its Entity Type's.

A tab has `label`, `icon`, `route` (a route name), `permission` (the codename it
needs), `app` (the app label), `order` and `active`.

## Which tabs a user sees

`GET users/{id}/mobile_tabs/` answers the tabs of the **current profile**
(`core/services/mobile_tab_service.tabs_for`), with the same rules as the menus:

- the tab's `permission` is among the profile's menu permissions (an Active
  assignment only; hidden permissions left out);
- its app is active for the Entity Type, entitled (`has_module`) and not hidden;
- the tab is `active`; at most `MAX_TABS` (5), in `order`.

The frontend never decides: `UserStore.MobileTabs` holds the answer and
`components/footer/MobileTabBar.vue` renders it.

## Suggesting tabs (seed)

Each module may offer candidates in `<app>/mobile_tabs.py`:

```python
TABS = [
    {"label": "Lessons", "icon": "history_edu", "route": "view_own_lesson",
     "permission": "view_own_lesson", "order": 10},
]
```

`POST entitytypemobiletabs/seed/ {entity_type, replace?}` ("Suggest tabs", also
the `seed_mobile_tabs` command) copies the candidates of the Entity Type's active
apps. An Entity Type that already has tabs keeps them unless `replace`. The core
never imports a module by name: it looks for that file.

`GET entitytypemobiletabs/?entity_type=<id>` lists one Entity Type's tabs (a
malformed id is `400` on `entity_type`).

## Code and tests

- `saas/models/mobile_tab.py`, migration `0022_entitymobiletab_entitytypemobiletab`
- `saas/core/services/mobile_tab_service.py`, `saas/data/mobile_tab/`
- `saas/management/commands/seed_mobile_tabs.py`
- quasar_resaas: `components/footer/MobileTabBar.vue`,
  `pages/entity_type_mobile_tab/`, `pages/entity_mobile_tab/`,
  `pages/entity_type/EntityTypeMobileTabsPanel.vue`
- Tests: `saas/tests/test_mobile_tabs.py`; quasar_resaas
  `components/footer/MobileTabBar.spec.js`,
  `pages/entity_type/EntityTypeMobileTabsPanel.spec.js`
