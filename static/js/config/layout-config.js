const LayoutConfig = {
    roles: {
        system_admin: {
            value: 'system_admin',
            label: '系统管理员',
            description: '负责系统基础运维、权限与参数配置',
            homePage: '/admin/index.html',
            allowRegister: false,
            dataScope: 'all'
        },
        platform_operator: {
            value: 'platform_operator',
            label: '平台运营',
            description: '负责全局数据运营与商品运营',
            homePage: '/admin/data-analytics.html',
            allowRegister: false,
            dataScope: 'all'
        },
        community_leader: {
            value: 'community_leader',
            label: '社区团长',
            description: '负责本社区商品经营、订单执行与经营分析',
            homePage: '/admin/supplier/sales-analytics.html',
            allowRegister: false,
            dataScope: 'self'
        },
        user: {
            value: 'user',
            label: '普通用户',
            description: '负责商品浏览、购买和订单查询',
            homePage: '/front/mall/mall.html',
            allowRegister: true,
            dataScope: 'self'
        }
    },

    frontMenu: [
        {
            index: 'mall',
            title: '商品浏览',
            path: '/front/mall/mall.html',
            icon: 'el-icon-s-goods',
            roles: ['user']
        },
        {
            index: 'cart',
            title: '购物车',
            path: '/front/mall/cart.html',
            icon: 'el-icon-shopping-cart-2',
            roles: ['user']
        },
        {
            index: 'orders',
            title: '我的订单',
            path: '/front/mall/orders.html',
            icon: 'el-icon-s-order',
            roles: ['user']
        },
        {
            index: 'profile',
            title: '个人中心',
            path: '/front/profile.html',
            icon: 'el-icon-user',
            roles: ['user']
        },
        {
            index: 'notifications',
            title: '消息通知',
            path: '/front/announcements.html',
            icon: 'el-icon-bell',
            roles: ['user']
        }
    ],

    adminMenu: [
        {
            index: 'system-dashboard',
            title: '系统总览',
            path: '/admin/index.html',
            icon: 'el-icon-s-home',
            roles: ['system_admin']
        },
        {
            index: 'user-permission',
            title: '用户与权限管理',
            path: '/admin/users.html',
            icon: 'el-icon-user-solid',
            roles: ['system_admin']
        },
        {
            index: 'community-leader-manage',
            title: '社区团长管理',
            path: '/admin/suppliers.html',
            icon: 'el-icon-office-building',
            roles: ['system_admin']
        },
        {
            index: 'system-config',
            title: '系统配置',
            path: '/admin/system-config.html',
            icon: 'el-icon-setting',
            roles: ['system_admin']
        },
        {
            index: 'operator-orders',
            title: '订单管理',
            path: '/admin/mall/mall-orders.html',
            icon: 'el-icon-s-order',
            roles: ['platform_operator']
        },
        {
            index: 'operator-data',
            title: '数据分析',
            path: '/admin/operation-report.html',
            icon: 'el-icon-coin',
            roles: ['platform_operator']
        },
        {
            index: 'operator-sales-forecast',
            title: '销量预测',
            path: '/admin/data-analytics.html',
            icon: 'el-icon-data-analysis',
            roles: ['platform_operator']
        },
{
            index: 'announcements',
            title: '消息公告',
            path: '/admin/announcements.html',
            icon: 'el-icon-chat-line-square',
            roles: ['system_admin', 'platform_operator', 'community_leader', 'supplier']
        },
        {
            index: 'complaints',
            title: '投诉管理',
            path: '/admin/complaints.html',
            icon: 'el-icon-warning',
            roles: ['platform_operator']
        },
        {
            index: 'community-analysis',
            title: '社区经营看板',
            path: '/admin/supplier/index.html',
            icon: 'el-icon-data-board',
            roles: ['community_leader', 'supplier']
        },
        {
            index: 'community-sales-forecast',
            title: '销量预测',
            path: '/admin/supplier/sales-analytics.html',
            icon: 'el-icon-data-analysis',
            roles: ['community_leader', 'supplier']
        },
        {
            index: 'community-smart-selection',
            title: '智能选品',
            path: '/admin/supplier/smart-selection.html',
            icon: 'el-icon-shopping-bag-1',
            roles: ['community_leader', 'supplier']
        },
        {
            index: 'community-orders',
            title: '订单管理',
            path: '/admin/mall/mall-orders.html',
            icon: 'el-icon-s-order',
            roles: ['community_leader', 'supplier']
        },
        {
            index: 'community-after-sale',
            title: '售后管理',
            path: '/admin/supplier/after-sale.html',
            icon: 'el-icon-warning-outline',
            roles: ['community_leader', 'supplier']
        },
        {
            index: 'community-complaints',
            title: '投诉管理',
            path: '/admin/complaints.html',
            icon: 'el-icon-warning',
            roles: ['community_leader', 'supplier']
        },
        {
            index: 'community-products',
            title: '社区商品',
            path: '/admin/supplier/products.html',
            icon: 'el-icon-s-management',
            roles: ['community_leader', 'supplier']
        },
        {
            index: 'community-purchase-orders',
            title: '采购订单',
            path: '/admin/supplier/purchase-orders.html',
            icon: 'el-icon-document-copy',
            roles: ['community_leader', 'supplier']
        },
        {
            index: 'profile',
            title: '个人中心',
            path: '/admin/profile.html',
            icon: 'el-icon-s-custom',
            roles: ['system_admin', 'platform_operator', 'community_leader', 'supplier']
        }
    ],

    system: {
        title: '社区团购管理系统',
        logo: '/static/image/logo.png',
        defaultAvatar: '/static/image/profile.png'
    },

    menuGroups: {
        front: {
            '购物功能': ['mall', 'cart', 'orders'],
            '服务中心': ['profile', 'notifications']
        },
        system_admin: {
            '系统运维': ['system-dashboard', 'user-permission', 'community-leader-manage'],
            '基础配置': ['system-config'],
            '个人设置': ['profile']
        },
        platform_operator: {
            '运营中台': ['operator-orders', 'operator-data', 'operator-sales-forecast'],
            '服务管理': ['complaints', 'announcements'],
            '个人设置': ['profile']
        },
        community_leader: {
            '社区经营': ['community-analysis', 'community-sales-forecast', 'community-smart-selection'],
            '采购仓储': ['community-purchase-orders', 'community-products'],
            '订单管理': ['community-orders'],
            '服务管理': ['announcements', 'community-after-sale', 'community-complaints'],
            '个人设置': ['profile']
        }
    }
};

LayoutConfig.utils = {
    getAllRoles: function() {
        return Object.values(LayoutConfig.roles);
    },

    getRegisterRoles: function() {
        return Object.values(LayoutConfig.roles).filter(function(role) {
            return role.allowRegister;
        });
    },

    getRoleByValue: function(roleValue) {
        return LayoutConfig.roles[roleValue] || null;
    },

    getRoleLabel: function(roleValue) {
        const role = this.getRoleByValue(roleValue);
        return role ? role.label : roleValue;
    },

    getRoleHomePage: function(roleValue) {
        const role = LayoutConfig.roles[roleValue];
        return role ? role.homePage : '/';
    },

    getRoleDataScope: function(roleValue) {
        const role = LayoutConfig.roles[roleValue];
        return role ? role.dataScope : 'self';
    },

    getMenuTypeByRole: function(userRole) {
        if (['system_admin', 'platform_operator', 'community_leader', 'supplier'].includes(userRole)) {
            return 'adminMenu';
        }
        if (userRole === 'user') {
            return 'frontMenu';
        }
        return 'frontMenu';
    },

    filterMenuByRole: function(menuType, userRole) {
        const menu = LayoutConfig[menuType];
        if (!menu || !userRole) {
            return [];
        }
        return menu.filter(function(item) {
            return item.roles && item.roles.includes(userRole);
        });
    },

    hasMenuPermission: function(menuType, menuIndex, userRole) {
        const menu = LayoutConfig[menuType];
        const menuItem = menu.find(function(item) {
            return item.index === menuIndex;
        });
        if (!menuItem) {
            return false;
        }
        return menuItem.roles && menuItem.roles.includes(userRole);
    },

    getMenuByGroup: function(menuType, groupName, userRole) {
        const menu = LayoutConfig[menuType];
        let groupType = 'system_admin';

        if (menuType === 'frontMenu') {
            groupType = 'front';
        } else if (userRole === 'platform_operator') {
            groupType = 'platform_operator';
        } else if (userRole === 'community_leader' || userRole === 'supplier') {
            groupType = 'community_leader';
        }

        const group = LayoutConfig.menuGroups[groupType][groupName];
        if (!group) {
            return [];
        }

        return menu.filter(function(item) {
            return group.includes(item.index);
        });
    },

    getActiveMenu: function(menuType, currentPath) {
        const menu = LayoutConfig[menuType];
        return menu.find(function(item) {
            return item.path === currentPath;
        });
    },

    getBreadcrumb: function(menuType, currentPath) {
        const menu = LayoutConfig[menuType];
        const currentItem = menu.find(function(item) {
            return item.path === currentPath;
        });
        return currentItem ? [currentItem] : [];
    },

    buildDataScopeCondition: function(userRole, userId, tableAlias) {
        const dataScope = this.getRoleDataScope(userRole);
        const prefix = tableAlias ? tableAlias + '.' : '';

        if (dataScope === 'all') {
            return '';
        }

        if (userRole === 'community_leader' || userRole === 'supplier') {
            return `${prefix}supplierId = ${userId}`;
        }

        return `${prefix}userId = ${userId}`;
    }
};

if (typeof window !== 'undefined') {
    window.LayoutConfig = LayoutConfig;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = LayoutConfig;
}
