from datetime import datetime
from ..app import db


class Salon(db.Model):
    __tablename__ = "salons"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    
    address = db.Column(db.String(255))
    phone = db.Column(db.String(30))
    email = db.Column(db.String(150))
    opening_hours_pt = db.Column(db.String(100))
    opening_hours_en = db.Column(db.String(100))

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
    client_email = db.Column(db.String(150), nullable=True)
    client_phone = db.Column(db.String(30), nullable=False)

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

    lagos = Salon(
        name="Lagos",
        slug="lagos",
        address="R. José Ventura Neto Cabrita, Lote 1 Loja A, 8600-774 Lagos",
        phone="+351 910 668 153",
        email="dany_alves.7@hotmail.com",
        opening_hours_pt="Seg–Sex: 10h – 18h",
        opening_hours_en="Mon–Fri: 10am – 6pm",
    )

    luz = Salon(
        name="Praia da Luz",
        slug="praia-da-luz",
        address="Urb. St. James Lt 4 Fração U, Montes da Luz, 8600-174 Luz",
        phone="+351 910 668 153",
        email="dany_alves.7@hotmail.com",
        opening_hours_pt="Seg–Sex: 10h – 18h",
        opening_hours_en="Mon–Fri: 10am – 6pm",
    )   

    db.session.add_all([lagos, luz])
    db.session.flush()

    def criar_categorias(salon, incluir_massagem=False):
        categorias = {
            "pedicure": ServiceCategory(
                name_pt="Pedicure",
                name_en="Pedicure",
                icon="sparkles",
                display_order=1,
                salon=salon,
            ),
            "manicure": ServiceCategory(
                name_pt="Manicure",
                name_en="Manicure",
                icon="hand",
                display_order=2,
                salon=salon,
            ),
            "depilacao": ServiceCategory(
                name_pt="Depilação",
                name_en="Waxing",
                icon="leaf",
                display_order=3,
                salon=salon,
            ),
            "sobrancelhas": ServiceCategory(
                name_pt="Sobrancelhas",
                name_en="Eyebrows",
                icon="palette",
                display_order=4,
                salon=salon,
            ),
            "pestanas": ServiceCategory(
                name_pt="Pestanas",
                name_en="Eyelashes",
                icon="scissors",
                display_order=5,
                salon=salon,
            ),
            "faciais": ServiceCategory(
                name_pt="Faciais",
                name_en="Facials",
                icon="flower",
                display_order=6,
                salon=salon,
            ),
        }

        if incluir_massagem:
            categorias["massagem"] = ServiceCategory(
                name_pt="Massagem",
                name_en="Massage",
                icon="flower",
                display_order=7,
                salon=salon,
            )

        db.session.add_all(categorias.values())
        db.session.flush()

        return categorias

    cat_lagos = criar_categorias(lagos, incluir_massagem=True)
    cat_luz = criar_categorias(luz)

    # =========================================================
    # LAGOS — nomes e preços novos
    # =========================================================

    servicos_lagos = [
        # Pedicure
        (
            "pedicure",
            "Pedicure Completa",
            "Complete Pedicure",
            "Pedicure completa com cuidado dos pés.",
            "Complete pedicure with foot care.",
            30,
            25.00,
        ),
        (
            "pedicure",
            "SPA Pedicure",
            "SPA Pedicure",
            "Pedicure relaxante com tratamento SPA.",
            "Relaxing pedicure with SPA treatment.",
            40,
            30.00,
        ),
        (
            "pedicure",
            "Verniz de Gel",
            "Gel Polish",
            "Verniz gel de longa duração.",
            "Long-lasting gel polish.",
            60,
            28.00,
        ),
        (
            "pedicure",
            "Cortar + Pintar",
            "Cut + Paint",
            "Corte e pintura das unhas dos pés.",
            "Nail cut and polish for feet.",
            15,
            10.00,
        ),

        # Manicure
        (
            "manicure",
            "Manicure Normal",
            "Regular Manicure",
            "Manicure clássica com cuidado completo das mãos.",
            "Classic manicure with complete hand care.",
            30,
            15.00,
        ),
        (
            "manicure",
            "SPA das Mãos",
            "Hand SPA",
            "Tratamento SPA hidratante para as mãos.",
            "Moisturising SPA treatment for hands.",
            30,
            20.00,
        ),
        (
            "manicure",
            "Verniz de Gel",
            "Gel Polish",
            "Verniz gel de longa duração.",
            "Long-lasting gel polish.",
            60,
            18.00,
        ),
        (
            "manicure",
            "Extensões",
            "Extensions",
            "Extensões de unhas em gel.",
            "Gel nail extensions.",
            90,
            35.00,
        ),
        (
            "manicure",
            "Manutenção",
            "Maintenance",
            "Manutenção e retoque das unhas em gel.",
            "Maintenance and touch-up of gel nails.",
            60,
            25.00,
        ),
        (
            "manicure",
            "Manicure Francesa",
            "French Manicure",
            "Manicure francesa com acabamento clássico.",
            "French manicure with a classic finish.",
            120,
            30.00,
        ),
        (
            "manicure",
            "Remover Gel",
            "Gel Removal",
            "Remoção segura do gel com cuidado das unhas.",
            "Safe gel removal with nail care.",
            30,
            10.00,
        ),

        # Depilação
        (
            "depilacao",
            "Meia Perna",
            "Half Leg",
            "Depilação da meia perna com cera.",
            "Half leg waxing.",
            15,
            10.00,
        ),
        (
            "depilacao",
            "Perna Inteira",
            "Full Leg",
            "Depilação da perna inteira com cera.",
            "Full leg waxing.",
            30,
            17.00,
        ),
        (
            "depilacao",
            "Perna + Virilha",
            "Leg + Bikini",
            "Depilação da perna e virilha com cera.",
            "Leg and bikini waxing.",
            30,
            25.00,
        ),
        (
            "depilacao",
            "Virilha",
            "Bikini",
            "Depilação da virilha com cera.",
            "Bikini waxing.",
            15,
            10.00,
        ),
        (
            "depilacao",
            "Virilha Completa",
            "Full Bikini",
            "Depilação completa da virilha com cera.",
            "Full bikini waxing.",
            30,
            15.00,
        ),
        (
            "depilacao",
            "Axilas",
            "Underarms",
            "Depilação das axilas com cera.",
            "Underarm waxing.",
            10,
            5.00,
        ),
        (
            "depilacao",
            "Buço ou Queixo",
            "Upper Lip or Chin",
            "Depilação do buço ou queixo com cera.",
            "Upper lip or chin waxing.",
            5,
            3.50,
        ),
        (
            "depilacao",
            "Sobrancelha",
            "Eyebrow",
            "Depilação da sobrancelha com cera.",
            "Eyebrow waxing.",
            10,
            6.00,
        ),
        (
            "depilacao",
            "Braços",
            "Arms",
            "Depilação dos braços com cera.",
            "Arm waxing.",
            15,
            10.00,
        ),
        (
            "depilacao",
            "Costas e Peito",
            "Back & Chest",
            "Depilação das costas e peito com cera.",
            "Back and chest waxing.",
            45,
            20.00,
        ),

        # Sobrancelhas
        (
            "sobrancelhas",
            "Cera ou Threading + Tintura",
            "Waxing or Threading + Tint",
            "Design com cera ou linha e aplicação de tintura.",
            "Waxing or threading design with tint application.",
            20,
            15.00,
        ),
        (
            "sobrancelhas",
            "Design de Sobrancelha SPA",
            "SPA Eyebrow Design",
            "Design de sobrancelha com tratamento SPA completo.",
            "Eyebrow design with full SPA treatment.",
            30,
            20.00,
        ),

        # Pestanas
        (
            "pestanas",
            "Extensões de Pestanas",
            "Eyelash Extensions",
            "Aplicação de extensões de pestanas.",
            "Eyelash extension application.",
            120,
            35.00,
        ),
        (
            "pestanas",
            "Volume Brasileiro",
            "Brazilian Volume",
            "Extensão de pestanas em volume brasileiro.",
            "Brazilian volume lash extensions.",
            120,
            40.00,
        ),
        (
            "pestanas",
            "Lifting de Pestanas",
            "Lash Lift",
            "Lifting natural para pestanas com efeito duradouro.",
            "Natural lash lift with a long-lasting effect.",
            120,
            35.00,
        ),

        # Faciais
        (
            "faciais",
            "Limpeza de Pele Desintoxicação",
            "Detox Facial Cleansing",
            "Limpeza facial desintoxicante.",
            "Detox facial cleansing.",
            30,
            35.00,
        ),
        (
            "faciais",
            "Limpeza de Pele Premium com Tratamento Personalizado",
            "Premium Facial Cleansing with Personalised Treatment",
            "Limpeza facial premium com tratamento personalizado.",
            "Premium facial cleansing with personalised treatment.",
            60,
            60.00,
        ),
        (
            "faciais",
            "Hydragloss + Cor",
            "Hydragloss + Color",
            "Tratamento hidratante para os lábios com efeito gloss e cor.",
            "Hydrating lip treatment with gloss effect and color.",
            30,
            35.00,
        ),

        # Massagem
        (
            "massagem",
            "Massagem de Relaxamento 35 min",
            "Relaxing Massage 35 min",
            "Massagem de relaxamento com duração de 35 minutos.",
            "Relaxing massage lasting 35 minutes.",
            35,
            35.00,
        ),
        (
            "massagem",
            "Massagem de Relaxamento 60 min",
            "Relaxing Massage 60 min",
            "Massagem de relaxamento com duração de 60 minutos.",
            "Relaxing massage lasting 60 minutes.",
            60,
            60.00,
        ),
    ]

    # =========================================================
    # PRAIA DA LUZ — nomes, serviços e preços antigos
    # =========================================================

    servicos_luz = [
        # Pedicure
        (
            "pedicure",
            "Pedicure Normal",
            "Regular Pedicure",
            "Pedicure clássica com cuidado completo dos pés.",
            "Classic pedicure with complete foot care.",
            30,
            25.00,
        ),
        (
            "pedicure",
            "Pedicure SPA",
            "SPA Pedicure",
            "Pedicure relaxante com tratamento SPA.",
            "Relaxing pedicure with SPA treatment.",
            40,
            40.00,
        ),
        (
            "pedicure",
            "Verniz Gel / Shellac",
            "Gel Polish / Shellac",
            "Verniz gel de longa duração com acabamento perfeito.",
            "Long-lasting gel polish with a perfect finish.",
            60,
            35.00,
        ),
        (
            "pedicure",
            "Cortar + Pintar",
            "Cut + Paint",
            "Corte e pintura das unhas dos pés.",
            "Nail cut and polish for feet.",
            15,
            12.50,
        ),

        # Manicure
        (
            "manicure",
            "Manicure Normal",
            "Regular Manicure",
            "Manicure clássica com cuidado completo das mãos.",
            "Classic manicure with complete hand care.",
            30,
            15.00,
        ),
        (
            "manicure",
            "SPA das Mãos",
            "Hand SPA",
            "Tratamento SPA hidratante para as mãos.",
            "Moisturising SPA treatment for hands.",
            30,
            25.00,
        ),
        (
            "manicure",
            "Verniz Gel Shellac",
            "Shellac Gel Polish",
            "Verniz gel shellac de longa duração.",
            "Long-lasting shellac gel polish.",
            60,
            25.00,
        ),
        (
            "manicure",
            "Aplicação Gel",
            "Gel Nail Application",
            "Aplicação de gel para unhas resistentes e elegantes.",
            "Gel nail application for strong and elegant nails.",
            90,
            45.00,
        ),
        (
            "manicure",
            "Manutenção Gel",
            "Gel Maintenance",
            "Manutenção e retoque das unhas em gel.",
            "Maintenance and touch-up of gel nails.",
            60,
            30.00,
        ),
        (
            "manicure",
            "Gel Manicure Francesa",
            "French Gel Manicure",
            "Manicure francesa em gel com acabamento clássico.",
            "French gel manicure with a classic finish.",
            120,
            35.00,
        ),
        (
            "manicure",
            "Remover Gel",
            "Gel Removal",
            "Remoção segura do gel com cuidado das unhas.",
            "Safe gel removal with nail care.",
            30,
            12.50,
        ),

        # Depilação
        (
            "depilacao",
            "Meia Perna",
            "Half Leg",
            "Depilação da meia perna com cera.",
            "Half leg waxing.",
            15,
            15.00,
        ),
        (
            "depilacao",
            "Perna Inteira",
            "Full Leg",
            "Depilação da perna inteira com cera.",
            "Full leg waxing.",
            30,
            22.00,
        ),
        (
            "depilacao",
            "Perna + Virilha",
            "Leg + Bikini",
            "Depilação da perna e virilha com cera.",
            "Leg and bikini waxing.",
            30,
            30.00,
        ),
        (
            "depilacao",
            "Virilha",
            "Bikini",
            "Depilação da virilha com cera.",
            "Bikini waxing.",
            15,
            12.00,
        ),
        (
            "depilacao",
            "Virilha Completa",
            "Full Bikini",
            "Depilação completa da virilha com cera.",
            "Full bikini waxing.",
            30,
            17.00,
        ),
        (
            "depilacao",
            "Axilas",
            "Underarms",
            "Depilação das axilas com cera.",
            "Underarm waxing.",
            10,
            8.00,
        ),
        (
            "depilacao",
            "Buço e Queixo",
            "Upper Lip & Chin",
            "Depilação do buço e queixo com cera.",
            "Upper lip and chin waxing.",
            5,
            5.00,
        ),
        (
            "depilacao",
            "Sobrancelha",
            "Eyebrow",
            "Depilação da sobrancelha com cera.",
            "Eyebrow waxing.",
            10,
            6.00,
        ),
        (
            "depilacao",
            "Braços",
            "Arms",
            "Depilação dos braços com cera.",
            "Arm waxing.",
            15,
            15.00,
        ),
        (
            "depilacao",
            "Costas e Peito",
            "Back & Chest",
            "Depilação das costas e peito com cera.",
            "Back and chest waxing.",
            45,
            25.00,
        ),

        # Sobrancelhas
        (
            "sobrancelhas",
            "Design Sobrancelha + Tintura",
            "Eyebrow Design + Tint",
            "Design personalizado com tintura para sobrancelhas perfeitas.",
            "Personalised design with tint for perfect eyebrows.",
            20,
            15.00,
        ),
        (
            "sobrancelhas",
            "Design de Sobrancelha SPA",
            "SPA Eyebrow Design",
            "Design de sobrancelha com tratamento SPA completo.",
            "Eyebrow design with full SPA treatment.",
            30,
            20.00,
        ),

        # Pestanas
        (
            "pestanas",
            "Volume Brasileiro",
            "Brazilian Volume",
            "Extensão de pestanas em volume brasileiro.",
            "Brazilian volume lash extensions.",
            120,
            40.00,
        ),
        (
            "pestanas",
            "Volume Egípcio",
            "Egyptian Volume",
            "Extensão de pestanas em volume egípcio.",
            "Egyptian volume lash extensions.",
            120,
            35.00,
        ),
        (
            "pestanas",
            "Lifting de Pestana",
            "Lash Lift",
            "Lifting natural para pestanas com efeito duradouro.",
            "Natural lash lift with a long-lasting effect.",
            120,
            35.00,
        ),

        # Faciais
        (
            "faciais",
            "Limpeza de Pele",
            "Facial Cleansing",
            "Limpeza facial para uma pele fresca e renovada.",
            "Facial cleansing for fresh and renewed skin.",
            30,
            25.00,
        ),
        (
            "faciais",
            "Limpeza de Pele Profunda",
            "Deep Facial Cleansing",
            "Limpeza profunda com extração e tratamento especializado.",
            "Deep cleansing with extraction and specialist treatment.",
            60,
            45.00,
        ),
        (
            "faciais",
            "Hydragloss + Cor",
            "Hydragloss + Color",
            "Tratamento hidratante para os lábios com efeito gloss e aplicação de cor, proporcionando hidratação profunda, brilho intenso e um aspeto saudável e natural.",
            "Hydrating lip treatment with gloss effect and color application, providing deep hydration, intense shine, and a healthy, natural-looking finish.",
            30,
            40.00,
        ),
    ]

    services = []

    for (
        categoria,
        nome_pt,
        nome_en,
        desc_pt,
        desc_en,
        duracao,
        preco,
    ) in servicos_lagos:
        services.append(
            Service(
                name_pt=nome_pt,
                name_en=nome_en,
                description_pt=desc_pt,
                description_en=desc_en,
                duration_minutes=duracao,
                price=preco,
                category=cat_lagos[categoria],
            )
        )

    for (
        categoria,
        nome_pt,
        nome_en,
        desc_pt,
        desc_en,
        duracao,
        preco,
    ) in servicos_luz:
        services.append(
            Service(
                name_pt=nome_pt,
                name_en=nome_en,
                description_pt=desc_pt,
                description_en=desc_en,
                duration_minutes=duracao,
                price=preco,
                category=cat_luz[categoria],
            )
        )

    db.session.add_all(services)
    db.session.commit()