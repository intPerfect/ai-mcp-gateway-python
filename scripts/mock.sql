-- -*- coding: utf-8 -*-
-- MCP Gateway 数据库初始化脚本 - Product Service Mock数据

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;
USE ai_mcp_gateway_v2;

-- =====================================================
-- 1. 清理现有数据
-- =====================================================
DELETE FROM mcp_protocol_mapping WHERE protocol_id IN (SELECT protocol_id FROM mcp_protocol_http WHERE http_url LIKE '%localhost:8778%');
DELETE FROM mcp_gateway_tool WHERE gateway_id = 'gateway_001' AND protocol_type = 'http';
DELETE FROM mcp_protocol_http WHERE http_url LIKE '%localhost:8778%';

-- =====================================================
-- 2. 插入Product Service的HTTP协议配置
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
-- 3. 插入MCP工具配置 (无status字段)
-- =====================================================

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 2, 'get_all_products', 'function', '获取所有商品列表，返回商品ID、名称、价格、库存等信息', '1.0.0', 2, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 3, 'get_product_by_id', 'function', '根据ID获取单个商品详情', '1.0.0', 3, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 4, 'search_products', 'function', '搜索商品，支持关键词、分类、状态筛选、价格区间、排序', '1.0.0', 1, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 5, 'get_categories', 'function', '获取所有商品分类', '1.0.0', 7, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 6, 'get_category_by_id', 'function', '根据ID获取分类详情', '1.0.0', 8, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 7, 'compare_products', 'function', '商品比价，批量查询多个商品的详细信息并按价格排序', '1.0.0', 4, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 8, 'get_alternatives', 'function', '获取商品的替代推荐（同分类或相似价格）', '1.0.0', 5, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 9, 'get_trending_products', 'function', '获取热销商品榜单', '1.0.0', 6, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 10, 'check_inventory', 'function', '检查商品库存状态，包括可用数量、预留情况', '1.0.0', 10, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 11, 'reserve_inventory', 'function', '预留库存，带TTL有效期，防止超卖', '1.0.0', 11, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 12, 'release_reservation', 'function', '释放库存预留', '1.0.0', 12, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 13, 'confirm_reservation', 'function', '确认库存预留，扣减实际库存', '1.0.0', 13, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 20, 'calculate_price', 'function', '计算商品最终价格，支持会员折扣、优惠券', '1.0.0', 20, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 21, 'get_coupon_info', 'function', '获取优惠券信息，校验是否有效', '1.0.0', 21, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 22, 'apply_coupon', 'function', '试算优惠券应用后的价格', '1.0.0', 22, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 23, 'get_member_levels', 'function', '获取会员等级列表及折扣率', '1.0.0', 23, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 30, 'create_order', 'function', '创建订单，支持使用库存预留', '1.0.0', 30, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 31, 'list_orders', 'function', '查询订单列表，支持状态、日期筛选', '1.0.0', 31, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 32, 'get_order', 'function', '获取订单详情', '1.0.0', 32, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 33, 'pay_order', 'function', '模拟支付订单', '1.0.0', 33, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 34, 'cancel_order', 'function', '取消订单，自动释放库存', '1.0.0', 34, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 40, 'get_sales_stats', 'function', '销售统计，支持按时间、分类筛选', '1.0.0', 40, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 41, 'get_low_stock_alert', 'function', '低库存预警，库存低于阈值时提醒', '1.0.0', 41, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 42, 'get_recommendations', 'function', '获取商品推荐，基于销量和库存', '1.0.0', 42, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

INSERT INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type, create_time, update_time)
VALUES ('gateway_001', 43, 'get_category_stats', 'function', '获取各分类的销售统计', '1.0.0', 43, 'http', NOW(), NOW())
ON DUPLICATE KEY UPDATE tool_description = VALUES(tool_description);

-- =====================================================
-- 4. 插入参数映射
-- =====================================================

INSERT INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order, create_time, update_time)
VALUES 
(1, 'request', NULL, 'keyword', 'keyword', 'string', '搜索关键词', 0, 1, NOW(), NOW()),
(1, 'request', NULL, 'category_id', 'category_id', 'integer', '分类ID筛选', 0, 2, NOW(), NOW()),
(1, 'request', NULL, 'min_price', 'min_price', 'number', '最低价格', 0, 3, NOW(), NOW()),
(1, 'request', NULL, 'max_price', 'max_price', 'number', '最高价格', 0, 4, NOW(), NOW()),
(1, 'request', NULL, 'in_stock_only', 'in_stock_only', 'boolean', '仅显示有货', 0, 5, NOW(), NOW()),
(1, 'request', NULL, 'sort_by', 'sort_by', 'string', '排序方式(relevance/price_asc/price_desc/stock)', 0, 6, NOW(), NOW()),
(1, 'request', NULL, 'page', 'page', 'integer', '页码', 0, 7, NOW(), NOW()),
(1, 'request', NULL, 'page_size', 'page_size', 'integer', '每页数量', 0, 8, NOW(), NOW())
ON DUPLICATE KEY UPDATE mcp_desc = VALUES(mcp_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order, create_time, update_time)
VALUES (3, 'request', NULL, 'product_id', 'product_id', 'integer', '商品ID', 1, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE mcp_desc = VALUES(mcp_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order, create_time, update_time)
VALUES (8, 'request', NULL, 'category_id', 'category_id', 'integer', '分类ID', 1, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE mcp_desc = VALUES(mcp_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order, create_time, update_time)
VALUES (4, 'request', NULL, 'product_ids', 'product_ids', 'array', '商品ID数组，最多10个', 1, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE mcp_desc = VALUES(mcp_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order, create_time, update_time)
VALUES 
(5, 'request', NULL, 'product_id', 'product_id', 'integer', '商品ID', 1, 1, NOW(), NOW()),
(5, 'request', NULL, 'limit', 'limit', 'integer', '返回数量，默认5', 0, 2, NOW(), NOW())
ON DUPLICATE KEY UPDATE mcp_desc = VALUES(mcp_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order, create_time, update_time)
VALUES 
(6, 'request', NULL, 'category_id', 'category_id', 'integer', '分类ID筛选', 0, 1, NOW(), NOW()),
(6, 'request', NULL, 'limit', 'limit', 'integer', '返回数量，默认10', 0, 2, NOW(), NOW())
ON DUPLICATE KEY UPDATE mcp_desc = VALUES(mcp_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order, create_time, update_time)
VALUES 
(11, 'request', NULL, 'product_id', 'product_id', 'integer', '商品ID', 1, 1, NOW(), NOW()),
(11, 'request', NULL, 'quantity', 'quantity', 'integer', '预留数量', 1, 2, NOW(), NOW()),
(11, 'request', NULL, 'ttl_seconds', 'ttl_seconds', 'integer', '预留有效期(秒)，默认300', 0, 3, NOW(), NOW())
ON DUPLICATE KEY UPDATE mcp_desc = VALUES(mcp_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order, create_time, update_time)
VALUES (12, 'request', NULL, 'reservation_id', 'reservation_id', 'string', '预留ID', 1, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE mcp_desc = VALUES(mcp_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order, create_time, update_time)
VALUES (13, 'request', NULL, 'reservation_id', 'reservation_id', 'string', '预留ID', 1, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE mcp_desc = VALUES(mcp_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order, create_time, update_time)
VALUES 
(20, 'request', NULL, 'items', 'items', 'array', '商品列表 [{"product_id":1,"quantity":2}]', 1, 1, NOW(), NOW()),
(20, 'request', NULL, 'member_level', 'member_level', 'string', '会员等级(normal/silver/gold/platinum/diamond)', 0, 2, NOW(), NOW()),
(20, 'request', NULL, 'coupon_code', 'coupon_code', 'string', '优惠券码', 0, 3, NOW(), NOW())
ON DUPLICATE KEY UPDATE mcp_desc = VALUES(mcp_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order, create_time, update_time)
VALUES (21, 'request', NULL, 'code', 'code', 'string', '优惠券码', 1, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE mcp_desc = VALUES(mcp_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order, create_time, update_time)
VALUES 
(22, 'request', NULL, 'code', 'code', 'string', '优惠券码', 1, 1, NOW(), NOW()),
(22, 'request', NULL, 'order_amount', 'order_amount', 'number', '订单金额', 1, 2, NOW(), NOW())
ON DUPLICATE KEY UPDATE mcp_desc = VALUES(mcp_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order, create_time, update_time)
VALUES 
(30, 'request', NULL, 'items', 'items', 'array', '订单商品', 1, 1, NOW(), NOW()),
(30, 'request', NULL, 'customer_name', 'customer_name', 'string', '客户姓名', 0, 2, NOW(), NOW()),
(30, 'request', NULL, 'customer_phone', 'customer_phone', 'string', '客户电话', 0, 3, NOW(), NOW()),
(30, 'request', NULL, 'shipping_address', 'shipping_address', 'string', '收货地址', 0, 4, NOW(), NOW()),
(30, 'request', NULL, 'remark', 'remark', 'string', '备注', 0, 5, NOW(), NOW()),
(30, 'request', NULL, 'payment_method', 'payment_method', 'string', '支付方式', 0, 6, NOW(), NOW())
ON DUPLICATE KEY UPDATE mcp_desc = VALUES(mcp_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order, create_time, update_time)
VALUES 
(31, 'request', NULL, 'status', 'status', 'string', '订单状态筛选', 0, 1, NOW(), NOW()),
(31, 'request', NULL, 'page', 'page', 'integer', '页码', 0, 2, NOW(), NOW()),
(31, 'request', NULL, 'page_size', 'page_size', 'integer', '每页数量', 0, 3, NOW(), NOW())
ON DUPLICATE KEY UPDATE mcp_desc = VALUES(mcp_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order, create_time, update_time)
VALUES (32, 'request', NULL, 'order_no', 'order_no', 'string', '订单号', 1, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE mcp_desc = VALUES(mcp_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order, create_time, update_time)
VALUES (33, 'request', NULL, 'payment_method', 'payment_method', 'string', '支付方式', 1, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE mcp_desc = VALUES(mcp_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order, create_time, update_time)
VALUES (34, 'request', NULL, 'reason', 'reason', 'string', '取消原因', 0, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE mcp_desc = VALUES(mcp_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order, create_time, update_time)
VALUES 
(40, 'request', NULL, 'start_date', 'start_date', 'string', '开始日期', 0, 1, NOW(), NOW()),
(40, 'request', NULL, 'end_date', 'end_date', 'string', '结束日期', 0, 2, NOW(), NOW()),
(40, 'request', NULL, 'category_id', 'category_id', 'integer', '分类ID', 0, 3, NOW(), NOW())
ON DUPLICATE KEY UPDATE mcp_desc = VALUES(mcp_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order, create_time, update_time)
VALUES (41, 'request', NULL, 'threshold', 'threshold', 'integer', '库存预警阈值', 0, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE mcp_desc = VALUES(mcp_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order, create_time, update_time)
VALUES 
(42, 'request', NULL, 'category_id', 'category_id', 'integer', '分类ID', 0, 1, NOW(), NOW()),
(42, 'request', NULL, 'limit', 'limit', 'integer', '返回数量', 0, 2, NOW(), NOW())
ON DUPLICATE KEY UPDATE mcp_desc = VALUES(mcp_desc);

-- =====================================================
-- 5. 验证
-- =====================================================
SELECT '工具数量:' AS '', COUNT(*) FROM mcp_gateway_tool WHERE gateway_id = 'gateway_001';
SELECT '协议数量:' AS '', COUNT(*) FROM mcp_protocol_http WHERE http_url LIKE '%localhost:8778%';
