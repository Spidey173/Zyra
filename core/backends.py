from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

UserModel = get_user_model()

class CaseInsensitiveModelBackend(ModelBackend):
    """
    Allows users to log in with their username regardless of letter casing
    (e.g., 'Ash', 'ash', 'ASH', 'Spidey', 'spidey').
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if not username or not password:
            return None
        try:
            user = UserModel.objects.get(**{f"{UserModel.USERNAME_FIELD}__iexact": username})
        except (UserModel.DoesNotExist, UserModel.MultipleObjectsReturned):
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a non-existing user.
            UserModel().set_password(password)
            return None
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None
