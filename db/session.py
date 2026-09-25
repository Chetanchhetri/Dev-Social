from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from config.settings import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def seed_superadmin():
    from models.user import User, UserRole
    from utils.security import hash_password

    db = SessionLocal()
    try:
        superadmin = db.query(User).filter(User.role == UserRole.SUPERADMIN).first()
        hashed_pwd = hash_password(settings.SUPERADMIN_PASSWORD)

        if not superadmin:
            superadmin = User(
                full_name=settings.SUPERADMIN_NAME,
                email=settings.SUPERADMIN_EMAIL,
                hashed_password=hashed_pwd,
                role=UserRole.SUPERADMIN,
                is_verified=True
            )
            db.add(superadmin)
            print(f"Superadmin initialized: {settings.SUPERADMIN_EMAIL}")
        else:
            superadmin.email = settings.SUPERADMIN_EMAIL
            superadmin.hashed_password = hashed_pwd
            superadmin.is_verified = True
            print("Superadmin synchronized from .env")

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to seed superadmin: {str(e)}")
    finally:
        db.close()


def seed_test_user():
    """Seeds default user (ID 1) to ensure foreign key constraints and user locks pass during testing."""
    db = SessionLocal()
    try:
        user = db.execute(text("SELECT id FROM users WHERE id = 1")).fetchone()
        if not user:
            db.execute(text("""
                INSERT INTO users (id, full_name, email, hashed_password, role, is_verified) 
                VALUES (1, 'Test User', 'user@devsocial.local', 'dummyhash', 'USER', true)
                ON CONFLICT (id) DO NOTHING;
            """))
            db.commit()
            print("Default test user (ID 1) initialized.")
    except Exception as e:
        db.rollback()
        print(f"Failed to seed test user: {str(e)}")
    finally:
        db.close()


def init_db():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    seed_superadmin()
    seed_test_user()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()