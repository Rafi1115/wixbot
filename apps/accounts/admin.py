from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import OTP, UserProfile

User = get_user_model()


class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("email", "is_deleted", "is_active", "is_staff")
    list_filter = ("is_staff", "is_superuser", )
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("username", )}),
        (
            "Permissions",
            {"fields": ("is_deleted", "is_active", "is_staff", "is_superuser")},
        ),
        ("Important dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    list_editable = ("is_active",)
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )
    search_fields = ("email",)
    ordering = ("email",)
    readonly_fields = ("created_at", "updated_at")


admin.site.register(User, CustomUserAdmin)


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ("user", "purpose", "created_at", "expires_at", "is_used")
    list_filter = ("purpose", "is_used")
    search_fields = ("user__email",)


admin.site.register(UserProfile)
