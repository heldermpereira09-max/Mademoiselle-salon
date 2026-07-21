"""Baseline for the booking schema that predates Alembic."""

from alembic import op
import sqlalchemy as sa

revision = "20260720_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "salons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("address", sa.String(255)),
        sa.Column("phone", sa.String(30)),
        sa.Column("email", sa.String(150)),
        sa.Column("opening_hours_pt", sa.String(100)),
        sa.Column("opening_hours_en", sa.String(100)),
    )
    op.create_table(
        "service_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("salon_id", sa.Integer(), nullable=False),
        sa.Column("name_pt", sa.String(100), nullable=False),
        sa.Column("name_en", sa.String(100), nullable=False),
        sa.Column("icon", sa.String(50)),
        sa.Column("display_order", sa.Integer()),
        sa.ForeignKeyConstraint(["salon_id"], ["salons.id"]),
    )
    op.create_table(
        "services",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name_pt", sa.String(100), nullable=False),
        sa.Column("name_en", sa.String(100), nullable=False),
        sa.Column("description_pt", sa.Text()),
        sa.Column("description_en", sa.Text()),
        sa.Column("duration_minutes", sa.Integer()),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean()),
        sa.ForeignKeyConstraint(["category_id"], ["service_categories.id"]),
    )
    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_name", sa.String(100), nullable=False),
        sa.Column("client_email", sa.String(150)),
        sa.Column("client_phone", sa.String(30), nullable=False),
        sa.Column("salon_id", sa.Integer(), nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("appointment_date", sa.Date(), nullable=False),
        sa.Column("appointment_time", sa.Time(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("status", sa.String(20)),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("outlook_event_id", sa.String(200)),
        sa.ForeignKeyConstraint(["salon_id"], ["salons.id"]),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"]),
    )


def downgrade():
    op.drop_table("bookings")
    op.drop_table("services")
    op.drop_table("service_categories")
    op.drop_table("salons")
