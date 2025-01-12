from datetime import datetime, timedelta
import pytest

from basic_memory.schemas.activity import (
    TimeFrame,
    ActivityType,
    ChangeType,
    ActivityChange,
    ActivitySummary,
    RecentActivity,
)


def test_timeframe_parsing():
    """Test TimeFrame string parsing."""
    # Valid timeframes
    assert TimeFrame("1h").value == 1
    assert TimeFrame("1h").unit == "h"
    assert TimeFrame("24h").value == 24
    assert TimeFrame("7d").unit == "d"
    assert TimeFrame("4w").unit == "w"
    assert TimeFrame("2m").unit == "m"

    # Invalid timeframes
    with pytest.raises(ValueError):
        TimeFrame("")
    with pytest.raises(ValueError):
        TimeFrame("h")
    with pytest.raises(ValueError):
        TimeFrame("abc")
    with pytest.raises(ValueError):
        TimeFrame("1x")  # Invalid unit
    with pytest.raises(ValueError):
        TimeFrame("-1h")  # Negative value


def test_timeframe_to_timedelta():
    """Test conversion to timedelta."""
    assert TimeFrame("1h").to_timedelta == timedelta(hours=1)
    assert TimeFrame("24h").to_timedelta == timedelta(hours=24)
    assert TimeFrame("1d").to_timedelta == timedelta(days=1)
    assert TimeFrame("1w").to_timedelta == timedelta(weeks=1)
    assert TimeFrame("1m").to_timedelta == timedelta(days=30)  # Approximate


def test_activity_change_model():
    """Test ActivityChange model."""
    now = datetime.utcnow()
    change = ActivityChange(
        activity_type=ActivityType.ENTITY,
        change_type=ChangeType.CREATED,
        timestamp=now,
        permalink="test/path",
        summary="Created test document",
        content="Test content",
    )

    assert change.activity_type == ActivityType.ENTITY
    assert change.change_type == ChangeType.CREATED
    assert change.timestamp == now
    assert change.permalink == "test/path"
    assert change.summary == "Created test document"
    assert change.content == "Test content"


def test_activity_summary_model():
    """Test ActivitySummary model."""
    summary = ActivitySummary(
        entity_changes=3, relation_changes=2, most_active_paths=["path1", "path2"]
    )

    assert summary.entity_changes == 3
    assert summary.relation_changes == 2
    assert summary.most_active_paths == ["path1", "path2"]


def test_recent_activity_model():
    """Test RecentActivity model."""
    now = datetime.utcnow()
    change = ActivityChange(
        activity_type=ActivityType.ENTITY,
        change_type=ChangeType.CREATED,
        timestamp=now,
        permalink="test/path",
        summary="Created test document",
    )

    summary = ActivitySummary(entity_changes=1)

    activity = RecentActivity(timeframe="1d", changes=[change], summary=summary)

    assert activity.timeframe == "1d"
    assert len(activity.changes) == 1
    assert activity.changes[0].permalink == "test/path"
    assert activity.summary.entity_changes == 1
