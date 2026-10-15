import os

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# URL de connexion à PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://botox_user:botoxine@localhost/botox")

# Création de l'engine SQLAlchemy
engine = create_engine(DATABASE_URL)

# Création de la session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base pour les modèles ORM
Base = declarative_base()

# Dépendance pour obtenir une session de DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def upgrade_schema(target_engine=None):
    """
    Ajoute les colonnes créées après la première mise en place de la base.
    Les scripts de migrations/ ne s'exécutent qu'au tout premier démarrage du conteneur Postgres (volume vide) :
    une base existante est mise à jour ici, à chaque démarrage. IF NOT EXISTS rend l'opération sans effet si c'est déjà fait.
    """
    with (target_engine or engine).begin() as connection:
        connection.execute(text("ALTER TABLE bots ADD COLUMN IF NOT EXISTS state JSONB"))
