from typing import Dict, List, Optional

from service.mall.product_service import ProductService as BaseProductService


class ProductService(BaseProductService):
    """修正版商品服务：按社区团长账号隔离商品数据"""

    GLOBAL_ROLES = {'system_admin', 'platform_operator'}

    def _get_supplier_scope_id(self, user_info: Optional[Dict]) -> Optional[int]:
        if not user_info:
            return None
        if user_info.get('role') in self.GLOBAL_ROLES:
            return None
        if user_info.get('role') == 'community_leader':
            return user_info.get('id')
        return None

    def get_products(
        self,
        category_id: int = None,
        status: int = None,
        page: int = 1,
        limit: int = 10,
        keyword: str = None,
        sort_type: str = 'default',
        user_info: Optional[Dict] = None
    ) -> Dict:
        supplier_id = self._get_supplier_scope_id(user_info)
        return super().get_products(category_id, status, page, limit, keyword, sort_type) \
            if supplier_id is None else self._get_products_scoped(category_id, status, page, limit, keyword, sort_type, supplier_id)

    def _get_products_scoped(self, category_id, status, page, limit, keyword, sort_type, supplier_id):
        result = self.product_model.get_products(category_id, status, page, limit, keyword, sort_type, supplier_id)
        from utils.response import page_response
        return page_response(result['rows'], result['total'], result['page'], result['limit'])

    def create_product(self, product_data: Dict, user_info: Optional[Dict] = None) -> Dict:
        supplier_id = self._get_supplier_scope_id(user_info)
        if supplier_id is not None:
            product_data['supplierId'] = supplier_id
        return super().create_product(product_data)

    def update_product(self, product_id: int, product_data: Dict, user_info: Optional[Dict] = None) -> Dict:
        from utils.response import success, error
        try:
            supplier_id = self._get_supplier_scope_id(user_info)
            result = self.product_model.update_product(product_id, product_data, supplier_id)
            if result:
                return success(None, "商品更新成功")
            return error("商品更新失败或无权限")
        except Exception:
            return error("更新商品失败")

    def delete_product(self, product_id: int, user_info: Optional[Dict] = None) -> Dict:
        from utils.response import success, error
        try:
            supplier_id = self._get_supplier_scope_id(user_info)
            result = self.product_model.delete_product(product_id, supplier_id)
            if result:
                return success(None, "商品删除成功")
            return error("商品删除失败或无权限")
        except Exception:
            return error("删除商品失败")

    def update_product_status(self, product_id: int, status: int, user_info: Optional[Dict] = None) -> Dict:
        from utils.response import success, error
        try:
            supplier_id = self._get_supplier_scope_id(user_info)
            result = self.product_model.update_product_status(product_id, status, supplier_id)
            if result:
                status_text = "上架" if status == 1 else "下架"
                return success(None, f"商品{status_text}成功")
            return error("商品状态更新失败或无权限")
        except Exception:
            return error("更新商品状态失败")

    def batch_delete_products(self, product_ids: List[int], user_info: Optional[Dict] = None) -> Dict:
        from utils.response import success, error
        try:
            supplier_id = self._get_supplier_scope_id(user_info)
            result = self.product_model.batch_delete_products(product_ids, supplier_id)
            if result:
                return success(None, f"成功删除{len(product_ids)}个商品")
            return error("批量删除商品失败或无权限")
        except Exception:
            return error("批量删除商品失败")
