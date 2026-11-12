# Form Engine

Forms that are not limited to a model's automatic fields: declarative
definitions (JSON), layered per platform, entity type, Entity and Branch,
rendered by `<s-dynamic-form>` (quasar_resaas) and validated again by the
server. Same idea as the [dashboards](dashboards.md): data, never code.

| Part | Where |
|---|---|
| Condition DSL | `saas/core/forms/dsl.py` · quasar_resaas `utils/formConditions.js` |
| Definition validation | `saas/core/forms/definition.py` |
| Layers and their merge | `saas/core/forms/merge.py`, `resolver.py`, model `FormDefinition` |
| Forms shipped by a module | `<app>/forms.py` (`FORMS = [...]`), `saas/core/forms/registry.py` |
| Submission validation | `saas/core/forms/validation.py` |
| Drafts (autosave) | model `FormDraft` |
| API | `saas/data/form_definition/views/form_definition.py` |
| Renderer | quasar_resaas `components/forms/DynamicForm.vue` (`s-dynamic-form`), `DynamicField.vue`, `registry.js`, `utils/formDefinition.js` |
| Examples | `saas/core/forms/examples.py` (clinic, hotel, school) |

## Four modes

| Mode | What it is | Submits |
|---|---|---|
| `schema` | the model's Schema 1.0 fields (a store's `fields`), as today's automatic forms | the page decides (`@submit`) |
| `declarative` | a JSON definition: sections, fields, layout, behaviour | `@submit` |
| `hybrid` | a definition whose `from_schema` fields take the model field's metadata (type, label, required, options), plus custom fields and slots (`section-<key>`, `before`, `after`, `actions`) | `@submit` |
| `workflow` | an operation, not a CRUD (dispense, receive goods, finish a consultation, confirm a sale, check in, enrol) | `POST/PUT/PATCH` to `submit.endpoint` (a relative API path with `{placeholders}` filled from `params`) |

Schema 1.0 keeps working unchanged: `AutoForm`, `FormTwo`, `ActionForm` are
untouched, and `definitionFromSchema()` turns the same fields into a
definition when a page wants the new layouts.

## A definition

```json
{
  "schema_version": "1.0",
  "key": "hotel.check_in",
  "mode": "workflow",
  "layout": "wizard",
  "autosave": true,
  "submit": {"endpoint": "hotel/stays/{id}/check_in/", "method": "post"},
  "sections": [
    {"key": "guest", "label": "Guest", "fields": [
      {"name": "full_name", "type": "text", "label": "Full name", "required": true, "locked": true},
      {"name": "foreigner", "type": "boolean", "label": "Foreign guest"},
      {"name": "passport", "type": "text", "label": "Passport number",
       "visible_if": {"field": "foreigner", "op": "eq", "value": true},
       "required_if": {"field": "foreigner", "op": "eq", "value": true},
       "validators": [{"rule": "pattern", "value": "[A-Z0-9]{6,12}"}]}
    ]},
    {"key": "stay", "label": "Stay", "fields": [
      {"name": "nights", "type": "integer", "required": true, "validators": [{"rule": "min", "value": 1}]},
      {"name": "rate", "type": "decimal"},
      {"name": "total", "type": "decimal", "calculate": {"op": "product", "of": ["nights", "rate"]}},
      {"name": "companions", "type": "repeater", "max_items": 6,
       "fields": [{"name": "name", "type": "text", "required": true}]}
    ]}
  ]
}
```

- **Layouts**: `sections` (sections as `card`, `accordion` or `plain`), `tabs`,
  `wizard` (each step validated before the next), `grid`. A field takes
  `cols` 1-12.
- **Field types**: text, textarea, email, phone, integer, decimal, boolean,
  date, time, datetime, select, multiselect, relation (remote autocomplete:
  `relation.endpoint`), file, image, editor, repeater, object (nested), custom
  (`component`).
- **Behaviour**: `visible_if`, `required_if`, `readonly_if`, `disabled_if`
  (conditions), `default`, `calculate` (`sum` / `product` / `concat` of other
  fields), `validators` (`min_length`, `max_length`, `min`, `max`, `pattern`,
  `email`, `min_items`, `max_items`), `autosave` (drafts).
- Labels are canonical English, translated at render time (`tdc`).

## Conditions (DSL)

```json
{"field": "priority", "op": "in", "value": ["urgent", "emergency"]}
{"all": [<condition>, ...]}  {"any": [<condition>, ...]}  {"not": <condition>}
```

Operators: `eq ne in not_in gt gte lt lte empty not_empty contains`; `field`
may be a dotted path. Nothing is evaluated as code - no `eval`, no
`Function`; an unknown key or operator is refused when the definition is
saved, and the frontend treats an unknown operator as false. Depth is limited
to 8 levels, a `pattern` to 200 characters.

## Layers: PLATFORM → ENTITY TYPE → ENTITY → BRANCH

A form is resolved per request from the latest **published** version of
each layer that applies (`GET /api/django_resaas/forms/resolve/?key=`):

1. platform - a `FormDefinition` row, else the module's own `<app>/forms.py`
   (required: lower layers only customise);
2. the Entity's entity type;
3. the Entity;
4. the request's Branch.

A lower layer **customises, never weakens**: it may add sections and fields,
change labels, help, order, cols, defaults, options, component, relation,
title, layout and autosave. `required` stays true once a higher layer set it,
a higher `required_if` is kept, validators accumulate, a field that is
required or `locked` above cannot be hidden, made readonly or disabled below,
and `mode`, `source` and `submit` never change below (a layer cannot redirect
where data goes). Nothing is removed.

Who keeps which layer: platform and entity type need
`manage_platform_formdefinition` (Root); an Entity's and its Branches' layers
need `add/change/delete/publish_formdefinition` (Admin) and are always the
caller's own Entity - the Entity is never taken from the client, a Branch
must be one of the Entity's. A published version never changes or goes away:
a change is a new version (`version` + 1, `draft` until `publish`).

## Security and persistence

- The backend is the authority. `POST /api/django_resaas/forms/validate/`
  (and `validate_submission()` for a domain endpoint) drops unknown fields,
  drops fields that are hidden, readonly or disabled for that data (the client
  cannot set them), recomputes calculated fields and checks required,
  types, rules and repeaters. Hidden or readonly in the browser is never
  security.
- Definitions, versions, temporary state and submitted data are separate:
  `FormDefinition` (versions), `FormDraft` (one per user, Entity, form and
  context - autosave), and the business data goes to the **domain
  endpoint / service**, never into a generic JSON store.
- The resolved form, validation and drafts are for any member of the Entity
  (signed context, no permission - drafts only the caller's own).

## Component registry (frontend)

```js
import { registerFormComponent } from 'quasar_resaas'
registerFormComponent('saude.vital-signs', VitalSignsInput)
```

A module registers its own components without touching the engine; a field
with `"type": "custom", "component": "saude.vital-signs"` (or a registered
type name) renders it with `v-model`, `field`, `label`, `error` /
`errorMessage`, `readonly`, `disable`. An unknown component shows a
placeholder, never a guess.

## Examples

`saas/core/forms/examples.py` (tested by `tests/test_examples.py`):

- **Clinic** - `saude.triage`, workflow: vital signs with bounds, a priority,
  the reason required (and shown) only when urgent.
- **Hotel** - `hotel.check_in`, workflow wizard with autosave: guest (name
  locked; passport visible and required for foreigners, with a pattern), stay
  (nights ≥ 1, the total calculated), companions (repeater, at most 6). A
  hotel's own layer may add "vehicle plate" but cannot unlock the name.
- **School** - `school.enrolment`, hybrid over `django_resaas.Person` in tabs:
  the student's fields from the model's schema, the guardian as an object
  (phone required), the course from the catalog (relation), the scholarship
  document required only with a scholarship.

## Tests

Backend: `saas/core/forms/tests/` - `test_engine.py` (DSL, validation,
merge, submissions), `test_api.py` (layers and their permissions, the
caller's Entity, versions, resolve / validate / drafts), `test_examples.py`.
Frontend: `utils/formDefinition.spec.js`, `components/forms/DynamicForm.spec.js`
(wizard, conditions, repeater, registered component, workflow submit and the
server's field errors, resolve by key).
