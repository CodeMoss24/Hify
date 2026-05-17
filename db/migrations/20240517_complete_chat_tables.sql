-- =============================================
-- 迁移：完善 chat 相关表结构
-- =============================================

-- 1. 检查并完善 tb_conversation 表
SET @col_exists = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'tb_conversation'
    AND COLUMN_NAME = 'status'
);

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE `tb_conversation` ADD COLUMN `status` VARCHAR(20) NOT NULL DEFAULT ''ACTIVE'' COMMENT ''ACTIVE/ARCHIVED'' AFTER `title`',
    'SELECT ''status 列已存在'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2. 检查并完善 tb_message 表
-- 2.1 修改 content 为 LONGTEXT
SET @col_type = (
    SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'tb_message'
    AND COLUMN_NAME = 'content'
);

SET @sql = IF(@col_type != 'longtext',
    'ALTER TABLE `tb_message` MODIFY COLUMN `content` LONGTEXT NOT NULL COMMENT ''消息内容''',
    'SELECT ''content 列已是 LONGTEXT'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2.2 添加 finish_reason 字段
SET @col_exists = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'tb_message'
    AND COLUMN_NAME = 'finish_reason'
);

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE `tb_message` ADD COLUMN `finish_reason` VARCHAR(20) NOT NULL DEFAULT '''' COMMENT ''stop/length/error'' AFTER `content`',
    'SELECT ''finish_reason 列已存在'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2.3 添加 latency_ms 字段
SET @col_exists = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'tb_message'
    AND COLUMN_NAME = 'latency_ms'
);

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE `tb_message` ADD COLUMN `latency_ms` INT NOT NULL DEFAULT 0 COMMENT ''响应耗时ms'' AFTER `finish_reason`',
    'SELECT ''latency_ms 列已存在'' AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- =============================================
-- 显示最终表结构
-- =============================================
SHOW CREATE TABLE `tb_agent`;
SHOW CREATE TABLE `tb_conversation`;
SHOW CREATE TABLE `tb_message`;
