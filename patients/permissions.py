from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """Object-level check: only the user who created the patient may access it."""

    def has_object_permission(self, request, view, obj):
        return obj.owner_id == request.user.id
