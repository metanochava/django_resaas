# Creating a New Backend Resource

## 1. Model

``` python
class Patient(...):
    ...

    class RESAAS:
        search_fields = ["nid"]
        crud = True
```

## 2. Serializer

Create a serializer for the model, reusing the framework's base classes
whenever possible.

## 3. View

``` python
@registerView("patients")
class PatientAPIView(BaseAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
```

## 4. Routes

Register the view on the router used by the application.

## 5. Permissions

Confirm that the necessary codenames exist for list, view, add, change
and delete.

## 6. Tests

Test at least: - entity isolation; - branch isolation; - search; -
filters; - creation; - update; - removal; - permissions.
