from rest_framework.permissions import BasePermission


class IsTenantOwner(BasePermission):
    """Allow access only to the owner of a tenant workspace."""
    message = "Only the account owner can perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == request.user.ROLE_OWNER
            and request.user.tenant is not None
        )


class IsTenantMember(BasePermission):
    """Allow access to any active member (owner or agent) of a tenant."""
    message = "You must be a member of an active workspace."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.tenant is not None
        )
