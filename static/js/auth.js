// 认证工具类
const Auth = {
    // 检查是否已登录
    isLoggedIn() {
        return localStorage.getItem('token') !== null;
    },

    // 获取用户信息
    getUserInfo() {
        const userInfo = localStorage.getItem('userInfo');
        return userInfo ? JSON.parse(userInfo) : null;
    },

    // 设置用户信息
    setUserInfo(userInfo) {
        localStorage.setItem('userInfo', JSON.stringify(userInfo));
    },

    // 清除用户信息
    clearUserInfo() {
        localStorage.removeItem('token');
        localStorage.removeItem('userInfo');
    },

    // 检查用户权限
    hasRole(role) {
        const userInfo = this.getUserInfo();
        return userInfo && userInfo.role === role;
    },

    // 检查是否为管理员
    isAdmin() {
        return this.hasRole('system_admin');
    },

    // 检查是否为平台运营者
    isPlatformOperator() {
        return this.hasRole('platform_operator');
    },

    // 检查是否为社区团长
    isCommunityLeader() {
        return this.hasRole('community_leader');
    },

    // 检查是否为普通用户
    isUser() {
        return this.hasRole('user');
    },

    // 检查是否有后台权限
    hasAdminAccess() {
        return this.isAdmin() || this.isPlatformOperator() || this.isCommunityLeader();
    },

    // 获取角色名称
    getRoleName(role) {
        const roleMap = {
            'system_admin': '系统管理员',
            'platform_operator': '平台运营者',
            'community_leader': '社区团长',
            'user': '普通用户'
        };
        return roleMap[role] || role;
    },

    // 格式化时间
    formatTime(timeStr) {
        if (!timeStr) return '';
        const date = new Date(timeStr);
        return date.toLocaleString();
    },

    // 格式化日期
    formatDate(timeStr) {
        if (!timeStr) return '';
        const date = new Date(timeStr);
        return date.toLocaleDateString();
    }
};

// 请求拦截器
axios.interceptors.request.use(
    config => {
        // 添加认证头
        const token = localStorage.getItem('token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    error => {
        return Promise.reject(error);
    }
);

// 响应拦截器
axios.interceptors.response.use(
    response => {
        return response;
    },
    error => {
        if (error.response) {
            // 401 未授权，跳转到登录页
            if (error.response.status === 401) {
                Auth.clearUserInfo();
                window.location.href = '/login';
            }
            // 403 权限不足
            if (error.response.status === 403) {
                Vue.prototype.$message.error('权限不足');
            }
        }
        return Promise.reject(error);
    }
);
