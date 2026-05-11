"""Chat service implementation"""
from app.chat.interfaces import IConversationService, IMessageService
from app.provider.interfaces import IProviderService, IModelService
from app.mcp.interfaces import IMcpServerService, IMcpToolService
from app.knowledge.interfaces import IKnowledgeBaseService, IDocumentService, IDocumentChunkService
from app.agent.interfaces import IAgentService
from app.workflow.interfaces import IWorkflowService


class ConversationService(IConversationService):
    """Conversation service implementation"""
    pass


class MessageService(IMessageService):
    """Message service implementation"""
    pass