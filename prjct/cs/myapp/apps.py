from django.apps import AppConfig

class MyappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myapp'

    def ready(self):
        # Connexion des signaux ici
        import myapp.signals  # C'est tout ce qu'il faut
