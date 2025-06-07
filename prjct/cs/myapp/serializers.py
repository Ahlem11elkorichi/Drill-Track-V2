from rest_framework import serializers
from .models import  Forage, Notification, Rapport, Rapport_imported, User
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'registration_number', 'first_name', 'last_name', 'email', 'role']
        read_only_fields = ['id']


class Rapport_importedSerializer(serializers.ModelSerializer):
    user_info = UserSerializer(source='user', read_only=True)
    class Meta:
        model = Rapport_imported
        
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

class RapportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rapport
        fields = '__all__'


class ForageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Forage
        fields = ['idForage', 'zone', 'description']

class RapportSerializer(serializers.ModelSerializer):
    forage = ForageSerializer(source='idForage', read_only=True)
    
    class Meta:
        #model = Rapport
        fields = ['idRapport', 'numRapport', 'dateActuelle', 'depthActuel', 'forage']

class NotificationSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField()
    forage_info = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    display_message = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['idnotif', 'analysed', 'forage_info', 'time_ago', 'display_message']

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
    
    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

class LoginSerializer(serializers.Serializer):
    registration_number = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)



