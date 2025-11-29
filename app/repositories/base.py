"""
Base Repository following Repository Pattern and SOLID principles.

This provides a generic interface for data access operations,
following the Dependency Inversion Principle.
"""

from typing import Generic, TypeVar, Type, List, Optional, Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.base import BaseModel
from app.core.exceptions import NotFoundException, DatabaseException
from app.core.logging import get_logger

ModelType = TypeVar("ModelType", bound=BaseModel)

logger = get_logger(__name__)


class BaseRepository(Generic[ModelType]):
    """
    Base repository with common CRUD operations.

    Following SOLID principles:
    - Single Responsibility: Only handles data access
    - Open/Closed: Can be extended via inheritance
    - Liskov Substitution: All repositories can be used interchangeably
    - Interface Segregation: Minimal interface, extended as needed
    - Dependency Inversion: Depends on abstractions (Session interface)
    """

    def __init__(self, model: Type[ModelType], db: Session):
        """
        Initialize repository.

        Args:
            model: SQLAlchemy model class
            db: Database session (injected dependency)
        """
        self.model = model
        self.db = db

    def create(self, **kwargs) -> ModelType:
        """Create a new record."""
        try:
            instance = self.model(**kwargs)
            self.db.add(instance)
            self.db.flush()  # Flush instead of commit (let service handle transactions)
            self.db.refresh(instance)
            logger.info(f"Created {self.model.__name__} with id {instance.id}")
            return instance
        except Exception as e:
            logger.error(f"Error creating {self.model.__name__}: {str(e)}")
            raise DatabaseException(f"Error creating {self.model.__name__}", details=str(e))

    def get_by_id(self, id: int) -> Optional[ModelType]:
        """Get record by ID."""
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_by_id_or_fail(self, id: int) -> ModelType:
        """Get record by ID or raise exception."""
        instance = self.get_by_id(id)
        if not instance:
            raise NotFoundException(self.model.__name__, id)
        return instance

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[Any] = None
    ) -> List[ModelType]:
        """
        Get all records with optional filtering and pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records
            filters: Dictionary of filters {column: value}
            order_by: SQLAlchemy order_by clause
        """
        query = self.db.query(self.model)

        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)

        if order_by is not None:
            query = query.order_by(order_by)

        return query.offset(skip).limit(limit).all()

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records with optional filters."""
        query = self.db.query(func.count(self.model.id))

        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)

        return query.scalar()

    def update(self, instance: ModelType, **kwargs) -> ModelType:
        """Update a record."""
        try:
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)

            self.db.flush()
            self.db.refresh(instance)
            logger.info(f"Updated {self.model.__name__} with id {instance.id}")
            return instance
        except Exception as e:
            logger.error(f"Error updating {self.model.__name__}: {str(e)}")
            raise DatabaseException(f"Error updating {self.model.__name__}", details=str(e))

    def delete(self, instance: ModelType) -> None:
        """Delete a record."""
        try:
            self.db.delete(instance)
            self.db.flush()
            logger.info(f"Deleted {self.model.__name__} with id {instance.id}")
        except Exception as e:
            logger.error(f"Error deleting {self.model.__name__}: {str(e)}")
            raise DatabaseException(f"Error deleting {self.model.__name__}", details=str(e))

    def exists(self, **filters) -> bool:
        """Check if record exists with given filters."""
        query = self.db.query(self.model.id)
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        return query.first() is not None

    def bulk_create(self, objects: List[Dict[str, Any]]) -> List[ModelType]:
        """Bulk create records for better performance."""
        try:
            instances = [self.model(**obj) for obj in objects]
            self.db.bulk_save_objects(instances, return_defaults=True)
            self.db.flush()
            logger.info(f"Bulk created {len(instances)} {self.model.__name__} records")
            return instances
        except Exception as e:
            logger.error(f"Error bulk creating {self.model.__name__}: {str(e)}")
            raise DatabaseException(f"Error bulk creating {self.model.__name__}", details=str(e))
