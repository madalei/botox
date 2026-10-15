from sqlalchemy import String, JSON, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.adapters.database import Base

class Bot(Base):
    __tablename__ = "bots"

    id: Mapped[str] = mapped_column(primary_key=True)
    strategy: Mapped[str] = mapped_column(String, index=True)
    params: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String, index=True)
    # État de la position (achat en cours, prix d'achat, stop...) sauvegardé à chaque bougie,
    # pour la retrouver après un redémarrage du serveur. None = bot créé avant cette colonne.
    state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )