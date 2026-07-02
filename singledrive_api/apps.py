from django.apps import AppConfig


class SingledriveApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'singledrive_api'

    def ready(self):
        # Register task modules in every process (web + worker must share the same Huey registry)
        import singledrive_api.tasks.hashing  # noqa
        import singledrive_api.tasks.thumbnails  # noqa
