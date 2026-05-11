"""SQLAlchemy 基础配置：分页、自动时间、逻辑删除"""
from datetime import datetime, timezone
from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Query

from app.common.response import PageResult


class Base(DeclarativeBase):
    """SQLAlchemy 基类，所有 ORM 模型继承此基类"""
    pass


class TimestampMixin:
    """自动填充时间戳的 Mixin：created_at 和 updated_at"""

    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class SoftDeleteMixin:
    """逻辑删除 Mixin：deleted=1 表示已删除，查询时自动过滤"""

    deleted: Mapped[int] = mapped_column(default=0)

    @classmethod
    def find_all(cls, session):
        """查询所有未删除记录（自动过滤 deleted=1）"""
        return session.query(cls).filter(cls.deleted == 0)

    def soft_delete(self) -> None:
        """逻辑删除：将 deleted 设为 1"""
        self.deleted = 1


def paginate(query, page: int, page_size: int) -> tuple[list, int]:
    """分页工具：返回 (当前页数据列表, 总条数)"""
    total = query.count()
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()
    return items, total


T = TypeVar("T")


def to_page_result(items: list[T], total: int, page: int, page_size: int) -> PageResult:
    """将分页结果转为 PageResult 统一响应格式"""
    return PageResult(
        list=items,
        total=total,
        page=page,
        page_size=page_size,
    )