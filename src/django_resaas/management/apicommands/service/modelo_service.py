from django_resaas.core.utils import clean_class_name, clean_file_name
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
    <AutoCrud :module="{module}" :model="{model}" :can="User.can" :ignoreFields="ignoreFields" route="view_{model}"  />
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
    return """
<template>
  <q-page class="q-pa-sm">
    
  </q-page>
</template>

<script setup>

</script>
"""


def build_view_front_view(module, model):
    return """
<template>
  <q-page class="q-pa-sm">
    
  </q-page>
</template>

<script setup>

</script>
"""


def build_view_front_Store(module, model):
    return """
<template>
  <q-page class="q-pa-sm">
    
  </q-page>
</template>

<script setup>

</script>
"""


def build_view_front_Routes(module, model):
    return """
<template>
  <q-page class="q-pa-sm">
    
  </q-page>
</template>

<script setup>

</script>
"""


def add_route(module: str, model: str):

    base = Path(settings.BASE_DIR)
    module_routes = base.parent / 'front' / 'src' / 'pages' / module / 'routes.js'

    if not module_routes.exists():
        raise CommandError(f"Arquivo não encontrado: {module_routes}")

    text = module_routes.read_text(encoding="utf-8")

    model = model.lower()
    route_var = f"{model}Routes"

    # =====================================
    # 1. IMPORT
    # =====================================
    import_line = f"import {{ {route_var} }} from './{model}/{model}Routes'\n"

    if import_line not in text:
        text = re.sub(
            r"(import .*?\n)+",
            lambda m: m.group(0) + import_line,
            text,
            count=1
        )

    # =====================================
    # 2. ARRAY DO MÓDULO
    # =====================================
    pattern = r"export\s+(const|let)\s+\w+\s*=\s*\[(.*?)\]"
    match = re.search(pattern, text, re.S)

    if not match:
        raise CommandError("Array de routes do módulo não encontrado")

    block = match.group(2)

    if f"...{route_var}" in block:
        module_routes.write_text(text, encoding="utf-8")
        return

    new_block = block.rstrip() + f"\n  ...{route_var},\n"

    text = text.replace(block, new_block)

    module_routes.write_text(text, encoding="utf-8")





def remove_route(module: str, model: str):

    base = Path(settings.BASE_DIR)
    module_routes = base.parent / 'front' / 'src' / 'pages' / module / 'routes.js'

    if not module_routes.exists():
        raise CommandError(f"Arquivo não encontrado: {module_routes}")

    text = module_routes.read_text(encoding="utf-8")

    model = model.lower()
    route_var = f"{model}Routes"

    # =====================================
    # 1. REMOVER IMPORT
    # =====================================
    text = re.sub(
        rf"\n?import\s+\{{\s*{route_var}\s*\}}\s+from\s+['\"].*?{model}/routes['\"]\n?",
        "\n",
        text
    )

    # =====================================
    # 2. REMOVER SPREAD
    # =====================================
    text = re.sub(
        rf",?\s*\.\.\.{route_var}\s*,?",
        "",
        text
    )

    # =====================================
    # 3. LIMPEZA
    # =====================================
    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r"\n\s*\n\s*\n", "\n\n", text)

    module_routes.write_text(text, encoding="utf-8")