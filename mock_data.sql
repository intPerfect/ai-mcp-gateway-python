-- ============================================================
-- MCP Gateway Mock Data
-- Product Service APIs as MCP Tools
-- ============================================================

-- Gateway
INSERT IGNORE INTO mcp_gateway (gateway_id, gateway_name, gateway_desc, version, auth, status)
VALUES ('gateway_001', '商品服务网关', '对接 product-service 的 MCP 网关', '1.0.0', 0, 1);

-- Gateway Auth Key
INSERT IGNORE INTO mcp_gateway_auth (gateway_id, api_key, rate_limit, expire_time, status)
VALUES ('gateway_001', 'gw-test-api-key-001', 10000, '2099-12-31 23:59:59', 1);

-- ============================================================
-- Tools & Protocol HTTP configs
-- product-service base: http://localhost:8888
-- ============================================================

-- Tool 1: list_products (GET /api/products)
INSERT IGNORE INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type)
VALUES ('gateway_001', 1001, 'list_products', 'function', '查询商品列表，支持关键词搜索、分类筛选、状态筛选和分页', '1.0.0', 1001, 'http');

INSERT IGNORE INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, status)
VALUES (1001, 'http://localhost:8888/api/products', 'GET', NULL, 10000, 0, 1);

INSERT IGNORE INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order)
VALUES
(1001, 'request', NULL, 'keyword',   'keyword',   'string',  '搜索关键词（商品名称/SKU/描述）', 0, 1),
(1001, 'request', NULL, 'category_id','category_id','integer', '分类ID',                        0, 2),
(1001, 'request', NULL, 'status',    'status',    'integer', '商品状态: 0-下架 1-上架 2-售罄',  0, 3),
(1001, 'request', NULL, 'page',      'page',      'integer', '页码，从1开始',                   0, 4),
(1001, 'request', NULL, 'page_size', 'page_size', 'integer', '每页数量，最大100',               0, 5);

-- Tool 2: get_product (GET /api/products/{product_id})
INSERT IGNORE INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type)
VALUES ('gateway_001', 1002, 'get_product', 'function', '根据商品ID获取单个商品详情', '1.0.0', 1002, 'http');

INSERT IGNORE INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, status)
VALUES (1002, 'http://localhost:8888/api/products/1', 'GET', NULL, 10000, 0, 1);

INSERT IGNORE INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order)
VALUES
(1002, 'request', NULL, 'product_id', 'product_id', 'integer', '商品ID', 1, 1);

-- Tool 3: list_all_products (GET /api/products/all)
INSERT IGNORE INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type)
VALUES ('gateway_001', 1003, 'list_all_products', 'function', '获取所有上架商品列表（不分页，适合汇总查询）', '1.0.0', 1003, 'http');

INSERT IGNORE INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, status)
VALUES (1003, 'http://localhost:8888/api/products/all', 'GET', NULL, 10000, 0, 1);

-- Tool 4: create_product (POST /api/products)
INSERT IGNORE INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type)
VALUES ('gateway_001', 1004, 'create_product', 'function', '创建新商品', '1.0.0', 1004, 'http');

INSERT IGNORE INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, status)
VALUES (1004, 'http://localhost:8888/api/products', 'POST', '{"Content-Type": "application/json"}', 10000, 0, 1);

INSERT IGNORE INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order)
VALUES
(1004, 'request', NULL, 'sku',         'sku',         'string',  '商品SKU（唯一）',   1, 1),
(1004, 'request', NULL, 'name',        'name',        'string',  '商品名称',          1, 2),
(1004, 'request', NULL, 'price',       'price',       'number',  '销售价格',          1, 3),
(1004, 'request', NULL, 'stock',       'stock',       'integer', '库存数量',          1, 4),
(1004, 'request', NULL, 'description', 'description', 'string',  '商品描述',          0, 5),
(1004, 'request', NULL, 'cost',        'cost',        'number',  '成本价格',          0, 6),
(1004, 'request', NULL, 'category_id', 'category_id', 'integer', '分类ID',            0, 7),
(1004, 'request', NULL, 'image_url',   'image_url',   'string',  '商品图片URL',       0, 8);

-- Tool 5: update_product (PUT /api/products/{product_id})
INSERT IGNORE INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type)
VALUES ('gateway_001', 1005, 'update_product', 'function', '更新商品信息', '1.0.0', 1005, 'http');

INSERT IGNORE INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, status)
VALUES (1005, 'http://localhost:8888/api/products/1', 'PUT', '{"Content-Type": "application/json"}', 10000, 0, 1);

INSERT IGNORE INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order)
VALUES
(1005, 'request', NULL, 'product_id',  'product_id',  'integer', '商品ID',   1, 1),
(1005, 'request', NULL, 'name',        'name',        'string',  '商品名称', 0, 2),
(1005, 'request', NULL, 'price',       'price',       'number',  '销售价格', 0, 3),
(1005, 'request', NULL, 'stock',       'stock',       'integer', '库存数量', 0, 4),
(1005, 'request', NULL, 'description', 'description', 'string',  '商品描述', 0, 5),
(1005, 'request', NULL, 'status',      'status',      'integer', '商品状态: 0-下架 1-上架 2-售罄', 0, 6);

-- Tool 6: delete_product (DELETE /api/products/{product_id})
INSERT IGNORE INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type)
VALUES ('gateway_001', 1006, 'delete_product', 'function', '删除指定商品', '1.0.0', 1006, 'http');

INSERT IGNORE INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, status)
VALUES (1006, 'http://localhost:8888/api/products/1', 'DELETE', NULL, 10000, 0, 1);

INSERT IGNORE INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order)
VALUES
(1006, 'request', NULL, 'product_id', 'product_id', 'integer', '商品ID', 1, 1);

-- Tool 7: update_stock (PATCH /api/products/{product_id}/stock)
INSERT IGNORE INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type)
VALUES ('gateway_001', 1007, 'update_stock', 'function', '更新商品库存数量', '1.0.0', 1007, 'http');

INSERT IGNORE INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, status)
VALUES (1007, 'http://localhost:8888/api/products/1/stock', 'PATCH', NULL, 10000, 0, 1);

INSERT IGNORE INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order)
VALUES
(1007, 'request', NULL, 'product_id', 'product_id', 'integer', '商品ID',   1, 1),
(1007, 'request', NULL, 'stock',      'stock',      'integer', '新库存数量', 1, 2);

-- Tool 8: update_product_status (PATCH /api/products/{product_id}/status)
INSERT IGNORE INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type)
VALUES ('gateway_001', 1008, 'update_product_status', 'function', '更新商品上下架状态', '1.0.0', 1008, 'http');

INSERT IGNORE INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, status)
VALUES (1008, 'http://localhost:8888/api/products/1/status', 'PATCH', NULL, 10000, 0, 1);

INSERT IGNORE INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order)
VALUES
(1008, 'request', NULL, 'product_id', 'product_id', 'integer', '商品ID',                       1, 1),
(1008, 'request', NULL, 'status',     'status',     'integer', '状态: 0-下架 1-上架 2-售罄',    1, 2);

-- Tool 9: list_categories (GET /api/categories)
INSERT IGNORE INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type)
VALUES ('gateway_001', 1009, 'list_categories', 'function', '获取所有商品分类列表', '1.0.0', 1009, 'http');

INSERT IGNORE INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, status)
VALUES (1009, 'http://localhost:8888/api/categories', 'GET', NULL, 10000, 0, 1);

-- Tool 10: create_category (POST /api/categories)
INSERT IGNORE INTO mcp_gateway_tool (gateway_id, tool_id, tool_name, tool_type, tool_description, tool_version, protocol_id, protocol_type)
VALUES ('gateway_001', 1010, 'create_category', 'function', '创建新商品分类', '1.0.0', 1010, 'http');

INSERT IGNORE INTO mcp_protocol_http (protocol_id, http_url, http_method, http_headers, timeout, retry_times, status)
VALUES (1010, 'http://localhost:8888/api/categories', 'POST', '{"Content-Type": "application/json"}', 10000, 0, 1);

INSERT IGNORE INTO mcp_protocol_mapping (protocol_id, mapping_type, parent_path, field_name, mcp_path, mcp_type, mcp_desc, is_required, sort_order)
VALUES
(1010, 'request', NULL, 'name',        'name',        'string',  '分类名称',     1, 1),
(1010, 'request', NULL, 'description', 'description', 'string',  '分类描述',     0, 2),
(1010, 'request', NULL, 'parent_id',   'parent_id',   'integer', '父分类ID',     0, 3),
(1010, 'request', NULL, 'sort_order',  'sort_order',  'integer', '排序权重',     0, 4);
