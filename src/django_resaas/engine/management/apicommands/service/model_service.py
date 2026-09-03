from django_resaas.engine.core.utils import clean_class_name, clean_file_name
import re
from pathlib import Path
from django.conf import settings
from django.core.management.base import CommandError


def build_view_front_list(module, model):
    clean_class_name(model)
    clean_file_name(model)
    return f"""
<template>
  <q-page class="q-pa-sm">
    <AutoCrud :module="module" :model="model" :can="User.can" :ignoreFields="ignoreFields" route="view_{clean_file_name(model)}"  />
  </q-page>
</template>

<script setup>

import {{ AutoCrud }} from 'quasar_resaas'
import {{ useUserStore }} from 'quasar_resaas'

import {{ ref, watch, onMounted}} from 'vue'
import {{ useRoute }} from 'vue-router'


const User =useUserStore()
const route = useRoute()
const module = ref('{clean_file_name(module)}')
const model = ref('{clean_class_name(model)}')
const ignoreFields = ref(['created_at','updated_at', 'created_by', 'updated_by', 'deleted_at'] )

onMounted(async () => {{

}})

// 🔥 WATCH REATIVO DA ROTA
watch(
  () => route.params,
  () => {{

  }},
  {{ immediate: true }}
)
</script>

"""


def build_view_front_save_edit(module, model):
    return f"""
<template>

  <FormSaveEdit
    :schema="schema"
    :module="module"
    :model="model"
    :data="selectedRow"
    :can-do="User.can"
    :ignore-fields="ignoreFields"
    @saved="onSaved"
  />

</template>

<script setup>
import {{ ref, onMounted, watch }} from 'vue'
import {{ useRoute }} from 'vue-router'
import {{ FormSaveEdit, buildFormFromSchema, useUserStore, HTTPAuth, url }} from 'quasar_resaas'

// ----------------------------------
// STORE
// ----------------------------------
const User = useUserStore()

// ----------------------------------
// ROUTE
// ----------------------------------
const route = useRoute()

// ----------------------------------
// STATE
// ----------------------------------
const schema = ref([])
const selectedRow = ref(null)

// ----------------------------------
// CONFIG
// ----------------------------------
const module = '{clean_file_name(module)}'
const model = '{clean_class_name(module)}'

const schemaPath = 'fields'

const ignoreFields = [
  'created_at',
  'updated_at',
  'created_by',
  'updated_by'
]

// ----------------------------------
// LOAD DATA (EDIT)
// ----------------------------------
async function loadRow(id) {{
  if (!id) {{
    selectedRow.value = null
    return
  }}

  const {{ data }} = await HTTPAuth.get(
    url({{
      type: 'u',
      url: `api/${{module}}/${{model}}s/${{id}}/`
    }})
  )

  selectedRow.value = data
}}

// ----------------------------------
// INIT
// ----------------------------------
async function init() {{
  const data = await buildFormFromSchema({{
    module,
    model,
    schemaPath,
  }})

  schema.value = data.schema

  // 🔥 verifica se tem ID na rota
  const id = route.params.id || route.query.id

  await loadRow(id)
}}

// ----------------------------------
// EVENTS
// ----------------------------------
function onSaved() {{
  console.log('salvo')
}}

// ----------------------------------
// WATCH (se mudar rota)
// ----------------------------------
watch(
  () => route.fullPath,
  async () => {{
    await init()
  }}
)

// ----------------------------------
// LIFECYCLE
// ----------------------------------
onMounted(async () => {{
  await init()
}})
</script>

"""


def build_view_front_view(module, model):
    return f"""
<template>

  <FormSaveEdit
    :schema="schema"
    :module="module"
    :model="model"
    :data="selectedRow"
    :can-do="User.can"
    :ignore-fields="ignoreFields"
    @saved="onSaved"
  />

</template>

<script setup>
import {{ ref, onMounted, watch }} from 'vue'
import {{ useRoute }} from 'vue-router'
import {{ FormSaveEdit, buildFormFromSchema, useUserStore, HTTPAuth, url }} from 'quasar_resaas'

// ----------------------------------
// STORE
// ----------------------------------
const User = useUserStore()

// ----------------------------------
// ROUTE
// ----------------------------------
const route = useRoute()

// ----------------------------------
// STATE
// ----------------------------------
const schema = ref([])
const selectedRow = ref(null)

// ----------------------------------
// CONFIG
// ----------------------------------
const module = '{clean_file_name(module)}'
const model = '{clean_class_name(module)}'

const schemaPath = 'fields'

const ignoreFields = [
  'created_at',
  'updated_at',
  'created_by',
  'updated_by'
]

// ----------------------------------
// LOAD DATA (EDIT)
// ----------------------------------
async function loadRow(id) {{
  if (!id) {{
    selectedRow.value = null
    return
  }}

  const {{ data }} = await HTTPAuth.get(
    url({{
      type: 'u',
      url: `api/${{module}}/${{model}}s/${{id}}/`
    }})
  )

  selectedRow.value = data
}}

// ----------------------------------
// INIT
// ----------------------------------
async function init() {{
  const data = await buildFormFromSchema({{
    module,
    model,
    schemaPath,
  }})

  schema.value = data.schema

  // 🔥 verifica se tem ID na rota
  const id = route.params.id || route.query.id

  await loadRow(id)
}}

// ----------------------------------
// EVENTS
// ----------------------------------
function onSaved() {{
  console.log('salvo')
}}

// ----------------------------------
// WATCH (se mudar rota)
// ----------------------------------
watch(
  () => route.fullPath,
  async () => {{
    await init()
  }}
)

// ----------------------------------
// LIFECYCLE
// ----------------------------------
onMounted(async () => {{
  await init()
}})
</script>
"""


def build_view_front_Store(module, model):
    return f"""
import {{ /* HTTPAuth, url,*/ createBaseStore }} from 'quasar_resaas' 

export const use{clean_class_name(model)}tore = createBaseStore(
  '{clean_file_name(model)}',
  {{ url: 'api/{clean_file_name(module)}/{clean_file_name(model)}s', app: '{clean_file_name(module)}', model: '{clean_class_name(model)}' }},
  {{
    state: () => ({{

    }}),

    getters: {{
      actual: (state) => state.row,
    }},

    actions: {{

    }},

    hooks: {{
      beforeLoad() {{
        
      }},

      afterLoad(data) {{
        data
      }},

      beforeCreate(form) {{
        form
      }}
    }}
  }}
)
"""


def build_view_front_Routes(module, model):
    return f"""
import {{ tdc }} from 'quasar_resaas'

export let {clean_file_name(model)}Routes = [
  {{
    path: '/list_{clean_file_name(model)}',
    name: 'list_{clean_file_name(model)}',
    component: () => import('./{clean_class_name(model)}LPage.vue'),
    meta: {{
      title: tdc('Vista de') + ' ' + tdc('{clean_file_name(model)}'),
      requiresAuth: true,
      icon: 'list',
      requiredRole: 'list_{clean_file_name(model)}',
    }},
  }},
  {{
    path: '/add_{clean_file_name(model)}',
    name: 'add_{clean_file_name(model)}',
    component: () => import('./{clean_class_name(model)}SEPage.vue'),
    meta: {{
      title: tdc('Adicionar') + ' ' + tdc('{clean_file_name(model)}'),
      requiresAuth: true,
      icon: 'add',
      requiredRole: 'add_{clean_file_name(model)}',
    }},
  }},
  {{
    path: '/change_{clean_file_name(model)}/:id',
    name: 'change_{clean_file_name(model)}',
    component: () => import('./{clean_class_name(model)}SEPage.vue'),
    meta: {{
      title: tdc('Editar') + ' ' + tdc('{clean_file_name(model)}'),
      requiresAuth: true,
      icon: 'edit',
      requiredRole: 'change_{clean_file_name(model)}',
    }},
  }},
  {{
    path: '/view_{clean_file_name(model)}/:id',
    name: 'view_{clean_file_name(model)}',
    component: () => import('./{clean_class_name(model)}VPage.vue'),
    meta: {{
      title: tdc('Visualizar') + ' ' + tdc('{clean_file_name(model)}'),
      requiresAuth: true,
      icon: 'visibility',
      requiredRole: 'view_{clean_file_name(model)}',
    }},
  }}
]

"""



def add_route(module: str, model: str):

    base = Path(settings.BASE_DIR)
    module_routes = base.parent / 'front' / 'src' / 'pages' / module / 'routes.js'

    module = module.lower()
    model = model.lower()

    module_var = f"{module}Routes"
    route_var = f"{model}Routes"

    import_line = f"import {{ {route_var} }} from './{model}/{model}Routes'\n"
    spread_line = f"  ...{route_var},\n"

    # =====================================
    # CRIAR SE NÃO EXISTIR (CORRETO)
    # =====================================
    if not module_routes.exists():
        module_routes.write_text(
f"""{import_line}

export let {module_var} = [
{spread_line}]
"""
        )
        return

    text = module_routes.read_text(encoding="utf-8")

    # =====================================
    # GARANTIR ARRAY EXISTE
    # =====================================
    if f"export let {module_var}" not in text:
        text = (
            text.strip() + "\n\n" +
f"""export let {module_var} = [
]
"""
        )

    # =====================================
    # IMPORT
    # =====================================
    if import_line not in text:
        text = import_line + text

    # =====================================
    # INSERIR NO ARRAY
    # =====================================
    pattern = rf"export\s+let\s+{module_var}\s*=\s*\[(.*?)\]"
    match = re.search(pattern, text, re.S)

    if not match:
      module_routes.write_text(text, encoding="utf-8")
      return

    block = match.group(1)

    if f"...{route_var}" in block:
      module_routes.write_text(text, encoding="utf-8")
      return

    new_block = block.rstrip() + "\n" + spread_line

    text = text.replace(block, new_block)

    module_routes.write_text(text, encoding="utf-8")


def remove_route(module: str, model: str):

    base = Path(settings.BASE_DIR)
    module_routes = base.parent / 'front' / 'src' / 'pages' / module / 'routes.js'

    if not module_routes.exists():
        return

    text = module_routes.read_text(encoding="utf-8")

    model = model.lower()
    route_var = f"{model}Routes"

    # =====================================
    # REMOVE IMPORT
    # =====================================
    text = re.sub(
        rf"\n?import\s+\{{\s*{route_var}\s*\}}\s+from\s+['\"].*?{model}/{model}Routes['\"]\n?",
        "\n",
        text
    )

    # =====================================
    # REMOVE SPREAD
    # =====================================
    text = re.sub(
        rf",?\s*\.\.\.{route_var}\s*,?",
        "",
        text
    )

    # =====================================
    # LIMPEZA
    # =====================================
    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r"\n\s*\n\s*\n", "\n\n", text)

    module_routes.write_text(text, encoding="utf-8")