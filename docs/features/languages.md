# Languages: default per EntityType, Entity and User

RESAAS ships two languages, Português (`pt-pt`) and English (`en-us`),
seeded as `Language` rows by `LanguageService.load_defaults()`. English is the
canonical key of every text; Portuguese is its translation (see
`CLAUDE.md`, "Language, internationalization and translations").

This page covers **which language a person sees**. How a text is translated
(`Translate.tdc()` on the backend, `tdc()` on the frontend, the
`<app>/lang/ptpt.py` files and the `Translation` rows) is unchanged.

## Resolution

The effective language follows the same chain as the theme
([Themes](themes.md)):

```
User.language  →  Entity.language  →  EntityType.language  →  platform default (pt-pt)
```

An empty level means "inherit from the next one".

| Field | Meaning | Who sets it |
|---|---|---|
| `EntityType.language` | Default of every Entity of the type, and the login screen's language before anyone signs in | Root (`change_entitytype`) |
| `Entity.language` | Default of the Entity's users | The Entity's Admin (`change_entity`), within its own Entity |
| `User.language` | The person's own choice | The user, for their own account |

`LanguageService.PLATFORM_DEFAULT_CODE` (`pt-pt`) is used when no level chose
one.

Backend: `User.get_effective_language(entity)` returns the `Language`;
`User.get_ui_sources(entity)["language"]` says where it came from
(`"user"`, `"entity"`, `"entity_type"`, or `None` for the platform default).

## API

### `GET /api/me/` (PROTECTED, `IsAuthenticated`)

| Key | Content |
|---|---|
| `language` | The **effective** language `{id, name, code}` for the Entity of the signed `X-RESAAS-Context` |
| `own_language` | The user's own choice (id), or `null` when they inherit |
| `ui_sources.language` | Where the effective language came from |

The Entity is the one in the signed tenant context, never an id sent by the
client.

### `PATCH /api/django_resaas/users/{id}/` (PROTECTED)

The same self-service path as the personal theme. A user may change their own
account; changing another user needs `change_user`, inside the same Entity.

```json
{"language": "<language id>"}   // own language
{"language": null}              // back to the Entity's / EntityType's default
```

### `GET /api/django_resaas/entitytypes/` (PUBLIC, `list` in `public_actions`)

The public catalogue (`EntityTypePublicSerializer`) carries each type's
`language` as `{id, name, code}`, or `null`. It is the only language data
exposed without a session.

Entity and EntityType forms show the `language` field through their schema
(`fields = "__all__"`); no new permission was created.

## Frontend (quasar_resaas)

- **Signed in:** `UserStore.me()` applies `language` (the effective one).
- **Choosing a language:** the header menus and the Account Center call
  `LanguageStore.choose(language)`. This applies the language and, when
  signed in, saves it with `PATCH users/{id}/` and reloads `me()`.
  `choose(null)` is the Account Center's "Use the entity's language".
- **Before signing in:** `AuthLayout.applyLanguage()` uses, in order:
  1. the language this browser picked explicitly (`userLangChosen` in local
     storage);
  2. the host EntityType's `language`;
  3. `pt-pt`.
- `userLang` (local storage) mirrors the current language and sets the `L`
  header of every request.

## Migration

`django_resaas/saas/migrations/0009_entity_and_type_default_language.py` adds
the two nullable foreign keys. Existing data is not changed and nobody's
language changes until a level is set. Backward compatible.

## Troubleshooting

- **The login screen is in the wrong language.** Check the host's EntityType
  `language` in `GET entitytypes/`. Then check `userLangChosen` in the
  browser's local storage: an explicit pick wins over the type's default.
- **A user keeps their own language after the Entity's default changed.**
  Their `own_language` is set. They can use "Use the entity's language" in the
  Account Center, or an administrator can send `{"language": null}`.
