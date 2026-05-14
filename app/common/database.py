"""SQLAlchemy 基础配置：分页、自动时间、逻辑删除、依赖注入"""
from datetime import datetime, timezone
from typing import Generic, TypeVar

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

from app.common.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USERNAME
from app.common.response import PageResult


class Base(DeclarativeBase):
    """SQLAlchemy 基类，所有 ORM 模型直接继承此类即可

    包含所有公共字段：id（主键自增）、created_at、updated_at、deleted
    提供 find_all() 和 soft_delete()
    """

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    deleted: Mapped[int] = mapped_column(default=0)

    @classmethod
    def find_all(cls, session):
        """查询所有未删除记录（自动过滤 deleted=0）"""
        return session.query(cls).filter(cls.deleted == 0)

    def soft_delete(self) -> None:
        """逻辑删除：将 deleted 设为 1"""
        self.deleted = 1


# 数据库连接引擎（模块级单例）
_engine = create_engine(
    f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    pool_pre_ping=True,
)

# Session 工厂
SessionLocal = sessionmaker(bind=_engine)


def get_db() -> Session:
    """FastAPI 依赖注入：每个请求分配一个 session，请求结束时自动 close"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


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
