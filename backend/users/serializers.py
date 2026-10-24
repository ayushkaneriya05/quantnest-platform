from allauth.account.models import EmailAddress
from dj_rest_auth.registration.serializers import RegisterSerializer
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User
from .tokens import CustomRefreshToken


class PrivateAvatarField(serializers.ImageField):
    def to_representation(self, value):
        if not value:
            return None
        from django.core import signing
        from urllib.parse import urlencode
        from django.urls import reverse
        token = signing.dumps({"user": value.instance.pk, "name": value.name}, salt="profile-avatar")
        return reverse('avatar-content') + "?" + urlencode({"token": token})


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    token_class = CustomRefreshToken


class CustomRegisterSerializer(RegisterSerializer):
    first_name = serializers.CharField(required=True, max_length=30)
    last_name = serializers.CharField(required=True, max_length=30)

    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        data["first_name"] = self.validated_data.get("first_name", "")
        data["last_name"] = self.validated_data.get("last_name", "")
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for viewing and updating the user's profile."""

    is_email_verified = serializers.SerializerMethodField()
    avatar = PrivateAvatarField(required=False, allow_null=True)
    workspace_plan = serializers.SerializerMethodField()

    def get_workspace_plan(self, obj):
        from commercial.usage import get_account_policy
        plan = get_account_policy(obj)["plan"]
        return {"code": plan["code"], "name": plan["name"]}

    def validate_avatar(self, value):
        if value and (value.size > 2 * 1024 * 1024 or getattr(getattr(value, "image", None), "format", None) not in {"JPEG", "PNG", "WEBP"}):
            raise serializers.ValidationError("Upload a PNG, JPEG or WebP image no larger than 2 MiB.")
        return value

    def get_is_email_verified(self, obj):
        email_obj = EmailAddress.objects.filter(user=obj, email=obj.email).first()
        return email_obj.verified if email_obj else False

    username = serializers.CharField(
        min_length=3,
        required=False,
        allow_blank=True,
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message="This username is already taken.",
            )
        ],
    )
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=30)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=30)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "bio",
            "avatar",
            "is_2fa_enabled",
            "is_email_verified",
            "date_joined",
            "workspace_plan",
            "is_staff",
        )
        read_only_fields = ("id", "email", "is_2fa_enabled", "date_joined", "workspace_plan", "is_staff")

    def validate_bio(self, value):
        if value and len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Bio must be at least 10 characters long."
            )
        return value
