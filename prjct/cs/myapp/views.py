from datetime import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from .models import RapportImported, User, Forage, Notification, Priority, Rapport, Phase, PhaseStandard
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

class LatestNotificationForageView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        try:
            latest_notification = Notification.objects.select_related(
                'id_rapport__id_forage'
            ).order_by('-created_at').first()
            
            if not latest_notification:
                return Response({
                    "error": "Aucune notification trouvée."
                }, status=status.HTTP_404_NOT_FOUND)
            
            forage = latest_notification.rapport.id_forage
            
            data = {
                "id_forage": forage.id_forage,
                "notification_info": {
                    "notification_id": latest_notification.id_notif,
                    "rapport_number": latest_notification.id_rapport.num_rapport,
                    "date_notification": latest_notification.date_notif.strftime('%Y-%m-%d'),
                    "analysed": latest_notification.analysed,
                    "time_ago": latest_notification.time_ago
                },
                "forage_info": {
                    "zone": forage.zone,
                    "description": forage.description,
                    # CORRECTION : Supprimer la typo
                    "date_debut": forage.date_debut.strftime('%Y-%m-%d') if forage.date_debut else None,
                    "date_fin": forage.date_fin.strftime('%Y-%m-%d') if forage.date_fin else None
                }
            }
            
            return Response(data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DerniereRemarqueForageView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id_forage, format=None):
        try:
            forage = Forage.objects.get(id_forage=id_forage)

            dernier_rapport = (
                Rapport.objects
                .filter(id_forage=forage, id_rapport_imported__isnull=False)
                .select_related('id_rapport_imported', 'id_rapport_imported__user')
                .order_by('-id_rapport_imported__date_upload')
                .first()
            )

            if dernier_rapport and dernier_rapport.id_rapport_imported:
                rapport_imported = dernier_rapport.id_rapport_imported
                remarque = {
                    "titre": rapport_imported.title,
                    "priorite": rapport_imported.priority_remarque,
                    "observation": rapport_imported.observation_remarque,
                    "solution": rapport_imported.solution_remarque,
                    "date_upload": rapport_imported.date_upload.strftime('%Y-%m-%d'),
                    "utilisateur": f"{rapport_imported.user.first_name} {rapport_imported.user.last_name}" if rapport_imported.user else "Inconnu"
                }
                return Response({"forage_id": forage.id_forage, "remarque": remarque}, status=status.HTTP_200_OK)

            return Response({"message": "Aucune remarque disponible pour ce forage."}, status=status.HTTP_204_NO_CONTENT)

        except Forage.DoesNotExist:
            return Response({"error": "Forage non trouvé."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print("Erreur lors de la récupération de la remarque :", str(e))
            return Response({"error": "Erreur serveur."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ForagePhaseStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id_forage, format=None):
        try:
            forage = Forage.objects.get(id_forage=id_forage)
            phases = Phase.objects.filter(id_forage=forage)

            phase_list = []
            for phase in phases:
                phase_list.append({
                    "id_phase": phase.id_phase,
                    "nom_phase": phase.id_phase_standard.nom_de_phase if phase.id_phase_standard else "Inconnu",
                    "etat": phase.etat,
                    "delai": phase.delai_actuel,
                    "depth": phase.depth_actuel
                })

            data = {
                "id_forage": forage.id_forage,
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
            forage = Forage.objects.get(id_forage=id_forage)

            cout_prev = forage.cout_previstionnel or 0
            cout_actuel = forage.cout_actuel or 0

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
                "cout_previsionnel_forage": float(cout_prev),
                "cout_actuel_forage": float(cout_actuel),
                "pourcentage_depassement": round(pourcentage_depassement, 2),
                "statut": statut,
                "statut_text": statut_text,
                "segments": {
                    "max_value": float(max_value),
                    "segment_stops": [0, float(segment_vert), float(segment_orange), float(max_value)],
                    "current_value": float(cout_actuel)
                },
                "forage_info": {
                    "id_forage": forage.id_forage,
                    "zone": forage.zone,
                    "date_debut": forage.date_debut.strftime('%Y-%m-%d') if forage.date_debut else None,
                    "date_fin": forage.date_fin.strftime('%Y-%m-%d') if forage.date_fin else None
                }
            }

            return Response(data, status=status.HTTP_200_OK)

        except Forage.DoesNotExist:
            return Response({"error": "Forage non trouvé."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print("Erreur serveur forage cost status:", str(e))
            return Response({"error": "Une erreur interne est survenue"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PhaseDelayStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id_forage, format=None):
        try:
            latest_phase = Phase.objects.filter(id_forage=id_forage).order_by('-date_debut').first()
            if not latest_phase:
                return Response({"error": "Aucune phase trouvée pour ce forage."}, status=status.HTTP_404_NOT_FOUND)

            phase_standard = latest_phase.id_phase_standard
            if not phase_standard:
                return Response({"error": "Aucune phase standard associée à cette phase."}, status=status.HTTP_404_NOT_FOUND)

            delai_previsionnel = phase_standard.delai_previstionel or 0
            delai_actuel = latest_phase.delai_actuel or 0

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
                    "id_phase": latest_phase.id_phase,
                    "nom_phase_standard": phase_standard.nom_de_phase,
                    "date_debut": latest_phase.date_debut.strftime('%Y-%m-%d')
                }
            }
            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ForageDelayStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id_forage, format=None):
        try:
            forage = Forage.objects.get(id_forage=id_forage)

            duree_previsionnelle = forage.duree_previstionnelle or 0
            duree_actuelle = forage.duration_actuelle or 0

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
                    "id_forage": forage.id_forage,
                    "zone": forage.zone,
                    "date_debut": forage.date_debut.strftime('%Y-%m-%d') if forage.date_debut else None,
                }
            }
            return Response(data, status=status.HTTP_200_OK)

        except Forage.DoesNotExist:
            return Response({"error": "Forage introuvable."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CostStatusView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, id_forage, format=None):
        try:
            latest_phase = Phase.objects.filter(id_forage=id_forage).order_by('-date_debut').first()
            if not latest_phase:
                return Response({"error": "Aucune phase trouvée pour ce forage."}, status=status.HTTP_404_NOT_FOUND)

            phase_standard = latest_phase.id_phase_standard
            if not phase_standard:
                return Response({"error": "Aucune phase standard associée à cette phase."}, status=status.HTTP_404_NOT_FOUND)

            cout_previsionnel_standard = phase_standard.cout_previstionel or 0
            cout_cumulatif_actuel = latest_phase.cout_cumulatif_actuel or 0
            
            if cout_previsionnel_standard > 0:
                pourcentage_depassement = ((cout_cumulatif_actuel - cout_previsionnel_standard) / cout_previsionnel_standard) * 100
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

            segment_vert = cout_previsionnel_standard * 1.1
            segment_orange = cout_previsionnel_standard * 1.25
            max_value = cout_previsionnel_standard * 1.5

            data = {
                "cout_previsionnel_standard": float(cout_previsionnel_standard),
                "cout_cumulatif_actuel": float(cout_cumulatif_actuel),
                "pourcentage_depassement": round(pourcentage_depassement, 2),
                "statut": statut,
                "statut_text": statut_text,
                "segments": {
                    "max_value": float(max_value),
                    "segment_stops": [0, float(segment_vert), float(segment_orange), float(max_value)],
                    "current_value": float(cout_cumulatif_actuel)
                },
                "phase_info": {
                    "id_phase": latest_phase.id_phase,
                    "nom_phase_standard": phase_standard.nom_de_phase,
                    "current_operation": latest_phase.current_operation,
                    "planned_operation": latest_phase.planned_operation,
                    "date_debut": latest_phase.date_debut.strftime('%Y-%m-%d'),
                    "depth_actuel": float(latest_phase.depth_actuel) if latest_phase.depth_actuel else 0,
                    "delai_actuel": latest_phase.delai_actuel,
                    "cout_actuel": float(latest_phase.cout_actuel) if latest_phase.cout_actuel else 0
                }
            }

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            print("Erreur serveur cost status:", str(e))
            return Response({"error": "Une erreur interne est survenue"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DashboardForageView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, id_forage, format=None):
        try:
            phases = Phase.objects.filter(id_forage=id_forage).order_by('-date_debut')

            if not phases.exists():
                return Response({"message": "Aucune phase trouvée pour ce forage."}, status=status.HTTP_404_NOT_FOUND)

            latest_phase = phases.first()

            data = {
                "phase_actuelle": latest_phase.current_operation,
                "cout_cumulatif": float(latest_phase.cout_cumulatif_actuel) if latest_phase.cout_cumulatif_actuel else 0,
                "cout_actuel": float(latest_phase.cout_actuel) if latest_phase.cout_actuel else 0,
                "nombre_de_jours": latest_phase.delai_actuel
            }

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            print("Erreur serveur:", str(e))
            return Response({"error": "Une erreur interne est survenue"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class Rapport_importedView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]
    
    def get(self, request):
        fichiers = RapportImported.objects.all().select_related('user').order_by('-date_upload')
        serializer = Rapport_importedSerializer(fichiers, many=True)
        return Response(serializer.data)
    
    def post(self, request, format=None):
        try:
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
    queryset = RapportImported.objects.all()
    serializer_class = Rapport_importedSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['date_upload']

class RapportView(APIView):
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
    queryset = RapportImported.objects.all()
    serializer_class = Rapport_importedSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['username'] = self.user.registration_number
        return data

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
        
        user = authenticate(request, registration_number=registration_number, password=password)
        
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
    permission_classes = [AllowAny]

    def get(self, request):
        filter_type = request.query_params.get('filter', 'all')
    
        if filter_type == 'analysed':
            notifications = Notification.objects.filter(analysed=True)
        elif filter_type == 'not_analysed':
            notifications = Notification.objects.filter(analysed=False)
        else:
            notifications = Notification.objects.all()
         
        forage_groups = {}
        for notif in notifications.order_by('-created_at'):
            forage_key = notif.forage_info
            
            if forage_key not in forage_groups:
                forage_groups[forage_key] = []
            
            forage_groups[forage_key].append({
                "id": notif.id_notif,
                "message": notif.display_message,
                "time_ago": notif.time_ago,
                "analysed": notif.analysed,
                "forage_info": notif.forage_info
            })
        
        response_data = {
            "ALL": {
                "Analysed": Notification.objects.filter(analysed=True).count(),
                "Not analysed": Notification.objects.filter(analysed=False).count(),
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
            notif = Notification.objects.get(id_notif=notif_id)
            notif.analysed = True
            notif.save()
            return Response({"status": "success"})
        except Notification.DoesNotExist:
            return Response({"status": "error", "message": "Notification not found"}, status=404)

class NotificationCountView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        count = Notification.objects.filter(analysed=False).count()
        return Response({"count": count})

class PublicNotificationListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        filter_type = request.query_params.get('filter', 'all')
        last_update = request.query_params.get('last_update')
        
        if last_update:
            new_notifs = Notification.objects.filter(created_at__gt=last_update)
            if not new_notifs.exists():
                return Response(status=304)
                
        notifications = Notification.objects.select_related(
            'id_rapport', 
            'id_rapport__id_forage'
        ).all()
        
        if filter_type == 'analysed':
            notifications = notifications.filter(analysed=True)
        elif filter_type == 'not_analysed':
            notifications = notifications.filter(analysed=False)
        
        results = []
        for notif in notifications:
            try:
                forage_id = notif.id_rapport.id_forage.id_forage if notif.id_rapport and notif.id_rapport.id_forage else 0
                rapport_num = notif.id_rapport.num_rapport if notif.id_rapport else 0
                phase = notif.id_rapport.nom_phase if notif.id_rapport else "Unknown"
                zone = notif.id_rapport.id_forage.zone if notif.id_rapport and notif.id_rapport.id_forage else "Unknown"
                
                results.append({
                    'id': notif.id_notif,
                    'message': f"Rapport #{rapport_num}",
                    'forage_info': f"Zone: {zone} | Phase: {phase}",
                    'time_ago': notif.time_ago,
                    'analysed': notif.analysed,
                    'id_forage': forage_id
                })
            except Exception as e:
                print(f"Error processing notification {notif.id_notif}: {str(e)}")
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
            notification = Notification.objects.get(id_notif=notification_id)
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