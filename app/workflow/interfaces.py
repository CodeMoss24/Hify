"""Workflow module interfaces - define service contracts for Layer 3"""
from abc import ABC, abstractmethod
from typing import Optional, Any


class IWorkflowService(ABC):
    """Workflow service interface - exposed to Layer 4 (chat) module"""

    @abstractmethod
    async def create_workflow(self, data: "WorkflowCreate") -> "WorkflowResponse":
        pass

    @abstractmethod
    async def get_workflow(self, workflow_id: int) -> Optional["WorkflowResponse"]:
        pass

    @abstractmethod
    async def list_workflows(self, page: int, page_size: int) -> "PageResult[WorkflowResponse]":
        pass

    @abstractmethod
    async def update_workflow(self, workflow_id: int, data: "WorkflowUpdate") -> Optional["WorkflowResponse"]:
        pass

    @abstractmethod
    async def delete_workflow(self, workflow_id: int) -> bool:
        pass

    @abstractmethod
    async def execute_workflow(self, workflow_id: int, input_data: dict[str, Any]) -> dict[str, Any]:
        pass