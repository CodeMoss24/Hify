# db/ — 数据库建表脚本

## 目录说明

`schema.sql` — 一期手动建表脚本
`README.md` — 本目录说明

## 一期策略

开发阶段直接使用 `schema.sql` 手动执行建表，不引入 Alembic。理由：
- 表结构仍在快速迭代，Alembic 迁移脚本维护成本高
- 单人开发效率优先，拖慢节奏

## 后期迁移

生产环境或团队协作时，引入 Alembic 替代手动建表：
1. 安装 Alembic：`pip install alembic`
2. 初始化：`alembic init alembic`
3. 将 `schema.sql` 转换为初始迁移脚本
4. 后续表结构变更通过 `alembic revision --autogenerate` 生成迁移脚本

届时本目录结构：
```
db/
├── schema.sql         # 保留，作为初始化的参照
├── alembic/           # Alembic 迁移脚本目录
│   ├── versions/      # 各版本迁移脚本
│   └── env.py
└── README.md
```
