"""Test schema generation."""
from datetime import datetime, UTC

from sqlalchemy.schema import CreateTable
from sqlalchemy import text, select
import pytest

from basic_memory.models import Entity
from basic_memory.repository.entity_repository import EntityRepository


def test_entity_schema():
    """Test that SQLAlchemy generates correct schema."""
    create_sql = str(CreateTable(Entity.__table__))
    print("\nGenerated SQL:")
    print(create_sql)


@pytest.mark.anyio
async def test_actual_schema(session):
    """Check what schema actually exists in the test DB."""
    result = await session.execute(
        text("SELECT sql FROM sqlite_master WHERE type='table' AND name='entity'")
    )
    schema = result.scalar()
    print("\nActual Schema:")
    print(schema)

@pytest.mark.anyio
async def test_insert_entity(session):
    """Check what schema actually exists in the test DB."""

    id_value = "20240102-test"
    insert = await session.execute(
        text(f"INSERT INTO entity (id, name, entity_type, description) VALUES ('{id_value}', 'Test', 'test', 'Test description')")
    )
    assert insert is not None
    select_result = await session.execute(text("SELECT * FROM entity where id = '{id_value}'"))
    # assert created_at
    # assert updated_at

@pytest.mark.anyio
async def test_create_entity(entity_repository: EntityRepository):
    """Test creating a new entity"""
    entity_data = {
        'id': '20240102-test',
        'name': 'Test',
        'entity_type': 'test',
        'description': 'Test description',
    }
    entity = await entity_repository.create(entity_data)

    # Verify returned object
    assert entity.id == '20240102-test'
    assert entity.name == 'Test'
    assert entity.description == 'Test description'
    assert isinstance(entity.created_at, datetime)
    assert entity.created_at.tzinfo == UTC

    # Verify in database
    stmt = select(Entity).where(Entity.id == entity.id)
    result = await entity_repository.session.execute(stmt)
    db_entity = result.scalar_one()
    assert db_entity.id == entity.id
    assert db_entity.name == entity.name
    assert db_entity.description == entity.description
