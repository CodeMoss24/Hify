-- 为 tb_document 表新增 error_message 和 chunk_count 字段
ALTER TABLE `tb_document`
  ADD COLUMN `error_message` VARCHAR(512) NOT NULL DEFAULT '' COMMENT '处理失败时的错误信息' AFTER `status`,
  ADD COLUMN `chunk_count` INT NOT NULL DEFAULT 0 COMMENT '分块数量' AFTER `error_message`;
