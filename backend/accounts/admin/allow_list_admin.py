from django.contrib import admin

from accounts.models import AllowList


@admin.register(AllowList)
class AllowListAdmin(admin.ModelAdmin):
    list_display = ("email", "created_at")
    search_fields = ("email",)
    ordering = ("-created_at",)
