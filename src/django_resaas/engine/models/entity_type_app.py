
from django.db import models
from django_resaas.engine.core.base.models import TimeModel
class EntityTypeApp(TimeModel):
    entity_type = models.ForeignKey("django_resaas.EntityType", on_delete=models.CASCADE)
    app = models.ForeignKey("django_resaas.App", on_delete=models.CASCADE)

    class Meta:
        unique_together = ("entity_type", "app")
        permissions = (
            
        )

    class RESAAS:
        label_field = "entity_type.name"
        # route="view_entity"
        
    def __str__(self):
        return str(self.entity_type.name) + "  |  " + str(self.app.name)

