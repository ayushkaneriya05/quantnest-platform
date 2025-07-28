from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from .models import User

# dj-rest-auth handles registration and login serialization.
# We only need a serializer for our custom profile view.

class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for viewing and updating the user's profile."""
    username = serializers.CharField(
        min_length=3,
        required=False,
        allow_blank=True,
        validators=[
            UniqueValidator(queryset=User.objects.all(), message="This username is already taken.")
        ]
    )

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'bio', 'avatar')
        read_only_fields = ('id', 'email') # Do not allow email to be changed via this endpoint
    
    def validate_bio(self, value):
        if value and len(value.strip()) < 10:
            raise serializers.ValidationError("Bio must be at least 10 characters long.")
        return value

    def validate_avatar(self, value):
        if value:
            if value.size > 2 * 1024 * 1024:
                raise serializers.ValidationError("Avatar file size must be under 2MB.")
            if not value.content_type.startswith('image/'):
                raise serializers.ValidationError("Avatar must be an image file.")
        return value