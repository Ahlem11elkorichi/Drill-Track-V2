from rest_framework import serializers
from .models import Forage, Notification, Phase, PhaseStandard, Priority, Rapport, RapportImported, User

from django.db import models

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'registration_number', 'first_name', 'last_name', 'email', 'role']
        read_only_fields = ['id']


class Rapport_importedSerializer(serializers.ModelSerializer):
    user_info = UserSerializer(source='user', read_only=True)
    
    class Meta:
        model = RapportImported  # Changement : RapportImported au lieu de Rapport_imported
        fields = [
            'id_rapport_imported',
            'user',
            'url',
            'date_upload',
            'title',
            'priority_remarque',
            'observation_remarque',
            'solution_remarque',
            'user_info',
        ]
        read_only_fields = ['id_rapport_imported', 'date_upload']



class ForageSerializer(serializers.ModelSerializer):
    # Gestion des DecimalField pour Oracle
    cout_previstionnel = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    cout_actuel = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    
    class Meta:
        model = Forage
        fields = [
            'id_forage', 
            'zone', 
            'description', 
            'dateDebut', 
            'date_fin',
            'dureePrevistionnelle',
            'cout_previstionnel',
            'cout_actuel',
            'duration_actuelle'
        ]
        read_only_fields = ['id_forage']


class RapportSerializer(serializers.ModelSerializer):
    forage = ForageSerializer(source='id_forage', read_only=True)
    # Gestion explicite des champs pour Oracle
    date_actuelle = serializers.DateField()
    
    class Meta:
        model = Rapport
        fields = [
            'id_rapport', 
            'id_rapport_imported',
            'id_forage',
            'numRapport', 
            'date_actuelle', 
            'nom_phase',
            'forage'
        ]
        read_only_fields = ['id_rapport']


class NotificationSerializer(serializers.ModelSerializer):
    # Gestion explicite des champs calculés
    created_at = serializers.DateTimeField(read_only=True)
    date_notif = serializers.DateField(read_only=True)
    forage_info = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    display_message = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id_notif', 
            'id_user',
            'id_rapport',
            'date_notif',
            'analysed', 
            'created_at',
            'forage_info', 
            'time_ago', 
            'display_message'
        ]
        read_only_fields = ['id_notif', 'date_notif', 'created_at']

    def get_forage_info(self, obj):
        return obj.forage_info

    def get_time_ago(self, obj):
        return obj.time_ago

    def get_display_message(self, obj):
        return obj.display_message


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['registration_number', 'password', 'first_name', 'last_name', 'email', 'role']
        extra_kwargs = {
            'registration_number': {'max_length': 30},  # Limite Oracle
            'first_name': {'max_length': 30},
            'last_name': {'max_length': 30},
            'email': {'max_length': 100},
        }
    
    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    registration_number = serializers.CharField(required=True, max_length=30)
    password = serializers.CharField(required=True, write_only=True)


# Serializers additionnels pour les nouveaux modèles Oracle
class PhaseStandardSerializer(serializers.ModelSerializer):
    coutPrevistionel = serializers.DecimalField(max_digits=15, decimal_places=2)
    depthStandard = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        model = PhaseStandard
        fields = [
            'id_phase_standard',
            'nom_de_phase',
            'coutPrevistionel',
            'delaiPrevistionel',
            'depthStandard'
        ]
        read_only_fields = ['id_phase_standard']


class PhaseSerializer(serializers.ModelSerializer):
    # Gestion des DecimalField pour Oracle
    depthActuel = serializers.DecimalField(max_digits=10, decimal_places=2)
    cout_actuel = serializers.DecimalField(max_digits=15, decimal_places=2)
    coutCumulatifActuel = serializers.DecimalField(max_digits=15, decimal_places=2)
    dateDebut = serializers.DateField()
    
    # Relations pour affichage
    phase_standard = PhaseStandardSerializer(source='id_phase_standard', read_only=True)
    forage = ForageSerializer(source='id_forage', read_only=True)
    
    class Meta:
        model = Phase
        fields = [
            'id_phase',
            'id_phase_standard',
            'id_forage',
            'dateDebut',
            'depthActuel',
            'delaiActuel',
            'cout_actuel',
            'coutCumulatifActuel',
            'currentOperation',
            'plannedOperation',
            'etat',
            'phase_standard',
            'forage'
        ]
        read_only_fields = ['id_phase']


# Serializer pour les statistiques/dashboards
class ForageDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour les forages avec leurs phases"""
    phases = PhaseSerializer(many=True, read_only=True, source='phase_set')
    rapports = RapportSerializer(many=True, read_only=True, source='rapport_set')
    
    # Calculs pour Oracle
    cout_previstionnel = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    cout_actuel = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    
    class Meta:
        model = Forage
        fields = [
            'id_forage',
            'zone',
            'description',
            'dateDebut',
            'date_fin',
            'dureePrevistionnelle',
            'cout_previstionnel',
            'cout_actuel',
            'duration_actuelle',
            'phases',
            'rapports'
        ]


# Serializer pour validation des uploads
class FileUploadSerializer(serializers.Serializer):
    """Serializer pour la validation des fichiers uploadés"""
    file = serializers.FileField()
    title = serializers.CharField(max_length=200)
    priority_remarque = models.CharField(
        max_length=20, 
        choices=Priority.choices, 
        default=Priority.MEDIUM
    )
    observation_remarque = serializers.CharField(max_length=500)
    solution_remarque = serializers.CharField()
    
    def validate_file(self, value):
        """Validation du fichier pour Oracle"""
        # Taille maximale du fichier (exemple: 10MB)
        max_size = 10 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("Le fichier ne peut pas dépasser 10MB.")
        
        # Types de fichiers autorisés
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'text/plain']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("Type de fichier non autorisé.")
        
        return value