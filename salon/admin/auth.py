from functools import wraps

from flask import redirect, request, session, url_for

from ..models.models import AdminUser


ADMIN_SESSION_KEY = "admin_user_id"


def get_current_admin():
    admin_id = session.get(ADMIN_SESSION_KEY)
    if admin_id is None:
        return None

    admin_user = AdminUser.query.filter_by(
        id=admin_id,
        is_active=True,
    ).first()

    if admin_user is None:
        session.pop(ADMIN_SESSION_KEY, None)

    return admin_user


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if get_current_admin() is None:
            return redirect(
                url_for("admin.login", next=request.full_path.rstrip("?"))
            )
        return view(*args, **kwargs)

    return wrapped_view
