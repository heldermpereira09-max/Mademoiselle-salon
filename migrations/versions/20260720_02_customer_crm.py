"""Add customer CRM and historical booking prices."""

from datetime import datetime
from decimal import Decimal
import re

from alembic import op
import sqlalchemy as sa

revision = "20260720_02"
down_revision = "20260720_01"
branch_labels = None
depends_on = None


def _normalize_phone(phone):
    value = (phone or "").strip()
    digits = re.sub(r"\D", "", value)
    if value.startswith("+"):
        return f"+{digits}"
    if digits.startswith("00"):
        return f"+{digits[2:]}"
    if len(digits) == 9:
        return f"+351{digits}"
    return digits


def _backfill(bind):
    metadata = sa.MetaData()
    customers = sa.Table("customers", metadata, autoload_with=bind)
    bookings = sa.Table("bookings", metadata, autoload_with=bind)
    services = sa.Table("services", metadata, autoload_with=bind)

    rows = bind.execute(
        sa.select(
            bookings.c.id,
            bookings.c.client_name,
            bookings.c.client_email,
            bookings.c.client_phone,
            bookings.c.appointment_date,
            services.c.price,
        )
        .select_from(bookings.join(services, bookings.c.service_id == services.c.id))
        .order_by(bookings.c.created_at, bookings.c.id)
    ).mappings()

    customer_state = {}
    now = datetime.utcnow()
    for row in rows:
        normalized = _normalize_phone(row["client_phone"])
        price = Decimal(str(row["price"])).quantize(Decimal("0.01"))
        state = customer_state.get(normalized)

        if state is None:
            result = bind.execute(
                customers.insert().values(
                    name=row["client_name"],
                    email=row["client_email"] or None,
                    phone=row["client_phone"],
                    phone_normalized=normalized,
                    marketing_consent=False,
                    total_bookings=0,
                    total_spent=Decimal("0.00"),
                    loyalty_points=0,
                    loyalty_level="STANDARD",
                    created_at=now,
                    updated_at=now,
                )
            )
            state = {
                "id": result.inserted_primary_key[0],
                "count": 0,
                "spent": Decimal("0.00"),
                "first": None,
                "last": None,
                "email": row["client_email"] or None,
            }
            customer_state[normalized] = state

        state["count"] += 1
        state["spent"] += price
        visit = row["appointment_date"]
        state["first"] = visit if state["first"] is None else min(state["first"], visit)
        state["last"] = visit if state["last"] is None else max(state["last"], visit)
        if row["client_email"]:
            state["email"] = row["client_email"]

        bind.execute(
            bookings.update()
            .where(bookings.c.id == row["id"])
            .values(customer_id=state["id"], service_price=price)
        )
        bind.execute(
            customers.update()
            .where(customers.c.id == state["id"])
            .values(
                name=row["client_name"],
                email=state["email"],
                phone=row["client_phone"],
                total_bookings=state["count"],
                total_spent=state["spent"],
                first_visit=state["first"],
                last_visit=state["last"],
                updated_at=now,
            )
        )


def upgrade():
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(150)),
        sa.Column("phone", sa.String(30), nullable=False),
        sa.Column("phone_normalized", sa.String(30), nullable=False),
        sa.Column("preferred_language", sa.String(5)),
        sa.Column("marketing_consent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("birth_date", sa.Date()),
        sa.Column("preferred_contact", sa.String(20)),
        sa.Column("total_bookings", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_spent", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("first_visit", sa.Date()),
        sa.Column("last_visit", sa.Date()),
        sa.Column("loyalty_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("loyalty_level", sa.String(30), nullable=False, server_default="STANDARD"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("preferred_contact IS NULL OR preferred_contact IN ('WHATSAPP', 'EMAIL', 'PHONE')", name="ck_customers_preferred_contact"),
        sa.CheckConstraint("total_bookings >= 0", name="ck_customers_total_bookings_nonnegative"),
        sa.CheckConstraint("total_spent >= 0", name="ck_customers_total_spent_nonnegative"),
        sa.CheckConstraint("loyalty_points >= 0", name="ck_customers_loyalty_points_nonnegative"),
        sa.UniqueConstraint("phone_normalized", name="uq_customers_phone_normalized"),
    )
    op.create_index("ix_customers_phone_normalized", "customers", ["phone_normalized"])

    with op.batch_alter_table("bookings") as batch_op:
        batch_op.add_column(sa.Column("customer_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("service_price", sa.Numeric(10, 2), nullable=True))
        batch_op.create_index("ix_bookings_customer_id", ["customer_id"])
        batch_op.create_foreign_key(
            "fk_bookings_customer_id_customers",
            "customers",
            ["customer_id"],
            ["id"],
        )

    _backfill(op.get_bind())


def downgrade():
    with op.batch_alter_table("bookings") as batch_op:
        batch_op.drop_constraint("fk_bookings_customer_id_customers", type_="foreignkey")
        batch_op.drop_index("ix_bookings_customer_id")
        batch_op.drop_column("service_price")
        batch_op.drop_column("customer_id")
    op.drop_index("ix_customers_phone_normalized", table_name="customers")
    op.drop_table("customers")
