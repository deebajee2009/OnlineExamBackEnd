from django.apps import AppConfig


class JourniesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.journies'

    def ready(self):
        # import the signals module so that
        # Django registers your handlers on startup
        import apps.journies.signals  # noqa
