from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# URL de connexion à PostgreSQL
DATABASE_URL = "postgresql://botox_user:botoxine@localhost/botox"

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
