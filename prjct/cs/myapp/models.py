from django.conf import settings
from django.db import models
from enum import Enum
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone

from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, registration_number, password=None, **extra_fields):
        if not registration_number:
            raise ValueError('Le numéro d\'enregistrement est obligatoire')
        
        user = self.model(registration_number=registration_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, registration_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        
        return self.create_user(registration_number, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('ingenieur_terrain', 'Ingénieur Terrain'),
        ('responsable', 'Responsable'),
        ('admin', 'Administrateur'),
    )
    
    registration_number = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='ingenieur_terrain')
    date_joined = models.DateTimeField(auto_now_add=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'registration_number'
    REQUIRED_FIELDS = []
    
    class Meta:
        db_table = 'auth_user'  # Nom de table explicite pour éviter les problèmes
    
    def __str__(self):
        return self.registration_number
    
    @property
    def is_ingenieur_terrain(self):
        return self.role == 'ingenieur_terrain'
    
    @property
    def is_responsable(self):
        return self.role == 'responsable'

class Forage(models.Model):
    # Changement : nom de champ plus court et cohérent
    id_forage = models.AutoField(primary_key=True)
    zone = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    # Changement : noms de champs cohérents (snake_case)
    date_debut = models.DateField(blank=True, null=True) 
    date_fin = models.DateField(blank=True, null=True)
    duree_previstionnelle = models.IntegerField(blank=True, null=True, default=70)
    cout_previstionnel = models.FloatField(blank=True, null=True, default=11056000.0)
    cout_actuel = models.FloatField(blank=True, null=True, default=0)
    duration_actuelle = models.IntegerField(blank=True, null=True, default=0)

    class Meta:
        db_table = 'forage'
        
    def __str__(self):
        return f"Forage {self.id_forage} - {self.zone}"

class Priority(models.TextChoices):
    # Changement : Utilisation de TextChoices au lieu d'Enum pour Oracle
    HIGH = "HIGH", "High"
    MEDIUM = "MEDIUM", "Medium"
    LOW = "LOW", "Low"

class RapportImported(models.Model):
    # Changement : nom de classe en PascalCase et noms de champs cohérents
    id_rapport_imported = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    url = models.FileField(upload_to='rapports/')  # Ajout du chemin d'upload
    date_upload = models.DateField(auto_now_add=True)
    title = models.CharField(max_length=500)
    priority_remarque = models.CharField(
        max_length=20, 
        choices=Priority.choices, 
        default=Priority.MEDIUM
    )
    observation_remarque = models.CharField(max_length=500)
    solution_remarque = models.CharField(max_length=800)
    
    class Meta:
        db_table = 'rapport_imported'
    
    def __str__(self):
        return f"Rapport_imported {self.url} - {self.date_upload}"

class Rapport(models.Model):
    # Changement : noms de champs cohérents
    id_rapport = models.AutoField(primary_key=True)
    id_rapport_imported = models.ForeignKey(
        RapportImported, 
        on_delete=models.SET_NULL, 
        null=True
    )
    id_forage = models.ForeignKey(Forage, on_delete=models.CASCADE)
    num_rapport = models.IntegerField(default=0)
    date_actuelle = models.DateField(default="2024-01-01")
    nom_phase = models.CharField(max_length=100, default="phase X")  # Ajout max_length

    class Meta:
        db_table = 'rapport'

    def __str__(self):
        return f"Rapport {self.id_rapport} - {self.date_actuelle} - {self.nom_phase} - {self.id_forage} - {self.num_rapport}"

class PhaseStandard(models.Model):
    # Changement : noms de champs cohérents
    id_phase_standard = models.AutoField(primary_key=True)
    nom_de_phase = models.CharField(max_length=100, default="0")  # Ajout max_length
    cout_previstionel = models.FloatField()
    delai_previstionel = models.IntegerField()
    depth_standard = models.FloatField()

    class Meta:
        db_table = 'phase_standard'

    def __str__(self):
        return f"PhaseStandard {self.id_phase_standard}"

class Phase(models.Model):
    STATUS_CHOICES = [
        ("on_time", "On Time"),           # Changement : pas d'espaces dans les valeurs
        ("slightly_ahead", "Slightly Ahead"),
        ("delayed", "Delayed"),
        ("in_progress", "In Progress"),   # Changement : underscore au lieu d'espace
    ]
    
    # Changement : noms de champs cohérents
    id_phase = models.AutoField(primary_key=True)
    id_phase_standard = models.ForeignKey(PhaseStandard, on_delete=models.SET_NULL, null=True)
    id_forage = models.ForeignKey(Forage, on_delete=models.CASCADE)
    date_debut = models.DateField(default="2024-01-01")
    depth_actuel = models.FloatField(default=0)
    delai_actuel = models.IntegerField()
    cout_actuel = models.FloatField()
    cout_cumulatif_actuel = models.FloatField()
    current_operation = models.CharField(max_length=200, default="operation X")  # Ajout max_length
    planned_operation = models.CharField(max_length=200, default="operation Y")  # Ajout max_length
    etat = models.CharField(max_length=20, choices=STATUS_CHOICES, default="in_progress")

    class Meta:
        db_table = 'phase'

    def __str__(self):
        return f"Phase {self.id_phase} - {self.id_phase_standard} - {self.id_forage}"

class Notification(models.Model):
    # Changement : noms de champs cohérents
    id_notif = models.AutoField(primary_key=True)
    id_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    id_rapport = models.ForeignKey('Rapport', on_delete=models.CASCADE)
    date_notif = models.DateField(default=timezone.now)
    analysed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notification'
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
    
    def __str__(self):
        return f"Notification #{self.id_notif} - {self.id_rapport.num_rapport}"
    
    def mark_as_analysed(self):
        self.analysed = True
        self.save()
    
    @property
    def time_ago(self):
        now = timezone.now()
        diff = now - self.created_at
        
        if diff.days > 0:
            return f"about {diff.days} days ago"
        hours = diff.seconds // 3600
        if hours > 0:
            return f"about {hours} hours ago"
        minutes = diff.seconds // 60
        return f"about {minutes} minutes ago"
    
    @property
    def forage_info(self):
        forage = self.id_rapport.id_forage
        return f"Région{forage.id_forage:02d} ForageX{self.id_rapport.num_rapport:02d} PhaseY"
    
    @property
    def sender_name(self):
        return self.id_rapport.id_rapport_imported.user.get_full_name()
    
    @property
    def display_message(self):
        return f"{self.sender_name} sent a report"