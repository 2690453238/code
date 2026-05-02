-- 仓库表
CREATE TABLE IF NOT EXISTS `py_warehouse` (
    `id` int(11) NOT NULL AUTO_INCREMENT COMMENT 'ID',
    `supplierId` int(11) NOT NULL COMMENT '社区团长ID',
    `productId` int(11) NOT NULL COMMENT '商品ID',
    `productName` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '商品名称',
    `quantity` int(11) NOT NULL DEFAULT 0 COMMENT '库存数量',
    `costPrice` decimal(10, 2) DEFAULT NULL COMMENT '进价',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`) USING BTREE,
    UNIQUE KEY `uk_supplier_product` (`supplierId`, `productId`),
    KEY `idx_supplierId` (`supplierId`)
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '仓库表' ROW_FORMAT = Dynamic;

-- 采购订单表
CREATE TABLE IF NOT EXISTS `py_purchase_order` (
    `id` int(11) NOT NULL AUTO_INCREMENT COMMENT 'ID',
    `orderNo` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '订单编号',
    `supplierId` int(11) NOT NULL COMMENT '社区团长ID',
    `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'draft' COMMENT '状态: draft-草稿, confirmed-已确认, paid-已支付, cancelled-已取消',
    `totalCost` decimal(10, 2) NOT NULL DEFAULT 0.00 COMMENT '总费用（按进价）',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`) USING BTREE,
    KEY `idx_supplierId` (`supplierId`),
    KEY `idx_status` (`status`)
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '采购订单表' ROW_FORMAT = Dynamic;

-- 采购订单明细表
CREATE TABLE IF NOT EXISTS `py_purchase_order_item` (
    `id` int(11) NOT NULL AUTO_INCREMENT COMMENT 'ID',
    `orderId` int(11) NOT NULL COMMENT '采购订单ID',
    `productId` int(11) NOT NULL COMMENT '商品ID',
    `productName` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '商品名称',
    `quantity` int(11) NOT NULL COMMENT '采购数量',
    `costPrice` decimal(10, 2) DEFAULT NULL COMMENT '进价',
    `subtotal` decimal(10, 2) DEFAULT NULL COMMENT '小计',
    PRIMARY KEY (`id`) USING BTREE,
    KEY `idx_orderId` (`orderId`)
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '采购订单明细表' ROW_FORMAT = Dynamic;

-- 供应商折扣表（团长对滞销商品设置的折扣）
CREATE TABLE IF NOT EXISTS `py_supplier_discount` (
    `id` int(11) NOT NULL AUTO_INCREMENT COMMENT 'ID',
    `supplierId` int(11) NOT NULL COMMENT '社区团长ID',
    `productId` int(11) NOT NULL COMMENT '商品ID',
    `discountRate` decimal(3, 2) NOT NULL COMMENT '折扣率 0.00~1.00',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`) USING BTREE,
    UNIQUE KEY `uk_supplier_product` (`supplierId`, `productId`),
    KEY `idx_supplierId` (`supplierId`)
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '供应商折扣表' ROW_FORMAT = Dynamic;
