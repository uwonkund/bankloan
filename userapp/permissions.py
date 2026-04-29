from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        if request.user and request.user.is_admin:
            return True
        return request.user and request.user.is_admin

class BaseAuthPermission(BasePermission):
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            return True
        return False