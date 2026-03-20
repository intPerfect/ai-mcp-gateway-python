-- -*- coding: utf-8 -*-
-- MCP Gateway 数据库初始化脚本 - Product Service Mock数据
-- 运行前请确保数据库已创建

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;
USE ai_mcp_gateway_v2;

-- =====================================================
-- 1. 清理现有数据（可选，保留用于重新初始化）
-- =====================================================
-- DELETE FROM mcp_protocol_mapping WHERE protocol_id IN (SELECT id FROM mcp_protocol_http WHERE http_url LIKE '%localhost:8778%');
-- DELETE FROM mcp_gateway_tool WHERE gateway_id = 'gateway_001' AND protocol_type = 'http';
-- DELETE FROM mcp_protocol_http WHERE http_url LIKE '%localhost:8778%';

-- =====================================================
-- 2. 插入Product Service的HTTP协议配置
-- =====================================================

-- 商品管理协议 (protocol_id = 1)
INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, status, create_time, update_time)
VALUES (1, 'http://localhost:8778/api/products', 'GET', NULL, 30000, 0, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url), http_method = VALUES(http_method);

-- 商品列表-全部协议 (protocol_id = 2)
INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, status, create_time, update_time)
VALUES (2, 'http://localhost:8778/api/products/all', 'GET', NULL, 30000, 0, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

-- 商品详情协议 (protocol_id = 3)
INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, status, create_time, update_time)
VALUES (3, 'http://localhost:8778/api/products/{product_id}', 'GET', NULL, 30000, 0, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

-- 商品搜索协议 (protocol_id = 4)
INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, status, create_time, update_time)
VALUES (4, 'http://localhost:8778/api/products', 'GET', NULL, 30000, 0, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

-- 分类列表协议 (protocol_id = 5)
INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, status, create_time, update_time)
VALUES (5, 'http://localhost:8778/api/categories', 'GET', NULL, 30000, 0, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

-- 分类详情协议 (protocol_id = 6)
INSERT INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, status, create_time, update_time)
VALUES (6, 'http://localhost:8778/api/categories/{category_id}', 'GET', NULL, 30000, 0, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE http_url = VALUES(http_url);

-- =====================================================
-- 3. 插入MCP工具配置
-- =====================================================

-- 获取所有商品
INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 2, 'get_all_products', 'function', '获取所有商品列表，返回商品ID、名称、价格、库存等信息', '1.0.0', 2, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

-- 按ID获取商品
INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 3, 'get_product_by_id', 'function', '根据ID获取单个商品详情', '1.0.0', 3, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

-- 搜索商品
INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 4, 'search_products', 'function', '搜索商品，支持关键词、分类、状态筛选', '1.0.0', 4, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

-- 获取所有分类
INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 5, 'get_categories', 'function', '获取所有商品分类', '1.0.0', 5, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

-- 获取分类详情
INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 6, 'get_category_by_id', 'function', '根据ID获取分类详情', '1.0.0', 6, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

-- =====================================================
-- 4. 插入参数映射
-- =====================================================

-- search_products 参数映射 (protocol_id = 4)
INSERT INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order, create_time, update_time)
VALUES 
(4, 'request', NULL, 'keyword', 'keyword', 'string', '搜索关键词', 0, 1, NOW(), NOW()),
(4, 'request', NULL, 'category_id', 'category_id', 'integer', '分类ID筛选', 0, 2, NOW(), NOW()),
(4, 'request', NULL, 'status', 'status', 'integer', '商品状态筛选(0下架1上架2售罄)', 0, 3, NOW(), NOW()),
(4, 'request', NULL, 'page', 'page', 'integer', '页码', 0, 4, NOW(), NOW()),
(4, 'request', NULL, 'page_size', 'page_size', 'integer', '每页数量', 0, 5, NOW(), NOW())
ON DUPLICATE KEY UPDATE mcp_desc = VALUES(mcp_desc);

-- get_product_by_id 参数映射 (protocol_id = 3)
INSERT INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order, create_time, update_time)
VALUES (3, 'request', NULL, 'product_id', 'product_id', 'integer', '商品ID', 1, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE mcp_desc = VALUES(mcp_desc);

-- get_category_by_id 参数映射 (protocol_id = 6)
INSERT INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order, create_time, update_time)
VALUES (6, 'request', NULL, 'category_id', 'category_id', 'integer', '分类ID', 1, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE mcp_desc = VALUES(mcp_desc);

-- =====================================================
-- 5. 验证数据
-- =====================================================
SELECT '工具列表:' AS '';
SELECT id, gateway_id, tool_name, tool_description, protocol_id FROM mcp_gateway_tool WHERE gateway_id = 'gateway_001';

SELECT '协议配置:' AS '';
SELECT id, http_url, http_method, timeout FROM mcp_protocol_http WHERE id IN (2, 3, 4, 5, 6);

SELECT '参数映射:' AS '';
SELECT protocol_id, field_name, mcp_path, mcp_type, is_required FROM mcp_protocol_mapping WHERE protocol_id IN (3, 4, 6);
