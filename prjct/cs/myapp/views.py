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
    
from rest_framework.decorators import api_view

from .models import Phase, Forage
from django.db.models import Max
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Rapport, Forage
from django.core.exceptions import ObjectDoesNotExist

class DerniereRemarqueForageView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id_forage, format=None):
        try:
            forage = Forage.objects.get(idForage=id_forage)

            dernier_rapport = (
                Rapport.objects
                .filter(idForage=forage, id_rapport_imported__isnull=False)
                .select_related('id_rapport_imported')
                .order_by('-id_rapport_imported__date_upload')  # le plus récent
                .first()
            )

            if dernier_rapport and dernier_rapport.id_rapport_imported:
                rapport_imported = dernier_rapport.id_rapport_imported
                remarque = {
                    "titre": rapport_imported.title,
                    "priorite": rapport_imported.priority_remarque,
                    "observation": rapport_imported.observation_remarque,
                    "solution": rapport_imported.solution_remarque,
                    "date_upload": rapport_imported.date_upload.strftime('%Y-%m-%d')
                }
                return Response({"forage_id": forage.idForage, "remarque": remarque}, status=status.HTTP_200_OK)

            return Response({"message": "Aucune remarque disponible pour ce forage."}, status=status.HTTP_204_NO_CONTENT)

        except Forage.DoesNotExist:
            return Response({"error": "Forage non trouvé."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print("Erreur lors de la récupération de la remarque :", str(e))
            return Response({"error": "Erreur serveur."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# avec les inormations de l'utilisateurs 
# class DerniereRemarqueForageView(APIView):
#     def get(self, request, id_forage, format=None):
#         try:
#             forage = Forage.objects.get(idForage=id_forage)

#             dernier_rapport = (
#                 Rapport.objects
#                 .filter(idForage=forage, id_rapport_imported__isnull=False)
#                 .select_related('id_rapport_imported', 'id_rapport_imported__user')
#                 .order_by('-id_rapport_imported__date_upload')  # Tri décroissant par date
#                 .first()
#             )

#             if dernier_rapport and dernier_rapport.id_rapport_imported:
#                 rapport_imported = dernier_rapport.id_rapport_imported
#                 remarque = {
#                     "titre": rapport_imported.title,
#                     "priorite": rapport_imported.priority_remarque,
#                     "observation": rapport_imported.observation_remarque,
#                     "solution": rapport_imported.solution_remarque,
#                     "date_upload": rapport_imported.date_upload.strftime('%Y-%m-%d'),
#                     "utilisateur": rapport_imported.user.first_name+ " " + rapport_imported.user.last_name if rapport_imported.user else "Inconnu"  
#                 }
#                 return Response({"forage_id": forage.idForage, "remarque": remarque}, status=status.HTTP_200_OK)

#             return Response({"message": "Aucune remarque disponible pour ce forage."}, status=status.HTTP_204_NO_CONTENT)

#         except Forage.DoesNotExist:
#             return Response({"error": "Forage non trouvé."}, status=status.HTTP_404_NOT_FOUND)
#         except Exception as e:
#             print("Erreur lors de la récupération de la remarque :", str(e))
#             return Response({"error": "Erreur serveur."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
class ForagePhaseStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id_forage, format=None):
        try:
            forage = Forage.objects.get(idForage=id_forage)
            phases = Phase.objects.filter(idForage=forage)

            phase_list = []
            for phase in phases:
                phase_list.append({
                    "id_phase": phase.idPhase,
                    "nom_phase": phase.idPhaseStandard.nomDePhase if phase.idPhaseStandard else "Inconnu",
                    "etat": phase.etat,
                    "delai":phase.delaiActuel,
                    "depth":phase.depthActuel
                })

            data = {
                "id_forage": forage.idForage,
                "zone": forage.zone,
                "phases": phase_list
            }

            return Response(data, status=status.HTTP_200_OK)

        except Forage.DoesNotExist:
            return Response({"error": "Forage non trouvé."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print("Erreur serveur forage phase status:", str(e))
            return Response({"error": "Une erreur interne est survenue"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
class ForageCostStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id_forage, format=None):
        try:
            forage = Forage.objects.get(idForage=id_forage)

            cout_prev = forage.coutprevistionnel
            cout_actuel = forage.coutActuel

            if cout_prev > 0:
                pourcentage_depassement = ((cout_actuel - cout_prev) / cout_prev) * 100
            else:
                pourcentage_depassement = 0

            if pourcentage_depassement <= 10:
                statut = "green"
                statut_text = "Acceptable"
            elif pourcentage_depassement <= 25:
                statut = "orange"
                statut_text = "Slight overage"
            else:
                statut = "red"
                statut_text = "Significant overage"

            segment_vert = cout_prev * 1.1
            segment_orange = cout_prev * 1.25
            max_value = cout_prev * 1.5

            data = {
                "cout_previsionnel_forage": cout_prev,
                "cout_actuel_forage": cout_actuel,
                "pourcentage_depassement": round(pourcentage_depassement, 2),
                "statut": statut,
                "statut_text": statut_text,
                "segments": {
                    "max_value": max_value,
                    "segment_stops": [0, segment_vert, segment_orange, max_value],
                    "current_value": cout_actuel
                },
                "forage_info": {
                    "id_forage": forage.idForage,
                    "zone": forage.zone,
                    "date_debut": forage.dateDebut.strftime('%Y-%m-%d') if forage.dateDebut else None,
                    "date_fin": forage.dateFin.strftime('%Y-%m-%d') if forage.dateFin else None
                }
            }

            return Response(data, status=status.HTTP_200_OK)

        except Forage.DoesNotExist:
            return Response(
                {"error": "Forage non trouvé."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print("Erreur serveur forage cost status:", str(e))
            return Response(
                {"error": "Une erreur interne est survenue"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class PhaseDelayStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id_forage, format=None):
        try:
            latest_phase = Phase.objects.filter(idForage=id_forage).order_by('-dateDebut').first()
            if not latest_phase:
                return Response({"error": "Aucune phase trouvée pour ce forage."}, status=status.HTTP_404_NOT_FOUND)

            phase_standard = latest_phase.idPhaseStandard
            if not phase_standard:
                return Response({"error": "Aucune phase standard associée à cette phase."}, status=status.HTTP_404_NOT_FOUND)

            delai_previsionnel = phase_standard.delaiPrevistionel
            delai_actuel = latest_phase.delaiActuel

            if delai_previsionnel > 0:
                pourcentage_depassement = ((delai_actuel - delai_previsionnel) / delai_previsionnel) * 100
            else:
                pourcentage_depassement = 0

            if pourcentage_depassement <= 10:
                statut = "green"
                statut_text = "On time"
            elif pourcentage_depassement <= 25:
                statut = "orange"
                statut_text = "Slight delay"
            else:
                statut = "red"
                statut_text = "Significant delay"

            data = {
                "delai_previsionnel": delai_previsionnel,
                "delai_actuel": delai_actuel,
                "pourcentage_depassement": round(pourcentage_depassement, 2),
                "statut": statut,
                "statut_text": statut_text,
                "phase_info": {
                    "id_phase": latest_phase.idPhase,
                    "nom_phase_standard": phase_standard.nomDePhase,
                    "date_debut": latest_phase.dateDebut.strftime('%Y-%m-%d')
                }
            }
            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ForageDelayStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id_forage, format=None):
        try:
            forage = Forage.objects.get(pk=id_forage)

            duree_previsionnelle = forage.dureePrevistionnelle or 0
            duree_actuelle = forage.durationActuelle or 0

            if duree_previsionnelle > 0:
                pourcentage_depassement = ((duree_actuelle - duree_previsionnelle) / duree_previsionnelle) * 100
            else:
                pourcentage_depassement = 0

            if pourcentage_depassement <= 10:
                statut = "green"
                statut_text = "On time"
            elif pourcentage_depassement <= 25:
                statut = "orange"
                statut_text = "Slight delay"
            else:
                statut = "red"
                statut_text = "Significant delay"

            data = {
                "duree_previsionnelle": duree_previsionnelle,
                "duree_actuelle": duree_actuelle,
                "pourcentage_depassement": round(pourcentage_depassement, 2),
                "statut": statut,
                "statut_text": statut_text,
                "forage_info": {
                    "id_forage": forage.idForage,
                    "zone": forage.zone,
                    "date_debut": forage.dateDebut.strftime('%Y-%m-%d') if forage.dateDebut else None
                }
            }
            return Response(data, status=status.HTTP_200_OK)

        except Forage.DoesNotExist:
            return Response({"error": "Forage introuvable."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
class CostStatusView(APIView):
    permission_classes = [AllowAny]  # Ajustez selon vos besoins d'authentification
    
    def get(self, request, id_forage, format=None):
        try:
            print("ID Forage reçu pour cost status:", id_forage)

            # Récupère la phase la plus récente pour ce forage
            latest_phase = Phase.objects.filter(idForage=id_forage).order_by('-dateDebut').first()
            
            if not latest_phase:
                return Response(
                    {"error": "Aucune phase trouvée pour ce forage."},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Récupère la phase standard correspondante
            phase_standard = latest_phase.idPhaseStandard
            
            if not phase_standard:
                return Response(
                    {"error": "Aucune phase standard associée à cette phase."},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Calculs de comparaison basés sur les champs du modèle
            cout_previsionnel_standard = phase_standard.coutPrevistionel
            cout_cumulatif_actuel = latest_phase.coutCumulatifActuel
            
            # Calcul du pourcentage de dépassement
            if cout_previsionnel_standard > 0:
                pourcentage_depassement = ((cout_cumulatif_actuel - cout_previsionnel_standard) / cout_previsionnel_standard) * 100
            else:
                pourcentage_depassement = 0

            # Détermination du statut couleur
            # Vert: <= 10% de dépassement
            # Orange: 10% < dépassement <= 25%  
            # Rouge: > 25% de dépassement
            
            if pourcentage_depassement <= 10:
                statut = "green"
                statut_text = "Acceptable"
            elif pourcentage_depassement <= 25:
                statut = "orange"
                statut_text = "Slight overage"
            else:
                statut = "red"
                statut_text = "Significant overage"

            # Préparation des segments pour le speedometer
            # Segments basés sur le coût prévisionnel standard
            segment_vert = cout_previsionnel_standard * 1.1  # +10%
            segment_orange = cout_previsionnel_standard * 1.25  # +25%
            max_value = cout_previsionnel_standard * 1.5   # +50% pour l'échelle max

            data = {
                "cout_previsionnel_standard": cout_previsionnel_standard,
                "cout_cumulatif_actuel": cout_cumulatif_actuel,
                "pourcentage_depassement": round(pourcentage_depassement, 2),
                "statut": statut,
                "statut_text": statut_text,
                "segments": {
                    "max_value": max_value,
                    "segment_stops": [0, segment_vert, segment_orange, max_value],
                    "current_value": cout_cumulatif_actuel
                },
                "phase_info": {
                    "id_phase": latest_phase.idPhase,
                    "nom_phase_standard": phase_standard.nomDePhase,
                    "current_operation": latest_phase.currentOperation,
                    "planned_operation": latest_phase.plannedOperation,
                    "date_debut": latest_phase.dateDebut.strftime('%Y-%m-%d'),
                    "depth_actuel": latest_phase.depthActuel,
                    "delai_actuel": latest_phase.delaiActuel,
                    "cout_actuel": latest_phase.coutActuel
                }
            }

            print("Données cost status envoyées:", data)
            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            print("Erreur serveur cost status:", str(e))
            import traceback
            traceback.print_exc()
            return Response(
                {"error": "Une erreur interne est survenue"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class DashboardForageView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, id_forage, format=None):
        try:
            print("ID Forage reçu:", id_forage)

            # ✅ Utilisez 'idForage' au lieu de 'idForage_id'
            phases = Phase.objects.filter(idForage=id_forage).order_by('-dateDebut')

            if not phases.exists():
                return Response(
                    {"message": "Aucune phase trouvée pour ce forage."},
                    status=status.HTTP_404_NOT_FOUND
                )

            latest_phase = phases.first()

            data = {
                "phase_actuelle": latest_phase.currentOperation,
                "cout_cumulatif": latest_phase.coutCumulatifActuel,
                "cout_actuel": latest_phase.coutActuel,
                "nombre_de_jours": latest_phase.delaiActuel
            }

            print("Données envoyées:", data)
            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            print("Erreur serveur:", str(e))
            return Response(
                {"error": "Une erreur interne est survenue"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
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
                'priority_remarque': request.data.get('priority_remarque', Priority.MEDIUM.value),
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

