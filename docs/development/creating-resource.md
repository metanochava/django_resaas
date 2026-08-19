# Criar um Novo Recurso Backend

## 1. Model

``` python
class Paciente(...):
    ...

    class RESAAS:
        search_fields = ["nid"]
        crud = True
```

## 2. Serializer

Criar um serializer do model reutilizando a base do framework sempre que
possível.

## 3. View

``` python
@registerView("pacientes")
class PacienteAPIView(BaseAPIView):
    queryset = Paciente.objects.all()
    serializer_class = PacienteSerializer
```

## 4. Rotas

Registar a view no router utilizado pela aplicação.

## 5. Permissões

Confirmar que existem os codenames necessários para list, view, add,
change e delete.

## 6. Testes

Testar pelo menos: - isolamento por entidade; - isolamento por
sucursal; - pesquisa; - filtros; - criação; - atualização; - remoção; -
permissões.
