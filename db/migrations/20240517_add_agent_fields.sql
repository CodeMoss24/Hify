-- =============================================
-- 迁移：为 tb_agent 表添加缺失字段
-- =============================================

-- 添加 description 字段
ALTER TABLE `tb_agent`
ADD COLUMN `description` VARCHAR(500) NOT NULL DEFAULT '' COMMENT '描述'
AFTER `name`;

-- 添加 temperature 字段
ALTER TABLE `tb_agent`
ADD COLUMN `temperature` DECIMAL(3,2) NOT NULL DEFAULT 0.70 COMMENT '温度参数 0.00~1.00'
AFTER `system_prompt`;

-- 添加 max_tokens 字段
ALTER TABLE `tb_agent`
ADD COLUMN `max_tokens` INT NOT NULL DEFAULT 2048 COMMENT '最大生成 Token 数'
AFTER `temperature`;

-- 添加 max_context_turns 字段
ALTER TABLE `tb_agent`
ADD COLUMN `max_context_turns` INT NOT NULL DEFAULT 10 COMMENT '保留最近对话轮数'
AFTER `max_tokens`;

-- 添加 enabled 字段
ALTER TABLE `tb_agent`
ADD COLUMN `enabled` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '0=禁用 1=启用'
AFTER `max_context_turns`;

-- =============================================
-- 验证字段是否添加成功
-- =============================================
SHOW COLUMNS FROM `tb_agent`;
