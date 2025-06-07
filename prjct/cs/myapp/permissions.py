from rest_framework import permissions

class IsResponsable(permissions.BasePermission):
    """
    Permission pour les utilisateurs ayant le rôle 'responsable'
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_responsable

class IsIngenieurTerrain(permissions.BasePermission):
    """
    Permission pour les utilisateurs ayant le rôle 'ingenieur_terrain'
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_ingenieur_terrain
