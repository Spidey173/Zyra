import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from django.test import Client

@pytest.mark.django_db
def test_user_registration_success():
    client = Client()
    url = reverse('register')
    payload = {
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'StrongPassword123!',
        'password_confirm': 'StrongPassword123!'
    }
    response = client.post(url, payload)
    assert response.status_code == 302
    assert User.objects.filter(username='newuser').exists()
    user = User.objects.get(username='newuser')
    assert hasattr(user, 'profile')

@pytest.mark.django_db
def test_user_registration_duplicate_username(user_a):
    client = Client()
    url = reverse('register')
    payload = {
        'username': 'alice',
        'email': 'different@example.com',
        'password': 'StrongPassword123!',
        'password_confirm': 'StrongPassword123!'
    }
    response = client.post(url, payload)
    assert response.status_code == 200
    assert "already exists" in response.content.decode('utf-8')

@pytest.mark.django_db
def test_user_registration_password_mismatch():
    client = Client()
    url = reverse('register')
    payload = {
        'username': 'mismatchuser',
        'email': 'mismatch@example.com',
        'password': 'PasswordOne123!',
        'password_confirm': 'PasswordTwo999!'
    }
    response = client.post(url, payload)
    assert response.status_code == 200
    assert "Passwords do not match" in response.content.decode('utf-8')
    assert not User.objects.filter(username='mismatchuser').exists()

@pytest.mark.django_db
def test_user_login_success(user_a):
    client = Client()
    url = reverse('login')
    response = client.post(url, {'username': 'alice', 'password': 'Password123!'})
    assert response.status_code == 302
    assert response.url == reverse('home')
    assert int(client.session['_auth_user_id']) == user_a.id

@pytest.mark.django_db
def test_user_login_invalid_password(user_a):
    client = Client()
    url = reverse('login')
    response = client.post(url, {'username': 'alice', 'password': 'WrongPassword!'})
    assert response.status_code == 200
    assert "Invalid username or password" in response.content.decode('utf-8')

@pytest.mark.django_db
def test_user_login_case_insensitive(user_a):
    client = Client()
    url = reverse('login')
    # Login with uppercase "ALICE" against stored "alice"
    response = client.post(url, {'username': 'ALICE', 'password': 'Password123!'})
    assert response.status_code == 302
    assert response.url == reverse('home')
    assert int(client.session['_auth_user_id']) == user_a.id

@pytest.mark.django_db
def test_user_logout(auth_client_a):
    url = reverse('logout')
    response = auth_client_a.get(url)
    assert response.status_code == 302
    assert '_auth_user_id' not in auth_client_a.session

@pytest.mark.django_db
def test_unauthenticated_user_redirect():
    client = Client()
    url = reverse('home')
    response = client.get(url)
    assert response.status_code == 302
    assert reverse('login') in response.url

@pytest.mark.django_db
def test_password_reset_token_and_update(user_a):
    from django.contrib.auth.tokens import default_token_generator
    # Generate password reset token
    token = default_token_generator.make_token(user_a)
    assert default_token_generator.check_token(user_a, token) is True

    # Update password
    user_a.set_password('BrandNewPassword999!')
    user_a.save()

    # Verify new password works and old reset token is now invalid
    assert user_a.check_password('BrandNewPassword999!') is True
    assert default_token_generator.check_token(user_a, token) is False

