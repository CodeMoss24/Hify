-- =============================================
-- 一键修复数据库表结构
-- =============================================

-- 使用数据库
USE `hify`;

-- =============================================
-- 修复 tb_agent 表
-- =============================================

-- 添加 description (如果不存在)
SET @dbname = DATABASE();
SET @tablename = 'tb_agent';
SET @columnname = 'description';

SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_schema = @dbname)
      AND (table_name = @tablename)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN `description` VARCHAR(500) NOT NULL DEFAULT '''' COMMENT ''描述'' AFTER `name`')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 添加 temperature (如果不存在)
SET @columnname = 'temperature';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_schema = @dbname)
      AND (table_name = @tablename)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN `temperature` DECIMAL(3,2) NOT NULL DEFAULT 0.70 COMMENT ''温度参数 0.00~1.00'' AFTER `system_prompt`')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 添加 max_tokens (如果不存在)
SET @columnname = 'max_tokens';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_schema = @dbname)
      AND (table_name = @tablename)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN `max_tokens` INT NOT NULL DEFAULT 2048 COMMENT ''最大生成 Token 数'' AFTER `temperature`')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 添加 max_context_turns (如果不存在)
SET @columnname = 'max_context_turns';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_schema = @dbname)
      AND (table_name = @tablename)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN `max_context_turns` INT NOT NULL DEFAULT 10 COMMENT ''保留最近对话轮数'' AFTER `max_tokens`')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 添加 enabled (如果不存在)
SET @columnname = 'enabled';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_schema = @dbname)
      AND (table_name = @tablename)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN `enabled` TINYINT(1) NOT NULL DEFAULT 1 COMMENT ''0=禁用 1=启用'' AFTER `max_context_turns`')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- =============================================
-- 修复 tb_conversation 表
-- =============================================

SET @tablename = 'tb_conversation';

-- 添加 status (如果不存在)
SET @columnname = 'status';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_schema = @dbname)
      AND (table_name = @tablename)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN `status` VARCHAR(20) NOT NULL DEFAULT ''ACTIVE'' COMMENT ''ACTIVE/ARCHIVED'' AFTER `title`')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- =============================================
-- 修复 tb_message 表
-- =============================================

SET @tablename = 'tb_message';

-- 修改 content 为 LONGTEXT (如果需要)
SET @coltype = (
  SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = @dbname
  AND TABLE_NAME = @tablename
  AND COLUMN_NAME = 'content'
);

SET @preparedStatement = (SELECT IF(
  @coltype != 'longtext',
  CONCAT('ALTER TABLE ', @tablename, ' MODIFY COLUMN `content` LONGTEXT NOT NULL COMMENT ''消息内容'''),
  'SELECT 1'
));
PREPARE alterIfNeeded FROM @preparedStatement;
EXECUTE alterIfNeeded;
DEALLOCATE PREPARE alterIfNeeded;

-- 添加 finish_reason (如果不存在)
SET @columnname = 'finish_reason';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_schema = @dbname)
      AND (table_name = @tablename)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN `finish_reason` VARCHAR(20) NOT NULL DEFAULT '''' COMMENT ''stop/length/error'' AFTER `content`')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 添加 latency_ms (如果不存在)
SET @columnname = 'latency_ms';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_schema = @dbname)
      AND (table_name = @tablename)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN `latency_ms` INT NOT NULL DEFAULT 0 COMMENT ''响应耗时ms'' AFTER `finish_reason`')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- =============================================
-- 验证结果
-- =============================================
SELECT '=== tb_agent 表结构 ===' AS info;
SHOW COLUMNS FROM `tb_agent`;

SELECT '=== tb_conversation 表结构 ===' AS info;
SHOW COLUMNS FROM `tb_conversation`;

SELECT '=== tb_message 表结构 ===' AS info;
SHOW COLUMNS FROM `tb_message`;

SELECT '=== 迁移完成 ===' AS status;
