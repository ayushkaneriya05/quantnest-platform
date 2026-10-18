from django.contrib.admin.apps import AdminConfig


class QuantNestAdminConfig(AdminConfig):
    default_site = "backend.admin.QuantNestAdminSite"
