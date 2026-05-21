-- Hify 数据库建表脚本
-- 字符集: utf8mb4
-- 存储引擎: InnoDB
-- 一期手动建表使用，生产环境迁移到 Alembic

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- =============================================
-- 1. tb_model_provider - 模型提供商表
-- =============================================
DROP TABLE IF EXISTS `tb_model_provider`;
CREATE TABLE `tb_model_provider` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(64) NOT NULL COMMENT 'Provider 展示名称',
  `provider_type` VARCHAR(32) NOT NULL COMMENT 'openai/anthropic/openai_compatible/ollama',
  `base_url` VARCHAR(256) NOT NULL COMMENT 'API Base URL',
  `api_key` VARCHAR(512) NOT NULL DEFAULT '' COMMENT 'API Key',
  `extra_config` JSON DEFAULT NULL COMMENT '差异配置(anthropic_version, custom_headers等)',
  `status` VARCHAR(16) NOT NULL DEFAULT 'enabled' COMMENT 'enabled/disabled 用户控制',
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `deleted` TINYINT(1) NOT NULL DEFAULT 0,
  INDEX `idx_tb_model_provider_deleted` (`deleted`),
  UNIQUE INDEX `idx_tb_model_provider_name` (`name`, `deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型提供商表';

-- =============================================
-- 2. tb_model - 模型表
-- =============================================
DROP TABLE IF EXISTS `tb_model`;
CREATE TABLE `tb_model` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `provider_id` BIGINT NOT NULL COMMENT '关联 provider id',
  `name` VARCHAR(64) NOT NULL COMMENT '展示名称',
  `model_id` VARCHAR(128) NOT NULL COMMENT 'API 调用标识(如 gpt-4o)',
  `status` VARCHAR(16) NOT NULL DEFAULT 'enabled' COMMENT 'enabled/disabled',
  `capabilities` VARCHAR(256) NOT NULL DEFAULT '' COMMENT '能力标签(逗号分隔: streaming,tool_use,thinking)',
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `deleted` TINYINT(1) NOT NULL DEFAULT 0,
  INDEX `idx_tb_model_deleted` (`deleted`),
  INDEX `idx_tb_model_provider_id` (`provider_id`, `deleted`),
  UNIQUE INDEX `idx_tb_model_provider_model` (`provider_id`, `model_id`, `deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型表';

-- =============================================
-- 3. tb_provider_health_log - Provider 健康状态变更日志
-- =============================================
DROP TABLE IF EXISTS `tb_provider_health_log`;
CREATE TABLE `tb_provider_health_log` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `provider_id` BIGINT NOT NULL COMMENT 'Provider id',
  `prev_status` VARCHAR(16) NOT NULL COMMENT '变更前状态',
  `curr_status` VARCHAR(16) NOT NULL COMMENT '变更后状态',
  `error_message` VARCHAR(512) NOT NULL DEFAULT '' COMMENT '错误信息',
  `response_time_ms` INT NOT NULL DEFAULT 0 COMMENT '响应时间(ms)',
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  INDEX `idx_tb_provider_health_log_provider` (`provider_id`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Provider 健康状态变更日志';

-- =============================================
-- 4. tb_agent - Agent 表
-- =============================================
DROP TABLE IF EXISTS `tb_agent`;
CREATE TABLE `tb_agent` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(64) NOT NULL COMMENT 'Agent 名称',
  `description` VARCHAR(500) NOT NULL DEFAULT '' COMMENT '描述',
  `model_id` BIGINT NOT NULL COMMENT '关联模型 id',
  `workflow_id` BIGINT DEFAULT NULL COMMENT '绑定的工作流 id',
  `system_prompt` TEXT NOT NULL DEFAULT '' COMMENT '系统提示词',
  `temperature` DECIMAL(3,2) NOT NULL DEFAULT 0.70 COMMENT '温度参数 0.00~1.00',
  `max_tokens` INT NOT NULL DEFAULT 2048 COMMENT '最大生成 Token 数',
  `max_context_turns` INT NOT NULL DEFAULT 10 COMMENT '保留最近对话轮数',
  `enabled` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '0=禁用 1=启用',
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `deleted` TINYINT(1) NOT NULL DEFAULT 0,
  INDEX `idx_tb_agent_deleted` (`deleted`),
  INDEX `idx_tb_agent_model_id` (`model_id`, `deleted`),
  INDEX `idx_tb_agent_workflow_id` (`workflow_id`, `deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Agent 表';

-- =============================================
-- 5. tb_agent_knowledge_base - Agent 与知识库关联表
-- =============================================
DROP TABLE IF EXISTS `tb_agent_knowledge_base`;
CREATE TABLE `tb_agent_knowledge_base` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `agent_id` BIGINT NOT NULL COMMENT 'Agent id',
  `knowledge_base_id` BIGINT NOT NULL COMMENT '知识库 id',
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `deleted` TINYINT(1) NOT NULL DEFAULT 0,
  INDEX `idx_tb_agent_kb_deleted` (`deleted`),
  INDEX `idx_tb_agent_kb_agent_id` (`agent_id`, `deleted`),
  INDEX `idx_tb_agent_kb_kb_id` (`knowledge_base_id`, `deleted`),
  UNIQUE INDEX `idx_tb_agent_kb_unique` (`agent_id`, `knowledge_base_id`, `deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Agent 与知识库关联表';

-- =============================================
-- 6. tb_agent_tool - Agent 与 MCP 工具关联表
-- =============================================
DROP TABLE IF EXISTS `tb_agent_tool`;
CREATE TABLE `tb_agent_tool` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `agent_id` BIGINT NOT NULL COMMENT 'Agent id',
  `mcp_tool_id` BIGINT NOT NULL COMMENT 'MCP 工具 id',
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `deleted` TINYINT(1) NOT NULL DEFAULT 0,
  INDEX `idx_tb_agent_tool_deleted` (`deleted`),
  INDEX `idx_tb_agent_tool_agent_id` (`agent_id`, `deleted`),
  INDEX `idx_tb_agent_tool_mcp_id` (`mcp_tool_id`, `deleted`),
  UNIQUE INDEX `idx_tb_agent_tool_unique` (`agent_id`, `mcp_tool_id`, `deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Agent 与 MCP 工具关联表';

-- =============================================
-- 7. tb_mcp_server - MCP 服务器表
-- =============================================
DROP TABLE IF EXISTS `tb_mcp_server`;
CREATE TABLE `tb_mcp_server` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(64) NOT NULL COMMENT '服务器名称',
  `url` VARCHAR(256) NOT NULL COMMENT '服务器 URL',
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `deleted` TINYINT(1) NOT NULL DEFAULT 0,
  INDEX `idx_tb_mcp_server_deleted` (`deleted`),
  UNIQUE INDEX `idx_tb_mcp_server_name` (`name`, `deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='MCP 服务器表';

-- =============================================
-- 8. tb_mcp_tool - MCP 工具表
-- =============================================
DROP TABLE IF EXISTS `tb_mcp_tool`;
CREATE TABLE `tb_mcp_tool` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `server_id` BIGINT NOT NULL COMMENT '服务器 id',
  `name` VARCHAR(64) NOT NULL COMMENT '工具名称',
  `description` VARCHAR(256) DEFAULT '' COMMENT '工具描述',
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `deleted` TINYINT(1) NOT NULL DEFAULT 0,
  INDEX `idx_tb_mcp_tool_deleted` (`deleted`),
  INDEX `idx_tb_mcp_tool_server_id` (`server_id`, `deleted`),
  UNIQUE INDEX `idx_tb_mcp_tool_server_name` (`server_id`, `name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='MCP 工具表';

-- =============================================
-- 9. tb_knowledge_base - 知识库表
-- =============================================
DROP TABLE IF EXISTS `tb_knowledge_base`;
CREATE TABLE `tb_knowledge_base` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(64) NOT NULL COMMENT '知识库名称',
  `description` VARCHAR(256) DEFAULT '' COMMENT '知识库描述',
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `deleted` TINYINT(1) NOT NULL DEFAULT 0,
  INDEX `idx_tb_knowledge_base_deleted` (`deleted`),
  UNIQUE INDEX `idx_tb_knowledge_base_name` (`name`, `deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识库表';

-- =============================================
-- 10. tb_document - 文档表
-- =============================================
DROP TABLE IF EXISTS `tb_document`;
CREATE TABLE `tb_document` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `knowledge_base_id` BIGINT NOT NULL COMMENT '知识库 id',
  `name` VARCHAR(128) NOT NULL COMMENT '文档名称',
  `size` BIGINT NOT NULL DEFAULT 0 COMMENT '文件大小字节',
  `status` VARCHAR(32) NOT NULL DEFAULT 'pending' COMMENT '状态: pending/processing/done/failed',
  `error_message` VARCHAR(512) NOT NULL DEFAULT '' COMMENT '处理失败时的错误信息',
  `chunk_count` INT NOT NULL DEFAULT 0 COMMENT '分块数量',
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `deleted` TINYINT(1) NOT NULL DEFAULT 0,
  INDEX `idx_tb_document_deleted` (`deleted`),
  INDEX `idx_tb_document_kb_id` (`knowledge_base_id`, `deleted`),
  INDEX `idx_tb_document_status` (`status`, `deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文档表';

-- =============================================
-- 11. tb_document_chunk - 文档分块表
-- =============================================
DROP TABLE IF EXISTS `tb_document_chunk`;
CREATE TABLE `tb_document_chunk` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `document_id` BIGINT NOT NULL COMMENT '文档 id',
  `content` TEXT NOT NULL COMMENT '文本内容',
  `chunk_index` INT NOT NULL DEFAULT 0 COMMENT '分块序号',
  `vector_id` VARCHAR(64) DEFAULT '' COMMENT 'Qdrant 向量 id',
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `deleted` TINYINT(1) NOT NULL DEFAULT 0,
  INDEX `idx_tb_doc_chunk_deleted` (`deleted`),
  INDEX `idx_tb_doc_chunk_doc_id` (`document_id`, `deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文档分块表';

-- =============================================
-- 12. tb_conversation - 会话表
-- =============================================
DROP TABLE IF EXISTS `tb_conversation`;
CREATE TABLE `tb_conversation` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `agent_id` BIGINT NOT NULL COMMENT 'Agent id',
  `title` VARCHAR(128) NOT NULL DEFAULT '新对话' COMMENT '会话标题',
  `status` VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' COMMENT 'ACTIVE/ARCHIVED',
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `deleted` TINYINT(1) NOT NULL DEFAULT 0,
  INDEX `idx_tb_conversation_deleted` (`deleted`),
  INDEX `idx_tb_conversation_agent_id` (`agent_id`, `deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='会话表';

-- =============================================
-- 13. tb_message - 消息表
-- =============================================
DROP TABLE IF EXISTS `tb_message`;
CREATE TABLE `tb_message` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `conversation_id` BIGINT NOT NULL COMMENT '会话 id',
  `role` VARCHAR(16) NOT NULL COMMENT 'user/assistant/system',
  `content` LONGTEXT NOT NULL COMMENT '消息内容',
  `finish_reason` VARCHAR(20) NOT NULL DEFAULT '' COMMENT 'stop/length/error',
  `latency_ms` INT NOT NULL DEFAULT 0 COMMENT '响应耗时ms',
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `deleted` TINYINT(1) NOT NULL DEFAULT 0,
  INDEX `idx_tb_message_deleted` (`deleted`),
  INDEX `idx_tb_message_conv_id` (`conversation_id`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='消息表';

-- =============================================
-- 14. tb_message_reference - 消息引用表（RAG 引用）
-- =============================================
DROP TABLE IF EXISTS `tb_message_reference`;
CREATE TABLE `tb_message_reference` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `message_id` BIGINT NOT NULL COMMENT '消息 id',
  `document_chunk_id` BIGINT NOT NULL COMMENT '文档分块 id',
  `score` DECIMAL(5,4) DEFAULT 0 COMMENT '相似度得分',
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `deleted` TINYINT(1) NOT NULL DEFAULT 0,
  INDEX `idx_tb_msg_ref_deleted` (`deleted`),
  INDEX `idx_tb_msg_ref_msg_id` (`message_id`, `deleted`),
  INDEX `idx_tb_msg_ref_chunk_id` (`document_chunk_id`, `deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='消息引用表';

-- =============================================
-- 15. tb_workflow - 工作流表
-- =============================================
DROP TABLE IF EXISTS `tb_workflow`;
CREATE TABLE `tb_workflow` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(64) NOT NULL COMMENT '工作流名称',
  `description` VARCHAR(256) NOT NULL DEFAULT '' COMMENT '描述',
  `status` VARCHAR(20) NOT NULL DEFAULT 'DRAFT' COMMENT '状态: DRAFT/ACTIVE',
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `deleted` TINYINT(1) NOT NULL DEFAULT 0,
  INDEX `idx_tb_workflow_deleted` (`deleted`),
  UNIQUE INDEX `idx_tb_workflow_name` (`name`, `deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工作流表';

-- =============================================
-- 16. tb_workflow_node - 工作流节点表
-- =============================================
DROP TABLE IF EXISTS `tb_workflow_node`;
CREATE TABLE `tb_workflow_node` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `workflow_id` BIGINT NOT NULL COMMENT '工作流 id',
  `node_key` VARCHAR(32) NOT NULL COMMENT '节点唯一标识',
  `name` VARCHAR(64) NOT NULL COMMENT '节点名称',
  `node_type` VARCHAR(32) NOT NULL COMMENT '节点类型: START/END/LLM/CONDITION/API_CALL',
  `config` JSON NOT NULL COMMENT '节点配置 JSON',
  `position_x` INT NOT NULL DEFAULT 0 COMMENT 'X 坐标',
  `position_y` INT NOT NULL DEFAULT 0 COMMENT 'Y 坐标',
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `deleted` TINYINT(1) NOT NULL DEFAULT 0,
  INDEX `idx_tb_wf_node_deleted` (`deleted`),
  INDEX `idx_tb_wf_node_wf_id` (`workflow_id`, `deleted`),
  UNIQUE INDEX `idx_tb_wf_node_key` (`workflow_id`, `node_key`, `deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工作流节点表';

-- =============================================
-- 17. tb_workflow_edge - 工作流连线表
-- =============================================
DROP TABLE IF EXISTS `tb_workflow_edge`;
CREATE TABLE `tb_workflow_edge` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `workflow_id` BIGINT NOT NULL COMMENT '工作流 id',
  `source_node_key` VARCHAR(32) NOT NULL COMMENT '源节点 key',
  `target_node_key` VARCHAR(32) NOT NULL COMMENT '目标节点 key',
  `condition` VARCHAR(256) DEFAULT '' COMMENT '条件表达式',
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `deleted` TINYINT(1) NOT NULL DEFAULT 0,
  INDEX `idx_tb_wf_edge_deleted` (`deleted`),
  INDEX `idx_tb_wf_edge_wf_id` (`workflow_id`, `deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工作流连线表';

-- =============================================
-- 18. tb_user - 用户表
-- =============================================
DROP TABLE IF EXISTS `tb_user`;
CREATE TABLE `tb_user` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `username` VARCHAR(64) NOT NULL COMMENT '用户名',
  `password_hash` VARCHAR(256) NOT NULL COMMENT '密码哈希',
  `email` VARCHAR(128) DEFAULT '' COMMENT '邮箱',
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `deleted` TINYINT(1) NOT NULL DEFAULT 0,
  INDEX `idx_tb_user_deleted` (`deleted`),
  UNIQUE INDEX `idx_tb_user_username` (`username`, `deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- =============================================
-- 19. tb_api_key - API Key 表
-- =============================================
DROP TABLE IF EXISTS `tb_api_key`;
CREATE TABLE `tb_api_key` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT NOT NULL COMMENT '用户 id',
  `api_key` VARCHAR(64) NOT NULL COMMENT 'API Key',
  `name` VARCHAR(64) NOT NULL COMMENT 'Key 名称',
  `last_used_at` DATETIME(3) DEFAULT NULL COMMENT '最后使用时间',
  `expires_at` DATETIME(3) DEFAULT NULL COMMENT '过期时间',
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `deleted` TINYINT(1) NOT NULL DEFAULT 0,
  INDEX `idx_tb_api_key_deleted` (`deleted`),
  INDEX `idx_tb_api_key_user_id` (`user_id`, `deleted`),
  UNIQUE INDEX `idx_tb_api_key_key` (`api_key`, `deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='API Key 表';

-- =============================================
-- 20. tb_workflow_run - 工作流执行记录
-- =============================================
DROP TABLE IF EXISTS `tb_workflow_run`;
CREATE TABLE `tb_workflow_run` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `workflow_id` BIGINT NOT NULL COMMENT '工作流 id',
  `status` VARCHAR(20) NOT NULL DEFAULT 'PENDING' COMMENT '状态: PENDING/RUNNING/SUCCESS/FAILED',
  `input` JSON DEFAULT NULL COMMENT '输入数据',
  `output` JSON DEFAULT NULL COMMENT '输出数据',
  `error_message` TEXT NOT NULL DEFAULT '' COMMENT '错误信息',
  `elapsed_ms` INT NOT NULL DEFAULT 0 COMMENT '耗时(毫秒)',
  `started_at` DATETIME(3) DEFAULT NULL COMMENT '开始时间',
  `finished_at` DATETIME(3) DEFAULT NULL COMMENT '结束时间',
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `deleted` TINYINT(1) NOT NULL DEFAULT 0,
  INDEX `idx_tb_wf_run_workflow_id` (`workflow_id`, `deleted`),
  INDEX `idx_tb_wf_run_status` (`status`, `deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工作流执行记录表';

-- =============================================
-- 21. tb_workflow_node_run - 工作流节点执行记录
-- =============================================
DROP TABLE IF EXISTS `tb_workflow_node_run`;
CREATE TABLE `tb_workflow_node_run` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `workflow_run_id` BIGINT NOT NULL COMMENT '工作流执行 id',
  `node_key` VARCHAR(32) NOT NULL COMMENT '节点 key',
  `node_type` VARCHAR(32) NOT NULL COMMENT '节点类型',
  `status` VARCHAR(20) NOT NULL DEFAULT 'PENDING' COMMENT '状态: PENDING/RUNNING/SUCCESS/FAILED',
  `input_data` JSON DEFAULT NULL COMMENT '输入数据',
  `output_data` JSON DEFAULT NULL COMMENT '输出数据',
  `error_message` TEXT NOT NULL DEFAULT '' COMMENT '错误信息',
  `elapsed_ms` INT NOT NULL DEFAULT 0 COMMENT '耗时(毫秒)',
  `started_at` DATETIME(3) DEFAULT NULL COMMENT '开始时间',
  `finished_at` DATETIME(3) DEFAULT NULL COMMENT '结束时间',
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `deleted` TINYINT(1) NOT NULL DEFAULT 0,
  INDEX `idx_tb_wf_node_run_run_id` (`workflow_run_id`, `deleted`),
  INDEX `idx_tb_wf_node_run_node_key` (`node_key`, `deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工作流节点执行记录表';

-- =============================================
-- 22. tb_refund_application - 退款申请表
-- =============================================
DROP TABLE IF EXISTS `tb_refund_application`;
CREATE TABLE `tb_refund_application` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `order_id` VARCHAR(64) NOT NULL COMMENT '订单号',
  `user_id` VARCHAR(64) NOT NULL COMMENT '用户ID',
  `amount` BIGINT NOT NULL COMMENT '退款金额(分)',
  `reason` VARCHAR(512) NOT NULL DEFAULT '' COMMENT '退款原因',
  `status` VARCHAR(32) NOT NULL DEFAULT 'PENDING' COMMENT 'PENDING/APPROVED/PROCESSING/COMPLETED/REJECTED',
  `reject_reason` VARCHAR(512) NOT NULL DEFAULT '' COMMENT '拒绝原因',
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `deleted` TINYINT(1) NOT NULL DEFAULT 0,
  INDEX `idx_tb_refund_application_deleted` (`deleted`),
  INDEX `idx_tb_refund_application_order_id` (`order_id`, `deleted`),
  INDEX `idx_tb_refund_application_status` (`status`, `deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='退款申请表';

SET FOREIGN_KEY_CHECKS = 1;
