from datetime import datetime
from ..app import db


class ServiceCategory(db.Model):
    __tablename__ = "service_categories"
    id = db.Column(db.Integer, primary_key=True)
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
    category_id = db.Column(db.Integer, db.ForeignKey("service_categories.id"), nullable=False)
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
    if ServiceCategory.query.first():
        return

    categories = [
        ServiceCategory(name_pt="Pedicure",     name_en="Pedicure",   icon="sparkles", display_order=1),
        ServiceCategory(name_pt="Manicure",     name_en="Manicure",   icon="hand",     display_order=2),
        ServiceCategory(name_pt="Depilação",    name_en="Waxing",     icon="leaf",     display_order=3),
        ServiceCategory(name_pt="Sobrancelhas", name_en="Eyebrows",   icon="palette",  display_order=4),
        ServiceCategory(name_pt="Pestanas",     name_en="Eyelashes",  icon="scissors", display_order=5),
        ServiceCategory(name_pt="Faciais",      name_en="Facials",    icon="flower",   display_order=6),
    ]
    db.session.add_all(categories)
    db.session.flush()

    pedicure, manicure, depilacao, sobrancelhas, pestanas, faciais = categories

    services = [
        # ── Pedicure ──────────────────────────────────────────────────────
        Service(name_pt="Pedicure Normal", name_en="Regular Pedicure",
                description_pt="Pedicure clássica com cuidado completo dos pés.",
                description_en="Classic pedicure with complete foot care.",
                duration_minutes=30, price=25.00, category=pedicure),
        Service(name_pt="Pedicure SPA", name_en="SPA Pedicure",
                description_pt="Pedicure relaxante com tratamento SPA.",
                description_en="Relaxing pedicure with SPA treatment.",
                duration_minutes=40, price=40.00, category=pedicure),
        Service(name_pt="Verniz Gel / Shellac", name_en="Gel Polish / Shellac",
                description_pt="Verniz gel de longa duração com acabamento perfeito.",
                description_en="Long-lasting gel polish with a perfect finish.",
                duration_minutes=60, price=35.00, category=pedicure),
        Service(name_pt="Cortar + Pintar", name_en="Cut + Paint",
                description_pt="Corte e pintura das unhas dos pés.",
                description_en="Nail cut and polish for feet.",
                duration_minutes=15, price=12.50, category=pedicure),

        # ── Manicure ──────────────────────────────────────────────────────
        Service(name_pt="Manicure Normal", name_en="Regular Manicure",
                description_pt="Manicure clássica com cuidado completo das mãos.",
                description_en="Classic manicure with complete hand care.",
                duration_minutes=30, price=15.00, category=manicure),
        Service(name_pt="SPA das Mãos", name_en="Hand SPA",
                description_pt="Tratamento SPA hidratante para as mãos.",
                description_en="Moisturising SPA treatment for hands.",
                duration_minutes=30, price=25.00, category=manicure),
        Service(name_pt="Verniz Gel Shellac", name_en="Shellac Gel Polish",
                description_pt="Verniz gel shellac de longa duração.",
                description_en="Long-lasting shellac gel polish.",
                duration_minutes=60, price=25.00, category=manicure),
        Service(name_pt="Aplicação Gel", name_en="Gel Nail Application",
                description_pt="Aplicação de gel para unhas resistentes e elegantes.",
                description_en="Gel nail application for strong and elegant nails.",
                duration_minutes=90, price=45.00, category=manicure),
        Service(name_pt="Manutenção Gel", name_en="Gel Maintenance",
                description_pt="Manutenção e retoque das unhas em gel.",
                description_en="Maintenance and touch-up of gel nails.",
                duration_minutes=60, price=30.00, category=manicure),
        Service(name_pt="Gel Manicure Francesa", name_en="French Gel Manicure",
                description_pt="Manicure francesa em gel com acabamento clássico.",
                description_en="French gel manicure with a classic finish.",
                duration_minutes=120, price=35.00, category=manicure),
        Service(name_pt="Remover Gel", name_en="Gel Removal",
                description_pt="Remoção segura do gel com cuidado das unhas.",
                description_en="Safe gel removal with nail care.",
                duration_minutes=30, price=12.50, category=manicure),

        # ── Depilação / Waxing ────────────────────────────────────────────
        Service(name_pt="Meia Perna", name_en="Half Leg",
                description_pt="Depilação da meia perna com cera.",
                description_en="Half leg waxing.",
                duration_minutes=15, price=15.00, category=depilacao),
        Service(name_pt="Perna Inteira", name_en="Full Leg",
                description_pt="Depilação da perna inteira com cera.",
                description_en="Full leg waxing.",
                duration_minutes=30, price=22.00, category=depilacao),
        Service(name_pt="Perna + Virilha", name_en="Leg + Bikini",
                description_pt="Depilação da perna e virilha com cera.",
                description_en="Leg and bikini waxing.",
                duration_minutes=30, price=30.00, category=depilacao),
        Service(name_pt="Virilha", name_en="Bikini",
                description_pt="Depilação da virilha com cera.",
                description_en="Bikini waxing.",
                duration_minutes=15, price=12.00, category=depilacao),
        Service(name_pt="Virilha Completa", name_en="Full Bikini",
                description_pt="Depilação completa da virilha com cera.",
                description_en="Full bikini waxing.",
                duration_minutes=30, price=17.00, category=depilacao),
        Service(name_pt="Axilas", name_en="Underarms",
                description_pt="Depilação das axilas com cera.",
                description_en="Underarm waxing.",
                duration_minutes=10, price=8.00, category=depilacao),
        Service(name_pt="Buço e Queixo", name_en="Upper Lip & Chin",
                description_pt="Depilação do buço e queixo com cera.",
                description_en="Upper lip and chin waxing.",
                duration_minutes=5, price=5.00, category=depilacao),
        Service(name_pt="Braços", name_en="Arms",
                description_pt="Depilação dos braços com cera.",
                description_en="Arm waxing.",
                duration_minutes=15, price=15.00, category=depilacao),
        Service(name_pt="Costas e Peito", name_en="Back & Chest",
                description_pt="Depilação das costas e peito com cera.",
                description_en="Back and chest waxing.",
                duration_minutes=45, price=25.00, category=depilacao),

        # ── Sobrancelhas / Eyebrows ───────────────────────────────────────
        Service(name_pt="Design Sobrancelha + Tintura", name_en="Eyebrow Design + Tint",
                description_pt="Design personalizado com tintura para sobrancelhas perfeitas.",
                description_en="Personalised design with tint for perfect eyebrows.",
                duration_minutes=20, price=15.00, category=sobrancelhas),
        Service(name_pt="Design de Sobrancelha SPA", name_en="SPA Eyebrow Design",
                description_pt="Design de sobrancelha com tratamento SPA completo.",
                description_en="Eyebrow design with full SPA treatment.",
                duration_minutes=30, price=20.00, category=sobrancelhas),

        # ── Pestanas / Eyelashes ──────────────────────────────────────────
        Service(name_pt="Volume Brasileiro", name_en="Brazilian Volume",
                description_pt="Extensão de pestanas em volume brasileiro.",
                description_en="Brazilian volume lash extensions.",
                duration_minutes=120, price=40.00, category=pestanas),
        Service(name_pt="Volume Egípcio", name_en="Egyptian Volume",
                description_pt="Extensão de pestanas em volume egípcio.",
                description_en="Egyptian volume lash extensions.",
                duration_minutes=120, price=35.00, category=pestanas),
        Service(name_pt="Lifting de Pestana", name_en="Lash Lift",
                description_pt="Lifting natural para pestanas com efeito duradouro.",
                description_en="Natural lash lift with a long-lasting effect.",
                duration_minutes=120, price=35.00, category=pestanas),

        # ── Faciais / Facials ─────────────────────────────────────────────
        Service(name_pt="Limpeza de Pele", name_en="Facial Cleansing",
                description_pt="Limpeza facial para uma pele fresca e renovada.",
                description_en="Facial cleansing for fresh and renewed skin.",
                duration_minutes=30, price=25.00, category=faciais),
        Service(name_pt="Limpeza de Pele Profunda", name_en="Deep Facial Cleansing",
                description_pt="Limpeza profunda com extração e tratamento especializado.",
                description_en="Deep cleansing with extraction and specialist treatment.",
                duration_minutes=60, price=45.00, category=faciais),
        Service(name_pt="Hydragloss + Cor", name_en="Hydragloss + Color",
                description_pt="Tratamento hidratante para os lábios com efeito gloss e aplicação de cor, proporcionando hidratação profunda, brilho intenso e um aspeto saudável e natural.",
                description_en="Hydrating lip treatment with gloss effect and color application, providing deep hydration, intense shine, and a healthy, natural-looking finish.",
                duration_minutes=30, price=40.00, category=faciais),
    ]
    db.session.add_all(services)
    db.session.commit()
