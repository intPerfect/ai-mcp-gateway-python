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
DELETE FROM mcp_microservice WHERE name = 'Product Service';

-- =====================================================
-- 2. 插入微服务配置
-- =====================================================
INSERT INTO mcp_microservice (name, http_base_url, description, business_line, health_status, status, create_time, update_time)
VALUES ('Product Service', 'http://localhost:8778', '商品服务 - 提供商品、库存、订单、定价等核心功能', '电商业务', 'healthy', 1, NOW(), NOW())
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
(11, 'body', 'product_id', 'integer', '商品ID', 1, 1, NOW(), NOW()),
(11, 'body', 'quantity', 'integer', '预留数量', 1, 2, NOW(), NOW()),
(11, 'body', 'ttl_seconds', 'integer', '预留有效期(秒)，默认300', 0, 3, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc);

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
(22, 'body', 'code', 'string', '优惠券码', 1, 1, NOW(), NOW()),
(22, 'body', 'order_amount', 'number', '订单金额', 1, 2, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES 
(30, 'body', 'items', 'array', '订单商品', 1, 1, NOW(), NOW()),
(30, 'body', 'customer_name', 'string', '客户姓名', 0, 2, NOW(), NOW()),
(30, 'body', 'customer_phone', 'string', '客户电话', 0, 3, NOW(), NOW()),
(30, 'body', 'shipping_address', 'string', '收货地址', 0, 4, NOW(), NOW()),
(30, 'body', 'remark', 'string', '备注', 0, 5, NOW(), NOW()),
(30, 'body', 'payment_method', 'string', '支付方式', 0, 6, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES 
(31, 'query', 'status', 'string', '订单状态筛选', 0, 1, NOW(), NOW()),
(31, 'query', 'page', 'integer', '页码', 0, 2, NOW(), NOW()),
(31, 'query', 'page_size', 'integer', '每页数量', 0, 3, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES (32, 'path', 'order_no', 'string', '订单号', 1, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES 
(33, 'path', 'order_no', 'string', '订单号', 1, 0, NOW(), NOW()),
(33, 'body', 'payment_method', 'string', '支付方式', 1, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc);

INSERT INTO mcp_protocol_mapping (protocol_id, param_location, field_name, field_type, field_desc, is_required, sort_order, create_time, update_time)
VALUES 
(34, 'path', 'order_no', 'string', '订单号', 1, 0, NOW(), NOW()),
(34, 'body', 'reason', 'string', '取消原因', 0, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE field_desc = VALUES(field_desc);

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
