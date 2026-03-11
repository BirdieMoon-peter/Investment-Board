from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlmodel import Field, SQLModel

from app.db.models.timestamps import utc_now


class NewsItem(SQLModel, table=True):
    __tablename__ = "news_items"
    __table_args__ = (
        Index(
            "ix_news_items_security_id_published_at_title",
            "security_id",
            "published_at",
            "title",
            unique=True,
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    security_id: int = Field(
        sa_column=Column(ForeignKey("securities.id"), nullable=False, index=True)
    )
    title: str = Field(sa_column=Column(String, nullable=False))
    source: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    url: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    summary: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    published_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True)
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
