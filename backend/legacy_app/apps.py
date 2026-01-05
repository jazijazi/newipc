from django.apps import AppConfig


class LegacyAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'legacy_app'
