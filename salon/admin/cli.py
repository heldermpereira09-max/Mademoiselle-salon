import click
from flask.cli import with_appcontext

from ..app import db
from ..models.models import AdminUser


@click.command("create-admin")
@click.option("--name", prompt="Nome", help="Nome do administrador.")
@click.option("--email", prompt="Email", help="Email único do administrador.")
@click.option(
    "--password",
    prompt="Palavra-passe",
    hide_input=True,
    confirmation_prompt=True,
    help="Palavra-passe do administrador.",
)
@with_appcontext
def create_admin_command(name, email, password):
    """Cria um utilizador administrador."""
    name = name.strip()
    email = email.strip().lower()

    if not name or not email or not password:
        raise click.ClickException("Nome, email e palavra-passe são obrigatórios.")

    if "@" not in email:
        raise click.ClickException("Introduza um endereço de email válido.")

    if len(password) < 12:
        raise click.ClickException(
            "A palavra-passe deve ter pelo menos 12 caracteres."
        )

    if AdminUser.query.filter_by(email=email).first() is not None:
        raise click.ClickException("Já existe um administrador com este email.")

    admin_user = AdminUser(name=name, email=email, is_active=True)
    admin_user.set_password(password)
    db.session.add(admin_user)
    db.session.commit()

    click.echo(f"Administrador criado: {admin_user.email}")
