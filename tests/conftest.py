"""Pytest fixtures for testing."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models import *  # noqa


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session."""
    # Use in-memory SQLite for testing
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    db = TestingSessionLocal()
    
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_company(db_session):
    """Create a sample company for testing."""
    from app.models.company import Company
    
    company = Company(
        name="Test Company",
        email="test@company.com",
        phone="555-0000",
        address="123 Test St"
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


@pytest.fixture
def sample_notification_settings(db_session, sample_company):
    """Create sample notification settings."""
    from app.models.notification import NotificationSettings
    
    settings = NotificationSettings(
        company_id=sample_company.id,
        enabled=True
    )
    db_session.add(settings)
    db_session.commit()
    db_session.refresh(settings)
    return settings


@pytest.fixture
def sample_recipient(db_session, sample_notification_settings):
    """Create a sample notification recipient."""
    from app.models.notification import NotificationRecipient
    
    recipient = NotificationRecipient(
        notification_setting_id=sample_notification_settings.id,
        email="test@example.com",
        name="Test User",
        is_active=True
    )
    db_session.add(recipient)
    db_session.commit()
    db_session.refresh(recipient)
    return recipient
