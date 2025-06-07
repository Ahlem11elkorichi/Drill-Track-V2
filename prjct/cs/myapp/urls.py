from django.urls import path

from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import NotificationCountView, NotificationListView, PublicNotificationListView, RegisterView, LoginView, UserDetailView
from .views import  FichierExcelFilteredView,  Rapport_importedListCreateView, Rapport_importedView, LoginView, RapportView, RegisterView, UserDetailView
# Create a router for viewsets
router = DefaultRouter()


urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('<int:pk>/',UserDetailView.as_view(),name='user-detail'),
    path('upload-fichier/', Rapport_importedView.as_view(), name='upload-fichier'),
    path('fichier-extracted/', RapportView.as_view(), name='fichier-extracted'),
    path('api/articles/filtrer/', FichierExcelFilteredView.as_view()),
    path('rapport-imported/', Rapport_importedListCreateView.as_view()),
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/user/', UserDetailView.as_view(), name='user_detail'),
    path('notifications/', NotificationListView.as_view(), name='notifications-list'),
    path('notifications/count/', NotificationCountView.as_view(), name='notifications-count'),
    path('public/notifications/', PublicNotificationListView.as_view(), name='public-notifications'),
    path('public/notifications/mark_analysed/', PublicNotificationListView.as_view(), name='mark-notification-analysed'),

]

urlpatterns += router.urls
