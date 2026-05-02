-- 为商品表添加进价字段
ALTER TABLE `py_product`
    ADD COLUMN `costPrice` decimal(10, 2) DEFAULT NULL COMMENT '进价' AFTER `price`;

-- 为已有商品设置进价（进价 = 售价 × 4/5）
UPDATE `py_product`
SET `costPrice` = ROUND(`price` * 4 / 5, 2)
WHERE `costPrice` IS NULL;
