-- -*- coding: utf-8 -*-
-- MCP Gateway Mock Data - 完整测试数据
-- 执行顺序：先执行 init_db.sql 创建表结构，再执行本文件填充测试数据

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;
USE ai_mcp_gateway_v2;

-- =====================================================
-- 1. 清理现有测试数据
-- =====================================================
DELETE FROM mcp_protocol_mapping;
DELETE FROM mcp_protocol_http;
DELETE FROM mcp_gateway_tool;
DELETE FROM mcp_gateway_microservice;
DELETE FROM mcp_gateway_auth;
DELETE FROM mcp_gateway;
DELETE FROM mcp_microservice;
DELETE FROM mcp_gateway_llm;
DELETE FROM mcp_llm_config;
DELETE FROM sys_role_business_line;
DELETE FROM sys_gateway_permission;
DELETE FROM sys_role_permission;
DELETE FROM sys_user_role;
DELETE FROM sys_user_business_line;
DELETE FROM sys_permission;
DELETE FROM sys_resource;
DELETE FROM sys_user;
DELETE FROM sys_role;
DELETE FROM sys_business_line;

-- =====================================================
-- 2. 基础配置数据
-- =====================================================

-- 网关配置
INSERT INTO mcp_gateway (gateway_id, gateway_name, gateway_desc, version, business_line_id, status) VALUES
('gateway_001', '商品服务网关', 'Product Service MCP Gateway', '1.0.0', 2, 1),
('gateway_002', 'OA服务网关', 'OA Service MCP Gateway', '1.0.0', 1, 1);

-- OA 网关 API Key
INSERT INTO mcp_gateway_auth (gateway_id, key_id, api_key_hash, key_preview, rate_limit, expire_time, remark, status) VALUES
('gateway_002', 'oakey001', '$2b$12$9lHqeqRUeFzcAs9ixbFqwOsYYwoQakSuwZLdGfbYKelCGShl0X6ba', 'sk-oakey00...WxYz', 600, '2099-12-31 23:59:59', 'OA默认测试Key', 1);

-- 默认 API Key (仅供测试使用)
-- API Key: sk-defaultkey001:Xy7zA1b2C3d4E5f6G7h8I9j0KlMnOpQrStUvWxYz
INSERT INTO mcp_gateway_auth (gateway_id, key_id, api_key_hash, key_preview, rate_limit, expire_time, remark, status) VALUES
('gateway_001', 'defaultkey001', '$2b$12$9lHqeqRUeFzcAs9ixbFqwOsYYwoQakSuwZLdGfbYKelCGShl0X6ba', 'sk-defaultke...WxYz', 600, '2099-12-31 23:59:59', '默认测试Key', 1);

-- LLM 配置 (v10.0 统一)
-- API Key 直接存储（演示用，生产环境建议加密）
INSERT INTO mcp_llm_config (config_id, config_name, api_type, base_url, model_name, api_key, description, status) VALUES
('minimax_default', 'MiniMax默认', 'anthropic', 'https://api.minimaxi.com/anthropic', 'MiniMax-M2.5', 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJHcm91cE5hbWUiOiLnmb7ono3kupHliJsiLCJVc2VyTmFtZSI6IueZvuiejeS6keWImyIsIkFjY291bnQiOiIiLCJTdWJqZWN0SUQiOiIxOTk4NjY2Nzg0MTg5NzE0Njk5IiwiUGhvbmUiOiIxOTUxMTk4MTY4OSIsIkdyb3VwSUQiOiIxOTk4NjY2Nzg0MTgxMzI2MDkxIiwiUGFnZU5hbWUiOiIiLCJNYWlsIjoiIiwiQ3JlYXRlVGltZSI6IjIwMjUtMTItMTAgMjE6MzI6MTYiLCJUb2tlblR5cGUiOjQsImlzcyI6Im1pbmltYXgifQ.u5vB41nODwjoj-a728IeKgtdnoL7AC0rJbw3Uv8iXA6CVqXQ3SY5RCTo87yAzAeva8prR4YcBQ-nIG5mtXYd_jemI-mjA909hYN3yvWsjuD4m_3U2SqoDY5E6vV6gyGPzQlnB0OkzOKJCwQbb6FUfcymWTSiAtw2k8DgfCeQLJLUMKmxOjHYOontut_gujCxY57wU-8h0p4PWkS74hLnritLO3oIBq6ZNmf1d3uC4pw-jVCflSlymm16luObc-DeohNc83fAOtMPSJ76mi_bdAcoIgCOyAP3VUan53QyLHwzcq-i8YI-TuxkAvH3slauNsHAfUWNhlqJouRXdFwsHg', 'MiniMax大模型(Anthropic兼容接口)', 1);

-- 网关-LLM绑定关系 (v10.0)
INSERT INTO mcp_gateway_llm (gateway_id, llm_config_id, status) VALUES
('gateway_001', 'minimax_default', 1),
('gateway_002', 'minimax_default', 1);

-- =====================================================
-- 3. RBAC 权限系统数据
-- =====================================================

-- 业务线
INSERT INTO sys_business_line (id, line_code, line_name, description, status) VALUES
(1, 'OA', 'OA办公', 'OA办公自动化系统', 1),
(2, 'PRODUCT', '商品服务', '商品管理微服务', 1);

-- 资源定义
INSERT INTO sys_resource (id, resource_code, resource_name, resource_type, parent_id, api_path, sort_order, status) VALUES
(1, 'dashboard', '仪表盘', 'menu', 0, '/home', 0, 1),
(2, 'gateway', '网关管理', 'menu', 0, '/gateway', 1, 1),
(3, 'microservice', '微服务管理', 'menu', 0, '/microservice', 2, 1),
(4, 'tool', '工具管理', 'menu', 0, '/tools', 3, 1),
(5, 'chat', 'AI对话', 'menu', 0, '/chat', 4, 1),
(6, 'system', '系统管理', 'menu', 0, '/system', 5, 1),
(7, 'user', '用户管理', 'menu', 6, '/system/user', 1, 1),
(8, 'role', '角色管理', 'menu', 6, '/system/role', 2, 1),
(9, 'business_line', '业务线管理', 'menu', 6, '/system/business-line', 3, 1);

-- 权限定义
INSERT INTO sys_permission (id, permission_code, permission_name, resource_id, action, description, status) VALUES
(1, 'gateway:create', '创建网关', 2, 'create', '创建新网关', 1),
(2, 'gateway:read', '查看网关', 2, 'read', '查看网关详情和列表', 1),
(3, 'gateway:update', '更新网关', 2, 'update', '修改网关配置', 1),
(4, 'gateway:delete', '删除网关', 2, 'delete', '删除网关', 1),
(5, 'microservice:create', '创建微服务', 3, 'create', '注册新微服务', 1),
(6, 'microservice:read', '查看微服务', 3, 'read', '查看微服务详情和列表', 1),
(7, 'microservice:update', '更新微服务', 3, 'update', '修改微服务配置', 1),
(8, 'microservice:delete', '删除微服务', 3, 'delete', '删除微服务', 1),
(9, 'tool:create', '创建工具', 4, 'create', '创建新工具', 1),
(10, 'tool:read', '查看工具', 4, 'read', '查看工具详情和列表', 1),
(11, 'tool:update', '更新工具', 4, 'update', '修改工具配置', 1),
(12, 'tool:delete', '删除工具', 4, 'delete', '删除工具', 1),
(13, 'user:create', '创建用户', 7, 'create', '创建新用户', 1),
(14, 'user:read', '查看用户', 7, 'read', '查看用户详情和列表', 1),
(15, 'user:update', '更新用户', 7, 'update', '修改用户信息', 1),
(16, 'user:delete', '删除用户', 7, 'delete', '删除用户', 1),
(17, 'role:create', '创建角色', 8, 'create', '创建新角色', 1),
(18, 'role:read', '查看角色', 8, 'read', '查看角色详情和列表', 1),
(19, 'role:update', '更新角色', 8, 'update', '修改角色信息', 1),
(20, 'role:delete', '删除角色', 8, 'delete', '删除角色', 1),
(21, 'business_line:create', '创建业务线', 9, 'create', '创建新业务线', 1),
(22, 'business_line:read', '查看业务线', 9, 'read', '查看业务线详情和列表', 1),
(23, 'business_line:update', '更新业务线', 9, 'update', '修改业务线信息', 1),
(24, 'business_line:delete', '删除业务线', 9, 'delete', '删除业务线', 1);

-- 角色 (与前端 Layout.vue 一致)
-- SUPER_ADMIN: 超级管理员 - 全局角色
-- OA_ADMIN: OA管理员 - OA业务线管理员
-- PRODUCT_ADMIN: 商品管理员 - 商品业务线管理员
-- OA_USER: OA普通用户 - 只能查看和对话
-- PRODUCT_USER: 商品普通用户 - 只能查看和对话
INSERT INTO sys_role (id, role_code, role_name, description, business_line_id, is_system, status) VALUES
(1, 'SUPER_ADMIN', '超级管理员', '拥有系统全部权限', NULL, 1, 1),
(2, 'OA_ADMIN', 'OA管理员', 'OA业务线管理员', 1, 1, 1),
(3, 'PRODUCT_ADMIN', '商品管理员', '商品业务线管理员', 2, 1, 1),
(4, 'OA_USER', 'OA普通用户', 'OA业务线普通用户，只能查看和对话', 1, 1, 1),
(5, 'PRODUCT_USER', '商品普通用户', '商品业务线普通用户，只能查看和对话', 2, 1, 1);

-- 用户 (密码: admin123 或 123456)
-- admin 密码: admin123
-- oa_admin 密码: 123456
-- product_admin 密码: 123456
-- oa_user 密码: 123456
-- product_user 密码: 123456
INSERT INTO sys_user (id, username, password_hash, real_name, email, status) VALUES
(1, 'admin', '$2b$12$dCUfQCPNRi/QAuDMIsyDYe0ID5h3BhCoYvUlnfvFf7XPUFGvy2682', '系统管理员', 'admin@example.com', 1),
(2, 'oa_admin', '$2b$12$YW1lGkiyAMwcg.lOWwi0EubeZpLMO4cpyLMAPTyOZoUdGIkCw.Cpa', 'OA管理员', 'oa@example.com', 1),
(3, 'product_admin', '$2b$12$YW1lGkiyAMwcg.lOWwi0EubeZpLMO4cpyLMAPTyOZoUdGIkCw.Cpa', '商品管理员', 'product@example.com', 1),
(4, 'oa_user', '$2b$12$YW1lGkiyAMwcg.lOWwi0EubeZpLMO4cpyLMAPTyOZoUdGIkCw.Cpa', 'OA普通用户', 'oa_user@example.com', 1),
(5, 'product_user', '$2b$12$YW1lGkiyAMwcg.lOWwi0EubeZpLMO4cpyLMAPTyOZoUdGIkCw.Cpa', '商品普通用户', 'product_user@example.com', 1);

-- 用户角色关联
INSERT INTO sys_user_role (user_id, role_id) VALUES
(1, 1), -- admin -> SUPER_ADMIN
(2, 2), -- oa_admin -> OA_ADMIN
(3, 3), -- product_admin -> PRODUCT_ADMIN
(4, 4), -- oa_user -> OA_USER
(5, 5); -- product_user -> PRODUCT_USER

-- 用户-业务线关联
INSERT INTO sys_user_business_line (user_id, business_line_id, is_admin) VALUES
(1, 1, 1), -- admin 是所有业务线管理员
(1, 2, 1),
(2, 1, 1), -- oa_admin 是OA业务线管理员
(3, 2, 1), -- product_admin 是商品业务线管理员
(4, 1, 0), -- oa_user 是OA业务线普通用户
(5, 2, 0); -- product_user 是商品业务线普通用户

-- 超级管理员拥有所有权限
INSERT INTO sys_role_permission (role_id, permission_id)
SELECT 1, id FROM sys_permission WHERE status = 1;

-- OA_ADMIN 权限: 网关管理权限(针对OA网关) + 只读权限(其他网关) + 用户管理权限 + 角色管理权限
INSERT INTO sys_role_permission (role_id, permission_id) VALUES
(2, 1),   -- gateway:create
(2, 2),   -- gateway:read
(2, 3),   -- gateway:update
(2, 4),   -- gateway:delete
(2, 6),   -- microservice:read
(2, 7),   -- microservice:update
(2, 10),  -- tool:read
(2, 11),  -- tool:update
(2, 13),  -- user:create
(2, 14),  -- user:read
(2, 15),  -- user:update
(2, 16),  -- user:delete
(2, 17),  -- role:create
(2, 18),  -- role:read
(2, 19),  -- role:update
(2, 20),  -- role:delete
(2, 22),  -- business_line:read
(2, 23);  -- business_line:update

-- PRODUCT_ADMIN 权限: 网关、微服务、工具的管理权限 + 用户管理权限 + 角色管理权限
INSERT INTO sys_role_permission (role_id, permission_id) VALUES
(3, 1),   -- gateway:create
(3, 2),   -- gateway:read
(3, 3),   -- gateway:update
(3, 4),   -- gateway:delete
(3, 5),   -- microservice:create
(3, 6),   -- microservice:read
(3, 7),   -- microservice:update
(3, 8),   -- microservice:delete
(3, 9),   -- tool:create
(3, 10),  -- tool:read
(3, 11),  -- tool:update
(3, 12),  -- tool:delete
(3, 13),  -- user:create
(3, 14),  -- user:read
(3, 15),  -- user:update
(3, 16),  -- user:delete
(3, 17),  -- role:create
(3, 18),  -- role:read
(3, 19),  -- role:update
(3, 20),  -- role:delete
(3, 22),  -- business_line:read
(3, 23);  -- business_line:update

-- OA_USER 权限: 只读权限（不包含系统管理模块）
INSERT INTO sys_role_permission (role_id, permission_id) VALUES
(4, 2),   -- gateway:read
(4, 6),   -- microservice:read
(4, 10);  -- tool:read

-- PRODUCT_USER 权限: 只读权限（不包含系统管理模块）
INSERT INTO sys_role_permission (role_id, permission_id) VALUES
(5, 2),   -- gateway:read
(5, 6),   -- microservice:read
(5, 10);  -- tool:read

-- 网关权限配置
INSERT INTO sys_gateway_permission (role_id, gateway_id, can_create, can_read, can_update, can_delete, can_chat) VALUES
(1, 'gateway_001', 1, 1, 1, 1, 1), -- 超级管理员全部权限
(1, 'gateway_002', 1, 1, 1, 1, 1), -- 超级管理员全部权限
(2, 'gateway_001', 0, 1, 0, 0, 1), -- OA管理员只读和对话
(2, 'gateway_002', 1, 1, 1, 1, 1), -- OA管理员全部权限
(3, 'gateway_001', 1, 1, 1, 0, 1), -- 商品管理员除删除外全部权限
(3, 'gateway_002', 0, 1, 0, 0, 1), -- 商品管理员只读和对话
(4, 'gateway_002', 0, 1, 0, 0, 1), -- OA普通用户只能查看和对话
(5, 'gateway_001', 0, 1, 0, 0, 1); -- 商品普通用户只能查看和对话

-- 角色-业务线管理员关联（通过角色授予业务线管理员权限）
INSERT INTO sys_role_business_line (role_id, business_line_id, is_admin) VALUES
(2, 1, 1),  -- OA_ADMIN 角色是OA业务线管理员
(3, 2, 1);  -- PRODUCT_ADMIN 角色是商品业务线管理员

-- =====================================================
-- 2. 插入微服务配置
-- =====================================================
INSERT INTO mcp_microservice (name, http_base_url, description, business_line_id, health_status, status, create_time, update_time)
VALUES ('Product Service', 'http://localhost:8778', '商品服务 - 提供商品、库存、订单、定价等核心功能', 2, 'healthy', 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE description = VALUES(description), health_status = VALUES(health_status);

-- 获取微服务ID
SET @microservice_id = (SELECT id FROM mcp_microservice WHERE name = 'Product Service');

-- =====================================================
-- 3. 插入Product Service的HTTP协议配置
-- =====================================================

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (1, 'http://localhost:8778/api/products/search/advanced', 'GET', NULL, 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (2, 'http://localhost:8778/api/products/all', 'GET', NULL, 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (3, 'http://localhost:8778/api/products/{product_id}', 'GET', NULL, 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (4, 'http://localhost:8778/api/products/compare', 'POST', '{"Content-Type":"application/json"}', 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (5, 'http://localhost:8778/api/products/{product_id}/alternatives', 'GET', NULL, 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (6, 'http://localhost:8778/api/products/trending', 'GET', NULL, 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (7, 'http://localhost:8778/api/categories', 'GET', NULL, 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (8, 'http://localhost:8778/api/categories/{category_id}', 'GET', NULL, 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (10, 'http://localhost:8778/api/inventory/check/{product_id}', 'GET', NULL, 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (11, 'http://localhost:8778/api/inventory/reserve', 'POST', '{"Content-Type":"application/json"}', 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (12, 'http://localhost:8778/api/inventory/reserve/{reservation_id}', 'DELETE', NULL, 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (13, 'http://localhost:8778/api/inventory/reserve/{reservation_id}/confirm', 'POST', NULL, 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (20, 'http://localhost:8778/api/pricing/calculate', 'POST', '{"Content-Type":"application/json"}', 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (21, 'http://localhost:8778/api/pricing/coupons/{code}', 'GET', NULL, 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (22, 'http://localhost:8778/api/pricing/coupons/apply', 'POST', '{"Content-Type":"application/json"}', 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (23, 'http://localhost:8778/api/pricing/member-levels', 'GET', NULL, 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (30, 'http://localhost:8778/api/orders', 'POST', '{"Content-Type":"application/json"}', 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (31, 'http://localhost:8778/api/orders', 'GET', NULL, 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (32, 'http://localhost:8778/api/orders/{order_no}', 'GET', NULL, 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (33, 'http://localhost:8778/api/orders/{order_no}/pay', 'POST', '{"Content-Type":"application/json"}', 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (34, 'http://localhost:8778/api/orders/{order_no}/cancel', 'POST', '{"Content-Type":"application/json"}', 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (40, 'http://localhost:8778/api/analytics/sales', 'GET', NULL, 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (41, 'http://localhost:8778/api/analytics/low-stock', 'GET', NULL, 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (42, 'http://localhost:8778/api/analytics/recommend', 'GET', NULL, 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time)
VALUES (43, 'http://localhost:8778/api/analytics/category-stats', 'GET', NULL, 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

-- =====================================================
-- 4. 插入MCP工具配置 (绑定到Product Service微服务)
-- 包含模拟的调用统计数据展示不同天气状态
-- =====================================================

-- ☀️ 晴朗状态工具 (错误率 < 10%)
INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 2, 'get_all_products', 'function', '获取所有商品列表，返回商品ID、名称、价格、库存等信息', '1.0.0', 2, 'http', @microservice_id, 1, 'sunny', 100, 3, '0000', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 3, 'get_product_by_id', 'function', '根据ID获取单个商品详情', '1.0.0', 3, 'http', @microservice_id, 1, 'sunny', 85, 2, '0000', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 4, 'search_products', 'function', '搜索商品，支持关键词、分类、状态筛选、价格区间、排序', '1.0.0', 1, 'http', @microservice_id, 1, 'sunny', 120, 5, '0000', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 5, 'get_categories', 'function', '获取所有商品分类', '1.0.0', 7, 'http', @microservice_id, 1, 'sunny', 50, 1, '0000', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 6, 'get_category_by_id', 'function', '根据ID获取分类详情', '1.0.0', 8, 'http', @microservice_id, 1, 'sunny', 30, 0, '0000', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

-- ☁️ 阴云状态工具 (错误率 10%-50%)
INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 7, 'compare_products', 'function', '商品比价，批量查询多个商品的详细信息并按价格排序', '1.0.0', 4, 'http', @microservice_id, 1, 'cloudy', 40, 12, '4001', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 8, 'get_alternatives', 'function', '获取商品的替代推荐（同分类或相似价格）', '1.0.0', 5, 'http', @microservice_id, 1, 'cloudy', 25, 8, '4002', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

-- ☀️ 晴朗状态工具
INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 9, 'get_trending_products', 'function', '获取热销商品榜单', '1.0.0', 6, 'http', @microservice_id, 1, 'sunny', 60, 2, '0000', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 10, 'check_inventory', 'function', '检查商品库存状态，包括可用数量、预留情况', '1.0.0', 10, 'http', @microservice_id, 1, 'sunny', 200, 8, '0000', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

-- 🌧️ 下雨状态工具 (错误率 > 50%)
INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 11, 'reserve_inventory', 'function', '预留库存，带TTL有效期，防止超卖', '1.0.0', 11, 'http', @microservice_id, 1, 'rainy', 20, 15, '5001', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 12, 'release_reservation', 'function', '释放库存预留', '1.0.0', 12, 'http', @microservice_id, 1, 'rainy', 15, 12, 'TIMEOUT', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 13, 'confirm_reservation', 'function', '确认库存预留，扣减实际库存', '1.0.0', 13, 'http', @microservice_id, 1, 'cloudy', 18, 6, '4003', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

-- ☀️ 晴朗状态工具
INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 20, 'calculate_price', 'function', '计算商品最终价格，支持会员折扣、优惠券', '1.0.0', 20, 'http', @microservice_id, 1, 'sunny', 150, 5, '0000', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 21, 'get_coupon_info', 'function', '获取优惠券信息，校验是否有效', '1.0.0', 21, 'http', @microservice_id, 1, 'sunny', 80, 4, '0000', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 22, 'apply_coupon', 'function', '试算优惠券应用后的价格', '1.0.0', 22, 'http', @microservice_id, 1, 'cloudy', 35, 10, '4004', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 23, 'get_member_levels', 'function', '获取会员等级列表及折扣率', '1.0.0', 23, 'http', @microservice_id, 1, 'sunny', 45, 1, '0000', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 30, 'create_order', 'function', '创建订单，支持使用库存预留', '1.0.0', 30, 'http', @microservice_id, 1, 'sunny', 90, 6, '0000', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 31, 'list_orders', 'function', '查询订单列表，支持状态、日期筛选', '1.0.0', 31, 'http', @microservice_id, 1, 'sunny', 70, 3, '0000', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 32, 'get_order', 'function', '获取订单详情', '1.0.0', 32, 'http', @microservice_id, 1, 'sunny', 55, 2, '0000', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 33, 'pay_order', 'function', '模拟支付订单', '1.0.0', 33, 'http', @microservice_id, 1, 'cloudy', 40, 15, '5002', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 34, 'cancel_order', 'function', '取消订单，自动释放库存', '1.0.0', 34, 'http', @microservice_id, 1, 'sunny', 25, 1, '0000', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 40, 'get_sales_stats', 'function', '销售统计，支持按时间、分类筛选', '1.0.0', 40, 'http', @microservice_id, 1, 'sunny', 30, 1, '0000', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 41, 'get_low_stock_alert', 'function', '低库存预警，库存低于阈值时提醒', '1.0.0', 41, 'http', @microservice_id, 1, 'sunny', 20, 0, '0000', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 42, 'get_recommendations', 'function', '获取商品推荐，基于销量和库存', '1.0.0', 42, 'http', @microservice_id, 1, 'sunny', 45, 2, '0000', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES ('gateway_001', 43, 'get_category_stats', 'function', '获取各分类的销售统计', '1.0.0', 43, 'http', @microservice_id, 1, 'sunny', 35, 1, '0000', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

-- =====================================================
-- 5. 插入参数映射
-- =====================================================

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES 
(1, 'query', 'keyword', 'string', '搜索关键词', 0, 1, NOW(), NOW()),
(1, 'query', 'category_id', 'integer', '分类ID筛选', 0, 2, NOW(), NOW()),
(1, 'query', 'min_price', 'number', '最低价格', 0, 3, NOW(), NOW()),
(1, 'query', 'max_price', 'number', '最高价格', 0, 4, NOW(), NOW()),
(1, 'query', 'in_stock_only', 'boolean', '仅显示有货', 0, 5, NOW(), NOW()),
(1, 'query', 'sort_by', 'string', '排序方式(relevance/price_asc/price_desc/stock)', 0, 6, NOW(), NOW()),
(1, 'query', 'page', 'integer', '页码', 0, 7, NOW(), NOW()),
(1, 'query', 'page_size', 'integer', '每页数量', 0, 8, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES (3, 'path', 'product_id', 'integer', '商品ID', 1, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES (8, 'path', 'category_id', 'integer', '分类ID', 1, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES (4, 'body', 'product_ids', 'array', '商品ID数组，最多10个', 1, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES 
(5, 'path', 'product_id', 'integer', '商品ID', 1, 1, NOW(), NOW()),
(5, 'query', 'limit', 'integer', '返回数量，默认5', 0, 2, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES 
(6, 'query', 'category_id', 'integer', '分类ID筛选', 0, 1, NOW(), NOW()),
(6, 'query', 'limit', 'integer', '返回数量，默认10', 0, 2, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES 
(10, 'path', 'product_id', 'integer', '商品ID', 1, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES 
-- reserve_inventory: product_id/quantity/ttl_seconds 均为 Query 参数（FastAPI Query(...)）
(11, 'query', 'product_id', 'integer', '商品ID', 1, 1, NOW(), NOW()),
(11, 'query', 'quantity', 'integer', '预留数量', 1, 2, NOW(), NOW()),
(11, 'query', 'ttl_seconds', 'integer', '预留有效期(秒)，默认300', 0, 3, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc), param_location = VALUES(param_location);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES (12, 'path', 'reservation_id', 'string', '预留ID', 1, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES (13, 'path', 'reservation_id', 'string', '预留ID', 1, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES 
(20, 'body', 'items', 'array', '商品列表 [{"product_id":1,"quantity":2}]', 1, 1, NOW(), NOW()),
(20, 'body', 'member_level', 'string', '会员等级(normal/silver/gold/platinum/diamond)', 0, 2, NOW(), NOW()),
(20, 'body', 'coupon_code', 'string', '优惠券码', 0, 3, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES (21, 'path', 'code', 'string', '优惠券码', 1, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES 
-- apply_coupon: code 和 order_amount 均为 Query 参数
(22, 'query', 'code', 'string', '优惠券码', 1, 1, NOW(), NOW()),
(22, 'query', 'order_amount', 'number', '订单金额', 1, 2, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc), param_location = VALUES(param_location);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES 
(30, 'body', 'items', 'array', '订单商品 [{"product_id":1,"quantity":1,"reservation_id":"res_xxx"}]', 1, 1, NOW(), NOW()),
(30, 'body', 'reservation_ids', 'array', '预留ID列表(可选)，填入后自动确认预留并扣减库存', 0, 2, NOW(), NOW()),
(30, 'body', 'customer_name', 'string', '客户姓名', 0, 3, NOW(), NOW()),
(30, 'body', 'customer_phone', 'string', '客户电话', 0, 4, NOW(), NOW()),
(30, 'body', 'shipping_address', 'string', '收货地址', 0, 5, NOW(), NOW()),
(30, 'body', 'remark', 'string', '备注', 0, 6, NOW(), NOW()),
(30, 'body', 'payment_method', 'string', '支付方式(alipay/wechat/bank)', 0, 7, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc), sort_order = VALUES(sort_order);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES 
(31, 'query', 'status', 'string', '订单状态筛选(pending/paid/shipped/completed/cancelled)', 0, 1, NOW(), NOW()),
(31, 'query', 'customer_phone', 'string', '按客户手机号查询', 0, 2, NOW(), NOW()),
(31, 'query', 'start_date', 'string', '开始日期(YYYY-MM-DD)', 0, 3, NOW(), NOW()),
(31, 'query', 'end_date', 'string', '结束日期(YYYY-MM-DD)', 0, 4, NOW(), NOW()),
(31, 'query', 'page', 'integer', '页码', 0, 5, NOW(), NOW()),
(31, 'query', 'page_size', 'integer', '每页数量', 0, 6, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc), sort_order = VALUES(sort_order);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES (32, 'path', 'order_no', 'string', '订单号', 1, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES 
-- pay_order: payment_method 是 Query 参数（FastAPI Query(...)）
(33, 'path', 'order_no', 'string', '订单号', 1, 0, NOW(), NOW()),
(33, 'query', 'payment_method', 'string', '支付方式(alipay/wechat/bank)', 1, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc), param_location = VALUES(param_location);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES 
-- cancel_order: reason 是 Query 参数（FastAPI Query(None)）
(34, 'path', 'order_no', 'string', '订单号', 1, 0, NOW(), NOW()),
(34, 'query', 'reason', 'string', '取消原因', 0, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc), param_location = VALUES(param_location);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES 
(40, 'query', 'start_date', 'string', '开始日期', 0, 1, NOW(), NOW()),
(40, 'query', 'end_date', 'string', '结束日期', 0, 2, NOW(), NOW()),
(40, 'query', 'category_id', 'integer', '分类ID', 0, 3, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES (41, 'query', 'threshold', 'integer', '库存预警阈值', 0, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES 
(42, 'query', 'category_id', 'integer', '分类ID', 0, 1, NOW(), NOW()),
(42, 'query', 'limit', 'integer', '返回数量', 0, 2, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc);

-- =====================================================
-- 6. 验证
-- =====================================================
SELECT '微服务数量:' AS '', COUNT(*) FROM mcp_microservice;
SELECT '工具数量:' AS '', COUNT(*) FROM mcp_gateway_tool WHERE gateway_id = 'gateway_001';
SELECT '协议数量:' AS '', COUNT(*) FROM mcp_protocol_http WHERE http_url LIKE '%localhost:8778%';
SELECT '用户数量:' AS '', COUNT(*) FROM sys_user;
SELECT '角色数量:' AS '', COUNT(*) FROM sys_role;

-- =====================================================
-- 8. OA Service 微服务注册
-- =====================================================

INSERT INTO mcp_microservice (name, http_base_url, description, business_line_id, health_status, status, create_time, update_time)
VALUES ('OA Service', 'http://localhost:8890', 'OA办公自动化服务 - 提供员工信息管理、请假审批、报销审批等功能', 1, 'healthy', 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE description = VALUES(description), health_status = VALUES(health_status);

-- 获取OA微服务ID
SET @oa_microservice_id = (SELECT id FROM mcp_microservice WHERE name = 'OA Service');

-- =====================================================
-- 9. OA Service 工具注册
-- =====================================================

-- OA Service HTTP 协议配置 (protocol_id 从 50 开始)
INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, create_time, update_time) VALUES
(50, 'http://localhost:8890/api/employees', 'GET', NULL, 30000, 0, NOW(), NOW()),
(51, 'http://localhost:8890/api/employees', 'POST', '{"Content-Type":"application/json"}', 30000, 0, NOW(), NOW()),
(52, 'http://localhost:8890/api/employees/{employee_id}', 'GET', NULL, 30000, 0, NOW(), NOW()),
(53, 'http://localhost:8890/api/employees/{employee_id}', 'PUT', '{"Content-Type":"application/json"}', 30000, 0, NOW(), NOW()),
(54, 'http://localhost:8890/api/employees/{employee_id}', 'DELETE', NULL, 30000, 0, NOW(), NOW()),
(55, 'http://localhost:8890/api/leaves', 'GET', NULL, 30000, 0, NOW(), NOW()),
(56, 'http://localhost:8890/api/leaves', 'POST', '{"Content-Type":"application/json"}', 30000, 0, NOW(), NOW()),
(57, 'http://localhost:8890/api/leaves/{leave_id}', 'GET', NULL, 30000, 0, NOW(), NOW()),
(58, 'http://localhost:8890/api/leaves/{leave_id}', 'PUT', '{"Content-Type":"application/json"}', 30000, 0, NOW(), NOW()),
(59, 'http://localhost:8890/api/leaves/{leave_id}/approve', 'PUT', '{"Content-Type":"application/json"}', 30000, 0, NOW(), NOW()),
(60, 'http://localhost:8890/api/leaves/{leave_id}/reject', 'PUT', '{"Content-Type":"application/json"}', 30000, 0, NOW(), NOW()),
(61, 'http://localhost:8890/api/leaves/{leave_id}/cancel', 'PUT', NULL, 30000, 0, NOW(), NOW()),
(62, 'http://localhost:8890/api/expenses', 'GET', NULL, 30000, 0, NOW(), NOW()),
(63, 'http://localhost:8890/api/expenses', 'POST', '{"Content-Type":"application/json"}', 30000, 0, NOW(), NOW()),
(64, 'http://localhost:8890/api/expenses/{expense_id}', 'GET', NULL, 30000, 0, NOW(), NOW()),
(65, 'http://localhost:8890/api/expenses/{expense_id}', 'PUT', '{"Content-Type":"application/json"}', 30000, 0, NOW(), NOW()),
(66, 'http://localhost:8890/api/expenses/{expense_id}/approve', 'PUT', '{"Content-Type":"application/json"}', 30000, 0, NOW(), NOW()),
(67, 'http://localhost:8890/api/expenses/{expense_id}/reject', 'PUT', '{"Content-Type":"application/json"}', 30000, 0, NOW(), NOW()),
(68, 'http://localhost:8890/api/expenses/{expense_id}/cancel', 'PUT', NULL, 30000, 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

-- OA Service MCP 工具配置
INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, microservice_id, enabled, call_status, call_count, error_count, last_call_code, last_call_time, create_time, update_time)
VALUES
('gateway_002', 50, 'list_employees_api_employees_get', 'function', '获取员工列表。支持按部门ID、团队ID、状态、关键词筛选，支持分页', '1.0.0', 50, 'http', @oa_microservice_id, 1, 'sunny', 80, 3, '0000', NOW(), NOW(), NOW()),
('gateway_002', 51, 'create_employee_api_employees_post', 'function', '创建员工', '1.0.0', 51, 'http', @oa_microservice_id, 1, 'sunny', 25, 1, '0000', NOW(), NOW(), NOW()),
('gateway_002', 52, 'get_employee_api_employees__employee_id__get', 'function', '获取员工详情', '1.0.0', 52, 'http', @oa_microservice_id, 1, 'sunny', 45, 2, '0000', NOW(), NOW(), NOW()),
('gateway_002', 53, 'update_employee_api_employees__employee_id__put', 'function', '更新员工信息', '1.0.0', 53, 'http', @oa_microservice_id, 1, 'sunny', 20, 1, '0000', NOW(), NOW(), NOW()),
('gateway_002', 54, 'delete_employee_api_employees__employee_id__delete', 'function', '删除员工（软删除）', '1.0.0', 54, 'http', @oa_microservice_id, 1, 'cloudy', 10, 3, '4001', NOW(), NOW(), NOW()),
('gateway_002', 55, 'list_leaves_api_leaves_get', 'function', '获取请假列表。支持按申请人ID、状态、请假类型筛选，支持分页', '1.0.0', 55, 'http', @oa_microservice_id, 1, 'sunny', 60, 4, '0000', NOW(), NOW(), NOW()),
('gateway_002', 56, 'create_leave_api_leaves_post', 'function', '提交请假申请', '1.0.0', 56, 'http', @oa_microservice_id, 1, 'sunny', 30, 2, '0000', NOW(), NOW(), NOW()),
('gateway_002', 57, 'get_leave_api_leaves__leave_id__get', 'function', '获取请假详情', '1.0.0', 57, 'http', @oa_microservice_id, 1, 'sunny', 35, 1, '0000', NOW(), NOW(), NOW()),
('gateway_002', 58, 'update_leave_api_leaves__leave_id__put', 'function', '更新请假申请', '1.0.0', 58, 'http', @oa_microservice_id, 1, 'sunny', 15, 1, '0000', NOW(), NOW(), NOW()),
('gateway_002', 59, 'approve_leave_api_leaves__leave_id__approve_put', 'function', '审批通过请假申请', '1.0.0', 59, 'http', @oa_microservice_id, 1, 'cloudy', 25, 8, '4002', NOW(), NOW(), NOW()),
('gateway_002', 60, 'reject_leave_api_leaves__leave_id__reject_put', 'function', '审批拒绝请假申请', '1.0.0', 60, 'http', @oa_microservice_id, 1, 'cloudy', 18, 6, '4003', NOW(), NOW(), NOW()),
('gateway_002', 61, 'cancel_leave_api_leaves__leave_id__cancel_put', 'function', '撤销请假申请', '1.0.0', 61, 'http', @oa_microservice_id, 1, 'sunny', 12, 1, '0000', NOW(), NOW(), NOW()),
('gateway_002', 62, 'list_expenses_api_expenses_get', 'function', '获取报销列表。支持按申请人ID、状态、报销类型筛选，支持分页', '1.0.0', 62, 'http', @oa_microservice_id, 1, 'sunny', 55, 3, '0000', NOW(), NOW(), NOW()),
('gateway_002', 63, 'create_expense_api_expenses_post', 'function', '提交报销申请', '1.0.0', 63, 'http', @oa_microservice_id, 1, 'sunny', 28, 2, '0000', NOW(), NOW(), NOW()),
('gateway_002', 64, 'get_expense_api_expenses__expense_id__get', 'function', '获取报销详情', '1.0.0', 64, 'http', @oa_microservice_id, 1, 'sunny', 40, 2, '0000', NOW(), NOW(), NOW()),
('gateway_002', 65, 'update_expense_api_expenses__expense_id__put', 'function', '更新报销申请', '1.0.0', 65, 'http', @oa_microservice_id, 1, 'sunny', 15, 1, '0000', NOW(), NOW(), NOW()),
('gateway_002', 66, 'approve_expense_api_expenses__expense_id__approve_put', 'function', '审批通过报销申请', '1.0.0', 66, 'http', @oa_microservice_id, 1, 'cloudy', 22, 7, '4004', NOW(), NOW(), NOW()),
('gateway_002', 67, 'reject_expense_api_expenses__expense_id__reject_put', 'function', '审批拒绝报销申请', '1.0.0', 67, 'http', @oa_microservice_id, 1, 'cloudy', 16, 5, '4005', NOW(), NOW(), NOW()),
('gateway_002', 68, 'cancel_expense_api_expenses__expense_id__cancel_put', 'function', '撤销报销申请', '1.0.0', 68, 'http', @oa_microservice_id, 1, 'sunny', 10, 1, '0000', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description), microservice_id = VALUES(microservice_id), call_count = VALUES(call_count), error_count = VALUES(error_count), call_status = VALUES(call_status);

-- OA Service 参数映射
INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES
-- list_employees (50)
(50, 'query', 'dept_id', 'integer', '部门ID', 0, 1, NOW(), NOW()),
(50, 'query', 'team_id', 'integer', '团队ID', 0, 2, NOW(), NOW()),
(50, 'query', 'status', 'integer', '状态', 0, 3, NOW(), NOW()),
(50, 'query', 'keyword', 'string', '搜索关键词', 0, 4, NOW(), NOW()),
(50, 'query', 'page', 'integer', '页码', 0, 5, NOW(), NOW()),
(50, 'query', 'page_size', 'integer', '每页数量', 0, 6, NOW(), NOW()),
-- create_employee (51) - body params from schema
(51, 'body', 'name', 'string', '姓名', 1, 1, NOW(), NOW()),
(51, 'body', 'employee_no', 'string', '工号', 1, 2, NOW(), NOW()),
(51, 'body', 'gender', 'integer', '性别: 1-男 2-女', 0, 3, NOW(), NOW()),
(51, 'body', 'phone', 'string', '手机号', 0, 4, NOW(), NOW()),
(51, 'body', 'email', 'string', '邮箱', 0, 5, NOW(), NOW()),
(51, 'body', 'dept_id', 'integer', '部门ID', 0, 6, NOW(), NOW()),
(51, 'body', 'team_id', 'integer', '团队ID', 0, 7, NOW(), NOW()),
(51, 'body', 'position', 'string', '职位', 0, 8, NOW(), NOW()),
(51, 'body', 'level', 'string', '职级', 0, 9, NOW(), NOW()),
-- get_employee (52)
(52, 'path', 'employee_id', 'integer', '员工ID', 1, 1, NOW(), NOW()),
-- update_employee (53)
(53, 'path', 'employee_id', 'integer', '员工ID', 1, 1, NOW(), NOW()),
-- delete_employee (54)
(54, 'path', 'employee_id', 'integer', '员工ID', 1, 1, NOW(), NOW()),
-- list_leaves (55)
(55, 'query', 'employee_id', 'integer', '申请人ID', 0, 1, NOW(), NOW()),
(55, 'query', 'status', 'integer', '状态', 0, 2, NOW(), NOW()),
(55, 'query', 'leave_type', 'integer', '请假类型', 0, 3, NOW(), NOW()),
(55, 'query', 'page', 'integer', '页码', 0, 4, NOW(), NOW()),
(55, 'query', 'page_size', 'integer', '每页数量', 0, 5, NOW(), NOW()),
-- create_leave (56)
(56, 'body', 'leave_type', 'integer', '请假类型: 1-年假 2-病假 3-事假 4-婚假 5-产假 6-陪产假 7-丧假', 1, 1, NOW(), NOW()),
(56, 'body', 'start_date', 'string', '开始日期', 1, 2, NOW(), NOW()),
(56, 'body', 'end_date', 'string', '结束日期', 1, 3, NOW(), NOW()),
(56, 'body', 'days', 'string', '请假天数', 1, 4, NOW(), NOW()),
(56, 'body', 'employee_id', 'integer', '申请人ID', 1, 5, NOW(), NOW()),
(56, 'body', 'employee_name', 'string', '申请人姓名', 1, 6, NOW(), NOW()),
(56, 'body', 'reason', 'string', '请假原因', 0, 7, NOW(), NOW()),
-- get_leave (57)
(57, 'path', 'leave_id', 'integer', '请假ID', 1, 1, NOW(), NOW()),
-- update_leave (58)
(58, 'path', 'leave_id', 'integer', '请假ID', 1, 1, NOW(), NOW()),
-- approve_leave (59)
(59, 'path', 'leave_id', 'integer', '请假ID', 1, 1, NOW(), NOW()),
(59, 'body', 'approver_id', 'integer', '审批人ID', 1, 2, NOW(), NOW()),
(59, 'body', 'approver_name', 'string', '审批人姓名', 1, 3, NOW(), NOW()),
(59, 'body', 'remark', 'string', '审批备注', 0, 4, NOW(), NOW()),
-- reject_leave (60)
(60, 'path', 'leave_id', 'integer', '请假ID', 1, 1, NOW(), NOW()),
(60, 'body', 'approver_id', 'integer', '审批人ID', 1, 2, NOW(), NOW()),
(60, 'body', 'approver_name', 'string', '审批人姓名', 1, 3, NOW(), NOW()),
(60, 'body', 'remark', 'string', '审批备注', 0, 4, NOW(), NOW()),
-- cancel_leave (61)
(61, 'path', 'leave_id', 'integer', '请假ID', 1, 1, NOW(), NOW()),
-- list_expenses (62)
(62, 'query', 'employee_id', 'integer', '申请人ID', 0, 1, NOW(), NOW()),
(62, 'query', 'status', 'integer', '状态', 0, 2, NOW(), NOW()),
(62, 'query', 'expense_type', 'integer', '报销类型', 0, 3, NOW(), NOW()),
(62, 'query', 'page', 'integer', '页码', 0, 4, NOW(), NOW()),
(62, 'query', 'page_size', 'integer', '每页数量', 0, 5, NOW(), NOW()),
-- create_expense (63)
(63, 'body', 'expense_type', 'integer', '报销类型: 1-差旅费 2-交通费 3-餐饮费 4-办公费 5-其他', 1, 1, NOW(), NOW()),
(63, 'body', 'amount', 'string', '报销金额', 1, 2, NOW(), NOW()),
(63, 'body', 'employee_id', 'integer', '申请人ID', 1, 3, NOW(), NOW()),
(63, 'body', 'employee_name', 'string', '申请人姓名', 1, 4, NOW(), NOW()),
(63, 'body', 'description', 'string', '报销说明', 0, 5, NOW(), NOW()),
-- get_expense (64)
(64, 'path', 'expense_id', 'integer', '报销ID', 1, 1, NOW(), NOW()),
-- update_expense (65)
(65, 'path', 'expense_id', 'integer', '报销ID', 1, 1, NOW(), NOW()),
-- approve_expense (66)
(66, 'path', 'expense_id', 'integer', '报销ID', 1, 1, NOW(), NOW()),
(66, 'body', 'approver_id', 'integer', '审批人ID', 1, 2, NOW(), NOW()),
(66, 'body', 'approver_name', 'string', '审批人姓名', 1, 3, NOW(), NOW()),
(66, 'body', 'remark', 'string', '审批备注', 0, 4, NOW(), NOW()),
-- reject_expense (67)
(67, 'path', 'expense_id', 'integer', '报销ID', 1, 1, NOW(), NOW()),
(67, 'body', 'approver_id', 'integer', '审批人ID', 1, 2, NOW(), NOW()),
(67, 'body', 'approver_name', 'string', '审批人姓名', 1, 3, NOW(), NOW()),
(67, 'body', 'remark', 'string', '审批备注', 0, 4, NOW(), NOW()),
-- cancel_expense (68)
(68, 'path', 'expense_id', 'integer', '报销ID', 1, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc);

-- =====================================================
-- 10. 网关-微服务绑定关系
-- =====================================================

-- 绑定 Product Service 到 gateway_001
INSERT INTO mcp_gateway_microservice (gateway_id, microservice_id, bind_time, status, create_time, update_time)
VALUES ('gateway_001', @microservice_id, NOW(), 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE status = VALUES(status);

-- 绑定 OA Service 到 gateway_002
INSERT INTO mcp_gateway_microservice (gateway_id, microservice_id, bind_time, status, create_time, update_time)
VALUES ('gateway_002', @oa_microservice_id, NOW(), 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE status = VALUES(status);

-- =====================================================
-- 11. 最终验证
-- =====================================================
SELECT '总用户数:' AS '', COUNT(*) FROM sys_user;
SELECT '总角色数:' AS '', COUNT(*) FROM sys_role;
SELECT '总业务线数:' AS '', COUNT(*) FROM sys_business_line;
SELECT '微服务数量:' AS '', COUNT(*) FROM mcp_microservice;
SELECT '工具数量:' AS '', COUNT(*) FROM mcp_gateway_tool WHERE gateway_id = 'gateway_001';
SELECT '网关-微服务绑定数:' AS '', COUNT(*) FROM mcp_gateway_microservice;
SELECT 'LLM配置数:' AS '', COUNT(*) FROM mcp_llm_config;
SELECT '网关-LLM绑定数:' AS '', COUNT(*) FROM mcp_gateway_llm;
