# Themes: templates and customized copies

**What.** A `Theme` holds the colours of the app (`primary`, `secondary`, `accent`, header,
footer, sidebar, buttons, text...) and its visual surfaces (`ThemeSurface`). An EntityType,
an Entity and a User each point to one (`theme` FK); the effective look is
**User > Entity > EntityType** (`User.get_ui_config()`, `/me/`'s `ui_config`).

Since migration `django_resaas.0007_theme_owner` a theme can have an **owner**:

| `owner_scope` (read-only, in the API) | Owner field | Meaning |
|---|---|---|
| `template` | none | Shared template: everyone may use it, nobody but `change_theme` changes it |
| `entity_type` | `owner_entity_type` | A copy customized for that EntityType |
| `entity` | `owner_entity` | A copy customized for that Entity (organisation) |
| `user` | `owner_user` | A user's personal copy |

Existing themes have no owner: they are templates. The owner fields are set only by
`customize` and are read-only for clients.

Code: `saas/models/theme.py`, `saas/data/theme/views/theme.py`,
`saas/data/theme/serializers/theme.py`. Tests: `saas/tests/test_theme_ownership.py`.

## API (`django_resaas/themes/`, PROTECTED)

| Method | Route | Who |
|---|---|---|
| `GET` | `themes/`, `themes/{id}/` | any signed-in user; **only visible themes** (below) - another's theme answers 404 |
| `POST` | `themes/` | `add_theme` (a new template) |
| `PATCH/PUT` | `themes/{id}/` | per object, below |
| `DELETE` | `themes/{id}/` | per object, below (`delete_theme` for a template) |
| `POST` | `themes/{id}/customize/` | per level, below |

**Visible:** the templates, the caller's own themes, the themes of the Entity of the signed
context (`X-RESAAS-Context`) and of that Entity's EntityType. A superuser sees all.

**Writes (per object):**

| Theme | Allowed when |
|---|---|
| template | `change_theme` / `delete_theme` (Root) |
| owner entity_type | `change_entitytype` |
| owner entity | `change_entity` **and** the signed context is that Entity |
| owner user | the caller is that user |

Missing permission → `403 permission_denied`.

### `POST themes/{id}/customize/`

Copies a visible theme (and its surfaces) for one level, applies the copy to that level's
`theme`, and answers `201` with the new theme.

```json
{"scope": "entity", "name": "Ocean (Amal)", "values": {"primary": "#15803D", "accent": "#F59E0B"}}
```

| `scope` | Target | Needs |
|---|---|---|
| `user` | the caller (`target` may only be the caller, unless superuser) | nothing more |
| `entity` | the Entity of the signed context (`target` must be it) | `change_entity` |
| `entity_type` | `target` (an EntityType id, required) | `change_entitytype` |

`values` accepts only the customizable colour fields
(`ThemeCustomizeSerializer.CUSTOMIZABLE_FIELDS`) and only plain CSS colours (`#hex`,
`rgb()/rgba()`, `hsl()/hsla()`): anything else is `400`. `name` defaults to
"<source> (<level name>)". The source theme is never changed.

## Security

Authentication → signed tenant context → per-object owner rules above. Themes are not
tenant rows (`BaseModel`), so isolation is the visibility filter of `get_queryset`: knowing a
theme's id does not let another user or organisation read or change it.

**Breaking change (0007).** Before, any signed-in user could create, change or delete any
theme (the view was only authenticated). Now templates need `change_theme`; everyone else
customizes a copy.

## Troubleshooting

| Symptom | Check |
|---|---|
| `403` on customize at Entity level | The signed context is another Entity, or the profile lacks `change_entity` |
| A theme "disappeared" | It belongs to another user / organisation (not visible), or the context Entity changed |
| `400` on customize | A value is not a plain CSS colour, or the field is not customizable |
