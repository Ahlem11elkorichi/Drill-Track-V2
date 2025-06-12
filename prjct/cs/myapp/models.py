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
    
    def __str__(self):
        return self.registration_number
    
    @property
    def is_ingenieur_terrain(self):
        return self.role == 'ingenieur_terrain'
    
    @property
    def is_responsable(self):
        return self.role == 'responsable'
class Forage(models.Model):
    idForage = models.AutoField(primary_key=True)
    zone = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    dateDebut = models.DateField(blank=True, null=True) 
    dateFin = models.DateField(blank=True, null=True)
    dureePrevistionnelle = models.IntegerField(blank=True, null=True,default=70)
    coutprevistionnel = models.FloatField(blank=True, null=True,default=11056000.0)
    coutActuel = models.FloatField(blank=True, null=True,default=0)
    durationActuelle = models.IntegerField(blank=True, null=True,default=0)

    def __str__(self):
        return f"Forage {self.idForage} - {self.zone}"
    

from enum import Enum    
class Priority(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


    @classmethod
    def choices(cls):
        return [(key.value, key.name.replace("_", " ").title()) for key in cls]
    
class Rapport_imported(models.Model):
    id_rapport_imported=models.AutoField(primary_key=True)
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    url=models.FileField()
    date_upload=models.DateField(auto_now_add=True)
    title=models.CharField(max_length=500)
    priority_remarque=models.CharField(max_length=20,choices=Priority.choices(),default=Priority.MEDIUM.value)
    observation_remarque=models.CharField(max_length=500)
    solution_remarque=models.CharField(max_length=800)
    def __str__(self):
        return f"Rapport_imported {self.url} - {self.date_upload}"
    
   
class Rapport(models.Model):
    idRapport = models.AutoField(primary_key=True)
    id_rapport_imported=models.ForeignKey(Rapport_imported,on_delete=models.SET_NULL, null=True)
    idForage = models.ForeignKey(Forage, on_delete=models.CASCADE)
    numRapport=models.IntegerField(default=0)
    dateActuelle = models.DateField(default="2024-01-01")
    nom_phase=models.CharField(default="phase X")

    def __str__(self):
        return f"Rapport {self.idRapport} - {self.dateActuelle} - {self.nom_phase} - {self.idForage}- {self.numRapport}"


class PhaseStandard(models.Model):
    idPhaseStandard = models.AutoField(primary_key=True)
    nomDePhase=models.CharField(default="0")
    coutPrevistionel = models.FloatField()
    delaiPrevistionel = models.IntegerField()
    depthStandard = models.FloatField()

    def __str__(self):
        return f"PhaseStandard {self.idPhaseStandard}"


class Phase(models.Model):
    STATUS_CHOICES = [
        ("on time", "On Time"),
        ("slightly ahead", "Slightly Ahead"),
        ("delayed", "Delayed"),
        ("inprogress", "In Progress"),
    ]
    idPhase = models.AutoField(primary_key=True)
    idPhaseStandard = models.ForeignKey(PhaseStandard, on_delete=models.SET_NULL, null=True)
    idForage = models.ForeignKey(Forage, on_delete=models.CASCADE)
    dateDebut = models.DateField(default="2024-01-01")
    depthActuel = models.FloatField(default=0)
    delaiActuel = models.IntegerField()
    coutActuel = models.FloatField()
    coutCumulatifActuel = models.FloatField()
    currentOperation = models.CharField(default="operation X")
    plannedOperation=models.CharField(default="operation Y")
    etat = models.CharField(max_length=20, choices=STATUS_CHOICES, default="in progress")

    def __str__(self):
        return f"Phase {self.idPhase} - {self.idPhaseStandard} - {self.idForage} - {self.dateDebut} - {self.depthActuel} - {self.delaiActuel} - {self.coutActuel} - {self.coutCumulatifActuel} - {self.currentOperation} - {self.plannedOperation}"
    

from enum import Enum
class Priority(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


    @classmethod
    def choices(cls):
        return [(key.value, key.name.replace("_", " ").title()) for key in cls]
    








class Notification(models.Model):
    idnotif = models.AutoField(primary_key=True)
    iduser = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    idRapport = models.ForeignKey('Rapport', on_delete=models.CASCADE)
    dateNotif = models.DateField(default=timezone.now)
    analysed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
    
    def __str__(self):
        return f"Notification #{self.idnotif} - {self.idRapport.numRapport}"
    
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
        forage = self.idRapport.idForage
        return f"Région{forage.idForage:02d} ForageX{self.idRapport.numRapport:02d} PhaseY"
    
    @property
    def sender_name(self):
        return self.idRapport.id_rapport_imported.user.get_full_name()
    
    @property
    def display_message(self):
        return f"{self.sender_name} sent a report"

