from django.apps import AppConfig


class NotificationsConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"

    name = "django_resaas.notifications"
    label = "notifications"

    verbose_name = "Notifications"

    def ready(self):
        """
        Regista o NotificationEngine como listener do EventDispatcher.

        `propagate=False` (omitido = default): um bug a resolver uma
        regra de notificação nunca deve derrubar a transacção de negócio
        que emitiu o evento (ex.: confirmar uma venda) - isto seria pior
        do que simplesmente não enviar a notificação. É a mesma filosofia
        de "Business Failure Isolation" da spec (secção 67), aplicada de
        forma consistente ao próprio motor, não só ao provider/fila. A
        Outbox só é criada dentro da transacção quando `resolve()` chega
        lá sem excepções - se `resolve()` falhar, a excepção é apenas
        logada e a venda continua a confirmar-se normalmente.
        """

        from django_resaas.engine.core.events import EventDispatcher
        from django_resaas.notifications.engine import NotificationEngine
        from django_resaas.notifications.providers import register_default_providers

        EventDispatcher.register("*", NotificationEngine.on_event)
        register_default_providers()
