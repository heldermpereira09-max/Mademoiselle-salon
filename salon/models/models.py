from datetime import datetime
from ..app import db


class Salon(db.Model):
    __tablename__ = "salons"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)

    categories = db.relationship(
        "ServiceCategory",
        back_populates="salon",
        cascade="all, delete-orphan"
    )

    bookings = db.relationship(
        "Booking",
        back_populates="salon",
        cascade="all, delete-orphan"
    )


class ServiceCategory(db.Model):
    __tablename__ = "service_categories"

    id = db.Column(db.Integer, primary_key=True)

    salon_id = db.Column(
        db.Integer,
        db.ForeignKey("salons.id"),
        nullable=False
    )

    salon = db.relationship(
        "Salon",
        back_populates="categories"
    )

    name_pt = db.Column(db.String(100), nullable=False)
    name_en = db.Column(db.String(100), nullable=False)
    icon = db.Column(db.String(50), default="sparkles")
    display_order = db.Column(db.Integer, default=0)

    services = db.relationship("Service", back_populates="category", lazy=True)

    def name(self, lang="pt"):
        return self.name_pt if lang == "pt" else self.name_en


class Service(db.Model):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    name_pt = db.Column(db.String(100), nullable=False)
    name_en = db.Column(db.String(100), nullable=False)
    description_pt = db.Column(db.Text)
    description_en = db.Column(db.Text)
    duration_minutes = db.Column(db.Integer, default=60)
    price = db.Column(db.Float, nullable=False)

    category_id = db.Column(
        db.Integer,
        db.ForeignKey("service_categories.id"),
        nullable=False
    )

    category = db.relationship("ServiceCategory", back_populates="services")
    active = db.Column(db.Boolean, default=True)

    def name(self, lang="pt"):
        return self.name_pt if lang == "pt" else self.name_en

    def description(self, lang="pt"):
        return self.description_pt if lang == "pt" else self.description_en


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(100), nullable=False)
    client_email = db.Column(db.String(150), nullable=False)
    client_phone = db.Column(db.String(30))

    salon_id = db.Column(
        db.Integer,
        db.ForeignKey("salons.id"),
        nullable=False
    )

    salon = db.relationship(
        "Salon",
        back_populates="bookings"
    )

    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    service = db.relationship("Service")

    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    outlook_event_id = db.Column(db.String(200))

    @property
    def appointment_datetime(self):
        return datetime.combine(self.appointment_date, self.appointment_time)


def seed_data():
    if Salon.query.first():
        return

    lagos = Salon(name="Lagos", slug="lagos")
    luz = Salon(name="Praia da Luz", slug="praia-da-luz")

    db.session.add_all([lagos, luz])
    db.session.flush()

    def criar_categorias(salon):
        categorias = {
            "pedicure": ServiceCategory(name_pt="Pedicure", name_en="Pedicure", icon="sparkles", display_order=1, salon=salon),
            "manicure": ServiceCategory(name_pt="Manicure", name_en="Manicure", icon="hand", display_order=2, salon=salon),
            "depilacao": ServiceCategory(name_pt="Depilação", name_en="Waxing", icon="leaf", display_order=3, salon=salon),
            "sobrancelhas": ServiceCategory(name_pt="Sobrancelhas", name_en="Eyebrows", icon="palette", display_order=4, salon=salon),
            "pestanas": ServiceCategory(name_pt="Pestanas", name_en="Eyelashes", icon="scissors", display_order=5, salon=salon),
            "faciais": ServiceCategory(name_pt="Faciais", name_en="Facials", icon="flower", display_order=6, salon=salon),
            "massagem": ServiceCategory(name_pt="Massagem", name_en="Massage", icon="flower", display_order=7, salon=salon),
        }
        db.session.add_all(categorias.values())
        db.session.flush()
        return categorias

    cat_lagos = criar_categorias(lagos)
    cat_luz = criar_categorias(luz)

    servicos_base = [
        ("pedicure", "Pedicure Completa", "Complete Pedicure", "Pedicure completa com cuidado dos pés.", "Complete pedicure with foot care.", 30, 20.00, 25.00),
        ("pedicure", "SPA Pedicure", "SPA Pedicure", "Pedicure relaxante com tratamento SPA.", "Relaxing pedicure with SPA treatment.", 40, 30.00, 40.00),
        ("pedicure", "Verniz de Gel", "Gel Polish", "Verniz gel de longa duração.", "Long-lasting gel polish.", 60, 28.00, 35.00),
        ("pedicure", "Cortar + Pintar", "Cut + Paint", "Corte e pintura das unhas dos pés.", "Nail cut and polish for feet.", 15, 10.00, 12.50),

        ("manicure", "Manicure Normal", "Regular Manicure", "Manicure clássica com cuidado das mãos.", "Classic manicure with hand care.", 30, 15.00, 15.00),
        ("manicure", "SPA das Mãos", "Hand SPA", "Tratamento SPA hidratante para as mãos.", "Moisturising SPA treatment for hands.", 30, 25.00, 25.00),
        ("manicure", "Verniz de Gel", "Gel Polish", "Verniz gel de longa duração.", "Long-lasting gel polish.", 60, 18.00, 25.00),
        ("manicure", "Extensões", "Extensions", "Extensões de unhas em gel.", "Gel nail extensions.", 90, 35.00, 45.00),
        ("manicure", "Manutenção", "Maintenance", "Manutenção e retoque das unhas em gel.", "Maintenance and touch-up of gel nails.", 60, 28.00, 30.00),
        ("manicure", "Manicure Francesa", "French Manicure", "Manicure francesa com acabamento clássico.", "French manicure with a classic finish.", 120, 30.00, 35.00),
        ("manicure", "Remover Gel", "Gel Removal", "Remoção segura do gel.", "Safe gel removal.", 30, 10.00, 12.50),

        ("depilacao", "Meia Perna", "Half Leg", "Depilação da meia perna com cera.", "Half leg waxing.", 15, 10.00, 15.00),
        ("depilacao", "Perna Inteira", "Full Leg", "Depilação da perna inteira com cera.", "Full leg waxing.", 30, 17.00, 22.00),
        ("depilacao", "Perna + Virilha", "Leg + Bikini", "Depilação da perna e virilha com cera.", "Leg and bikini waxing.", 30, 25.00, 30.00),
        ("depilacao", "Virilha", "Bikini", "Depilação da virilha com cera.", "Bikini waxing.", 15, 10.00, 12.00),
        ("depilacao", "Virilha Completa", "Full Bikini", "Depilação completa da virilha com cera.", "Full bikini waxing.", 30, 13.00, 17.00),
        ("depilacao", "Axilas", "Underarms", "Depilação das axilas com cera.", "Underarm waxing.", 10, 5.00, 8.00),
        ("depilacao", "Buço e Queixo", "Upper Lip & Chin", "Depilação do buço e queixo.", "Upper lip and chin waxing.", 5, 2.50, 5.00),
        ("depilacao", "Braços", "Arms", "Depilação dos braços com cera.", "Arm waxing.", 15, 10.00, 15.00),
        ("depilacao", "Costas e Peito", "Back & Chest", "Depilação das costas e peito.", "Back and chest waxing.", 45, 20.00, 25.00),

        ("sobrancelhas", "Cera ou Threading + Tintura", "Waxing or Threading + Tint", "Design com cera ou linha e tintura.", "Waxing or threading design with tint.", 20, 15.00, 15.00),
        ("sobrancelhas", "Design de Sobrancelha SPA", "SPA Eyebrow Design", "Design de sobrancelha com tratamento SPA.", "Eyebrow design with SPA treatment.", 30, 20.00, 20.00),

        ("pestanas", "Extensões de Pestanas", "Eyelash Extensions", "Extensões de pestanas.", "Eyelash extensions.", 120, 35.00, 35.00),
        ("pestanas", "Volume Brasileiro", "Brazilian Volume", "Extensão de pestanas em volume brasileiro.", "Brazilian volume lash extensions.", 120, 40.00, 40.00),
        ("pestanas", "Lifting de Pestanas", "Lash Lift", "Lifting natural para pestanas.", "Natural lash lift.", 120, 35.00, 35.00),

        ("faciais", "Limpeza de Pele Desintoxicação", "Detox Facial Cleansing", "Limpeza facial desintoxicante.", "Detox facial cleansing.", 30, 35.00, 25.00),
        ("faciais", "Limpeza de Pele Premium com Tratamento Personalizado", "Premium Facial Cleansing with Personalised Treatment", "Limpeza facial premium com tratamento personalizado.", "Premium facial cleansing with personalised treatment.", 60, 60.00, 45.00),
        ("faciais", "Hydragloss + Cor", "Hydragloss + Color", "Tratamento hidratante para os lábios com cor.", "Hydrating lip treatment with color.", 30, 35.00, 40.00),

        ("massagem", "Massagem de Relaxamento 35 min", "Relaxing Massage 35 min", "Massagem de relaxamento.", "Relaxing massage.", 35, 35.00, 35.00),
        ("massagem", "Massagem de Relaxamento 60 min", "Relaxing Massage 60 min", "Massagem de relaxamento.", "Relaxing massage.", 60, 60.00, 60.00),
    ]

    services = []

    for categoria, nome_pt, nome_en, desc_pt, desc_en, duracao, preco_lagos, preco_luz in servicos_base:
        services.append(Service(
            name_pt=nome_pt,
            name_en=nome_en,
            description_pt=desc_pt,
            description_en=desc_en,
            duration_minutes=duracao,
            price=preco_lagos,
            category=cat_lagos[categoria]
        ))

        services.append(Service(
            name_pt=nome_pt,
            name_en=nome_en,
            description_pt=desc_pt,
            description_en=desc_en,
            duration_minutes=duracao,
            price=preco_luz,
            category=cat_luz[categoria]
        ))

    db.session.add_all(services)
    db.session.commit()