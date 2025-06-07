from datetime import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from .models import User, Forage, Notification, Priority, Rapport, Rapport_imported, User
from .serializers import LoginSerializer, NotificationSerializer, RapportSerializer, Rapport_importedSerializer, RegisterSerializer, UserSerializer
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import render, redirect
from django.contrib import messages
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .serializers import UserSerializer
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import JsonResponse
import json
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import Notification
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token 
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework import generics, permissions, status
from .permissions import IsResponsable, IsIngenieurTerrain

# class UploadFichierExcelView(APIView):
#     parser_classes = [MultiPartParser, FormParser]

#     def post(self, request, format=None):
#         serializer = FichierExcelSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


class Rapport_importedView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]
    
    def get(self, request):
        # Utilisez select_related pour optimiser les requêtes
        fichiers = Rapport_imported.objects.all().select_related('user').order_by('-date_upload')
        serializer = Rapport_importedSerializer(fichiers, many=True)
        return Response(serializer.data)
    
    def post(self, request, format=None):
        try:
            print("Request data:", request.data)
            print("Request files:", request.FILES)
            
            data = {
                'url': request.FILES.get('url'),
                'priority_remarque': request.data.get('priority_remarque', Priority.MOYENNE.value),
                'title': request.data.get('title', ''),
                'user': request.data.get('user'),
                'observation_remarque': request.data.get('observation_remarque', ''),
                'solution_remarque': request.data.get('solution_remarque', '')
            }
            
            if not data['url']:
                return Response({"error": "Excel file is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            if not data['observation_remarque']:
                return Response({"error": "Observation is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = Rapport_importedSerializer(data=data)
            
            if serializer.is_valid():
                rapport_imported = serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                print("Serializer errors:", serializer.errors)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            print(f"Exception in upload: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
class FichierExcelFilteredView(generics.ListAPIView):
    queryset = Rapport_imported.objects.all()
    serializer_class = Rapport_importedSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['date_upload']  # pour filtrer selon la dateeee, ndirou la mm chose brk on ajoute d'autres fields apres generation t3 maria


class RapportView(APIView):
    # get pour responsable 
    def get(self, request):
        fichiers = Rapport.objects.all()
        serializer = RapportSerializer(fichiers, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = RapportSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class Rapport_importedListCreateView(generics.ListCreateAPIView):
    queryset = Rapport_imported.objects.all()
    serializer_class = Rapport_importedSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['username'] = self.user.username
        # Vous pouvez ajouter d'autres informations utilisateur ici si nécessaire
        return data



# Inscription
class RegisterView(APIView):
    def post(self, request):
        data = request.data
        user = User.objects.create_user(
            email=data['email'],
            password=data['password'],
            nom=data['nom'],
            prenom=data['prenom'],
            telephone=data.get('telephone', ''),
            role=data['role']
        )
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

# Connexion
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.IsAuthenticated, IsResponsable]

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        registration_number = serializer.validated_data['registration_number']
        password = serializer.validated_data['password']
        
        user = authenticate(registration_number=registration_number, password=password)
        
        if user is None:
            return Response(
                {'error': 'Password or registration number incorrect'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })

class UserDetailView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user

class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        filter_type = request.query_params.get('filter', 'all')
        
        if filter_type == 'analysed':
            notifications = request.user.notifications.filter(analysed=True)
        elif filter_type == 'not_analysed':
            notifications = request.user.notifications.filter(analysed=False)
        else:
            notifications = request.user.notifications.all()
        
        # Group by forage info
        forage_groups = {}
        for notif in notifications.order_by('-created_at'):
            forage_key = notif.forage_info
            
            if forage_key not in forage_groups:
                forage_groups[forage_key] = []
            
            forage_groups[forage_key].append({
                "id": notif.idnotif,
                "message": notif.display_message,
                "time_ago": notif.time_ago,
                "analysed": notif.analysed,
                "forage_info": notif.forage_info
            })
        
        # Build response
        response_data = {
            "ALL": {
                "Analysed": request.user.notifications.filter(analysed=True).count(),
                "Not analysed": request.user.notifications.filter(analysed=False).count(),
            },
            "notifications": [
                {
                    "forage": forage,
                    "items": items
                }
                for forage, items in forage_groups.items()
            ]
        }
        
        return Response(response_data)
    
    def post(self, request):
        notif_id = request.data.get('id')
        try:
            notif = request.user.notifications.get(idnotif=notif_id)
            notif.mark_as_analysed()
            return Response({"status": "success"})
        except Notification.DoesNotExist:
            return Response({"status": "error", "message": "Notification not found"}, status=404)

class NotificationCountView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        count = request.user.notifications.filter(analysed=False).count()
        return Response({"count": count})
    

class PublicNotificationListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        filter_type = request.query_params.get('filter', 'all')
        last_update = request.query_params.get('last_update')
        # Retournez seulement les nouvelles notifications si last_update est fourni
        if last_update:
            new_notifs = Notification.objects.filter(created_at__gt=last_update)
            if not new_notifs.exists():
                return Response(status=304)  # Not Modified
        notifications = Notification.objects.select_related(
            'idRapport', 
            'idRapport__idForage'
        ).all()
        
        if filter_type == 'analysed':
            notifications = notifications.filter(analysed=True)
        elif filter_type == 'not_analysed':
            notifications = notifications.filter(analysed=False)
        
        results = []
        for notif in notifications:
            try:
                # Gestion des valeurs nulles
                forage_id = notif.idRapport.idForage.idForage if notif.idRapport and notif.idRapport.idForage else 0
                rapport_num = notif.idRapport.numRapport if notif.idRapport else 0
                
                results.append({
                    'id': notif.idnotif,
                    'message': f"Rapport #{rapport_num}",
                    'forage_info': f"Région{forage_id} ForageX{rapport_num}",
                    'time_ago': notif.time_ago,
                    'analysed': notif.analysed
                })
            except Exception as e:
                # Enregistrer l'erreur mais continuer le traitement
                print(f"Error processing notification {notif.idnotif}: {str(e)}")
                continue
        
        return Response({
            'analysed_count': Notification.objects.filter(analysed=True).count(),
            'not_analysed_count': Notification.objects.filter(analysed=False).count(),
            'count': len(results),
            'results': results
        })
    
    def post(self, request):
        notification_id = request.data.get('notification_id')
        try:
            notification = Notification.objects.get(idnotif=notification_id)
            notification.analysed = True
            notification.save()
            return Response({
                'status': 'success',
                'message': 'Notification marquée comme analysée'
            })
        except Notification.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Notification non trouvée'
            }, status=status.HTTP_404_NOT_FOUND)