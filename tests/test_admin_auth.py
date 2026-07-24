from datetime import timedelta

from salon.app import db
from salon.models.models import AdminUser


def _create_admin(active=True):
    admin_user = AdminUser(
        name="Admin Teste",
        email="admin@example.com",
        is_active=active,
    )
    admin_user.set_password("correct-password")
    db.session.add(admin_user)
    db.session.commit()
    return admin_user


def test_dashboard_requires_authentication(client):
    response = client.get("/admin/")

    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


def test_login_has_accessible_password_visibility_toggle(client):
    response = client.get("/admin/login")
    content = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'id="passwordToggle"' in content
    assert 'type="button"' in content
    assert 'aria-label="Mostrar palavra-passe"' in content
    assert 'aria-pressed="false"' in content
    assert 'passwordInput.type = isVisible ? "password" : "text"' in content


def test_active_admin_can_login_and_logout(app, client):
    with app.app_context():
        admin_user = _create_admin()
        admin_id = admin_user.id

    response = client.post(
        "/admin/login",
        data={
            "email": "ADMIN@example.com",
            "password": "correct-password",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/")

    with client.session_transaction() as flask_session:
        assert flask_session["admin_user_id"] == admin_id
        assert flask_session.permanent is True

    dashboard = client.get("/admin/")
    assert dashboard.status_code == 200
    assert "Painel de Administração" in dashboard.get_data(as_text=True)

    logout = client.post("/admin/logout")
    assert logout.status_code == 302

    with client.session_transaction() as flask_session:
        assert "admin_user_id" not in flask_session


def test_inactive_admin_cannot_login(app, client):
    with app.app_context():
        _create_admin(active=False)

    response = client.post(
        "/admin/login",
        data={
            "email": "admin@example.com",
            "password": "correct-password",
        },
    )

    assert response.status_code == 200
    assert "inválidos" in response.get_data(as_text=True)


def test_create_admin_cli(app):
    runner = app.test_cli_runner()
    result = runner.invoke(
        args=[
            "create-admin",
            "--name",
            "CLI Admin",
            "--email",
            "cli@example.com",
            "--password",
            "cli-password",
        ]
    )

    assert result.exit_code == 0

    with app.app_context():
        admin_user = AdminUser.query.filter_by(email="cli@example.com").one()
        assert admin_user.name == "CLI Admin"
        assert admin_user.check_password("cli-password")


def test_create_admin_rejects_short_password(app):
    runner = app.test_cli_runner()
    result = runner.invoke(
        args=[
            "create-admin",
            "--name",
            "CLI Admin",
            "--email",
            "cli@example.com",
            "--password",
            "short",
        ]
    )

    assert result.exit_code != 0
    assert "pelo menos 12 caracteres" in result.output

    with app.app_context():
        assert AdminUser.query.count() == 0


def test_create_admin_rejects_invalid_email(app):
    runner = app.test_cli_runner()
    result = runner.invoke(
        args=[
            "create-admin",
            "--name",
            "CLI Admin",
            "--email",
            "invalid-email",
            "--password",
            "valid-password",
        ]
    )

    assert result.exit_code != 0
    assert "email válido" in result.output

    with app.app_context():
        assert AdminUser.query.count() == 0


def test_successful_login_clears_existing_session(app, client):
    with app.app_context():
        admin_user = _create_admin()
        admin_id = admin_user.id

    with client.session_transaction() as flask_session:
        flask_session["existing_value"] = "must-be-removed"
        flask_session["salon_slug"] = "lagos"

    response = client.post(
        "/admin/login",
        data={
            "email": "admin@example.com",
            "password": "correct-password",
        },
    )

    assert response.status_code == 302

    with client.session_transaction() as flask_session:
        assert flask_session["admin_user_id"] == admin_id
        assert "existing_value" not in flask_session
        assert "salon_slug" not in flask_session


def test_admin_session_uses_eight_hour_permanent_lifetime(app, client):
    assert app.config["PERMANENT_SESSION_LIFETIME"] == timedelta(hours=8)

    with app.app_context():
        _create_admin()

    client.post(
        "/admin/login",
        data={
            "email": "admin@example.com",
            "password": "correct-password",
        },
    )

    with client.session_transaction() as flask_session:
        assert flask_session.permanent is True
