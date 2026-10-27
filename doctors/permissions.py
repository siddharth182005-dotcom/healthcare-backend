from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsCreatorOrReadOnly(BasePermission):
    """Any authenticated user may read doctors; only the creator may modify/delete."""

    message = "Only the user who added this doctor can modify or delete it."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.created_by_id is not None and obj.created_by_id == request.user.id
