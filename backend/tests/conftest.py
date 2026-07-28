import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
    with TestingSession() as session:
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def machine_profile(db_session):
    from app.models.entities import MachineProfile, MachineType

    profile = MachineProfile(
        name="Fictional Test Mill",
        manufacturer="Example",
        model="VM-3",
        controller_name="Fanuc-style",
        machine_type=MachineType.MILL,
        axis_count=3,
        x_min=-20,
        x_max=20,
        y_min=-10,
        y_max=10,
        z_min=-5,
        z_max=15,
        max_spindle_rpm=10000,
        max_feed_rate=500,
        rapid_z_review_threshold=0,
        supported_work_offsets=["G54", "G55"],
        approved_g_codes=["G00", "G01", "G17", "G20", "G40", "G41", "G42", "G43", "G49", "G54", "G80", "G90"],
        approved_m_codes=["M03", "M05", "M06", "M08", "M09", "M30"],
        restricted_commands=["G91", "M00"],
        safe_start_template="G17 G20 G40 G49 G80 G90",
        program_end_template="M5 M9 G49 M30",
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile
