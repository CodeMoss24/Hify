"""Workflow module interfaces - define service contracts for Layer 3"""
from abc import ABC, abstractmethod
from typing import Optional
from sqlalchemy.orm import Session

from app.common.response import PageResult
from app.workflow.schemas import WorkflowCreate, WorkflowUpdate, WorkflowResponse


class IWorkflowService(ABC):
    """Workflow service interface - exposed to Layer 4 (chat) module"""

    @abstractmethod
    async def create_workflow(self, db: Session, body: WorkflowCreate) -> WorkflowResponse:
        pass

    @abstractmethod
    async def get_workflow(self, db: Session, workflow_id: int) -> Optional[WorkflowResponse]:
        pass

    @abstractmethod
    async def list_workflows(self, db: Session, page: int, page_size: int) -> PageResult[WorkflowResponse]:
        pass

    @abstractmethod
    async def update_workflow(self, db: Session, workflow_id: int, body: WorkflowUpdate) -> Optional[WorkflowResponse]:
        pass

    @abstractmethod
    async def delete_workflow(self, db: Session, workflow_id: int) -> None:
        pass
