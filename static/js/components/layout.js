// 统一布局组件文件

// 前台布局组件
Vue.component('front-layout', {
    props: {
        activeMenu: {
            type: String,
            default: '1'
        }
    },
    data() {
        return {
            layoutConfig: window.LayoutConfig || LayoutConfig,
            userInfo: null,
            menuItems: LayoutConfig.frontMenu,
            systemConfig: LayoutConfig.system
        }
    },
    mounted() {
        this.checkAuth();
        this.setActiveMenu();
        
        // 监听用户信息更新事件
        window.addEventListener('userInfoUpdated', this.handleUserInfoUpdate);
    },
    beforeDestroy() {
        // 移除事件监听
        window.removeEventListener('userInfoUpdated', this.handleUserInfoUpdate);
    },
    methods: {
        checkAuth() {
            // 基于本地缓存检查登录状态
            const token = localStorage.getItem('token') || sessionStorage.getItem('token');
            const userInfo = localStorage.getItem('userInfo') || sessionStorage.getItem('userInfo');
            
            if (token && userInfo) {
                try {
                    this.userInfo = JSON.parse(userInfo);
                } catch (e) {
                    console.error('解析用户信息失败:', e);
                    this.userInfo = null;
                }
            } else {
                this.userInfo = null;
            }
        },
        setActiveMenu() {
            const path = window.location.pathname;
            // 更精确的路径匹配
            const menuItem = this.menuItems.find(item => {
                // 完全匹配路径
                if (path === item.path) return true;
                // 匹配路径的最后部分
                const pathParts = path.split('/');
                const itemPathParts = item.path.split('/');
                return pathParts[pathParts.length - 1] === itemPathParts[itemPathParts.length - 1];
            });
            if (menuItem) {
                this.$emit('update:activeMenu', menuItem.index);
            }
        },
        handleMenuClick(index) {
            const menuItem = this.menuItems.find(item => item.index === index);
            if (menuItem) {
                window.location.href = menuItem.path;
            }
        },
        handleLogout() {
            this.$confirm('确定要退出登录吗？', '提示', {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning'
            }).then(() => {
                // 清除所有本地缓存数据
                localStorage.removeItem('token');
                localStorage.removeItem('userInfo');
                sessionStorage.removeItem('token');
                sessionStorage.removeItem('userInfo');
                
                // 清除用户信息
                this.userInfo = null;
                
                this.$message.success('退出登录成功');
                window.location.href = '/login';
            });
        },
        handleCommand(command) {
            if (command === 'profile') {
                window.location.href = '/front/profile.html';
            } else if (command === 'admin') {
                const homePage = LayoutConfig.utils.getRoleHomePage(this.userInfo.role);
                window.location.href = homePage;
            } else if (command === 'orders') {
                window.location.href = '/front/mall/orders.html';
            }  else if (command === 'cart') {
                window.location.href = '/front/mall/cart.html';
            } else if (command === 'logout') {
                this.handleLogout();
            }
        },
        goToLogin() {
            window.location.href = '/login';
        },
        goToRegister() {
            window.location.href = '/register';
        },
        handleUserInfoUpdate(event) {
            // 更新用户信息
            this.userInfo = event.detail.userInfo;
        }
    },
    template: `
        <div id="front-layout" class="modern-front-layout">
            <!-- 顶部导航栏 - 新设计 -->
            <el-header class="modern-header">
                <div class="header-content">
                    <div class="logo-section">
                        <div class="logo-icon">
                            <i class="el-icon-shopping-bag-2"></i>
                        </div>
                        <h2 class="logo-text">{{ systemConfig.title }}</h2>
                    </div>
                    
                    <div class="nav-menu-modern">
                        <div 
                            v-for="item in menuItems" 
                            :key="item.index"
                            :class="['menu-item-modern', { 'is-active': activeMenu === item.index }]"
                            @click="handleMenuClick(item.index)">
                            <span class="menu-text">{{ item.title }}</span>
                            <div class="menu-indicator"></div>
                        </div>
                    </div>
                    
                    <div class="user-section" v-if="userInfo">
                        <theme-switcher></theme-switcher>
                        <el-dropdown @command="handleCommand" class="user-dropdown-modern">
                            <div class="user-info-card">
                                <el-avatar :src="userInfo.avatar || systemConfig.defaultAvatar" :size="36"></el-avatar>
                                <div class="user-details">
                                    <span class="user-name">{{ userInfo.nickname || userInfo.username }}</span>
                                    <i class="el-icon-caret-bottom"></i>
                                </div>
                            </div>
                            <el-dropdown-menu slot="dropdown" class="modern-dropdown">
                                <el-dropdown-item command="profile">
                                    <i class="el-icon-user"></i> 个人中心
                                </el-dropdown-item>
                                <el-dropdown-item command="cart">
                                    <i class="el-icon-shopping-cart-2"></i> 购物车
                                </el-dropdown-item>
                                <el-dropdown-item command="orders">
                                    <i class="el-icon-s-order"></i> 我的订单
                                </el-dropdown-item>
                                <el-dropdown-item v-if="userInfo.role !== 'user'" command="admin">
                                    <i class="el-icon-s-tools"></i> 后台管理
                                </el-dropdown-item>
                                <el-dropdown-item divided command="logout">
                                    <i class="el-icon-switch-button"></i> 退出登录
                                </el-dropdown-item>
                            </el-dropdown-menu>
                        </el-dropdown>
                    </div>
                    
                    <div class="auth-section" v-else>
                        <theme-switcher></theme-switcher>
                        <el-button class="login-btn-modern" @click="goToLogin">
                            <i class="el-icon-user"></i> 登录
                        </el-button>
                        <el-button class="register-btn-modern" type="primary" @click="goToRegister">
                            <i class="el-icon-plus"></i> 注册
                        </el-button>
                    </div>
                </div>
            </el-header>

            <!-- 主要内容区域 -->
            <div class="main-content">
                <slot></slot>
            </div>

            <!-- 底部 - 新设计 -->
            <el-footer class="modern-footer">
                <div class="footer-content">
                    <div class="footer-info">
                        <p class="copyright">&copy; 2030 {{ systemConfig.title }}. All rights reserved.</p>
                    </div>
                </div>
            </el-footer>
        </div>
    `
});

// 后台布局组件
Vue.component('admin-layout', {
    props: {
        activeMenu: {
            type: String,
            default: 'dashboard'
        }
    },
    data() {
        return {
            layoutConfig: window.LayoutConfig || LayoutConfig,
            userInfo: null,
            isCollapse: false,
            menuItems: [],
            systemConfig: LayoutConfig.system
        }
    },
    created() {
        // 根据用户角色加载对应的菜单
        this.loadMenuByRole();
    },
    mounted() {
        this.checkAuth();
        
        // 监听用户信息更新事件
        window.addEventListener('userInfoUpdated', this.handleUserInfoUpdate);
    },
    beforeDestroy() {
        // 移除事件监听
        window.removeEventListener('userInfoUpdated', this.handleUserInfoUpdate);
    },
    methods: {
        loadMenuByRole() {
            // 获取用户信息
            const userInfoStr = localStorage.getItem('userInfo') || sessionStorage.getItem('userInfo');
            if (userInfoStr) {
                try {
                    const userInfo = JSON.parse(userInfoStr);
                    const userRole = userInfo.role;
                    
                    // 根据角色过滤菜单
                    this.menuItems = LayoutConfig.utils.filterMenuByRole('adminMenu', userRole);
                } catch (e) {
                    console.error('解析用户信息失败:', e);
                    this.menuItems = LayoutConfig.adminMenu;
                }
            } else {
                this.menuItems = LayoutConfig.adminMenu;
            }
        },
        checkAuth() {
            // 基于本地缓存检查登录状态
            const token = localStorage.getItem('token') || sessionStorage.getItem('token');
            const userInfo = localStorage.getItem('userInfo') || sessionStorage.getItem('userInfo');
            
            if (token && userInfo) {
                try {
                    this.userInfo = JSON.parse(userInfo);
                } catch (e) {
                    console.error('解析用户信息失败:', e);
                    this.userInfo = null;
                }
            } else {
                this.userInfo = null;
            }
        },
        handleMenuClick(index) {
            const menuItem = this.menuItems.find(item => item.index === index);
            if (menuItem) {
                window.location.href = menuItem.path;
            }
        },
        handleLogout() {
            this.$confirm('确定要退出登录吗？', '提示', {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning'
            }).then(() => {
                // 清除所有本地缓存数据
                localStorage.removeItem('token');
                localStorage.removeItem('userInfo');
                sessionStorage.removeItem('token');
                sessionStorage.removeItem('userInfo');
                
                // 清除用户信息
                this.userInfo = null;
                
                this.$message.success('退出登录成功');
                window.location.href = '/login';
            });
        },
        toggleCollapse() {
            this.isCollapse = !this.isCollapse;
        },
        handleCommand(command) {
            if (command === 'profile') {
                window.location.href = '/admin/profile.html';
            } else if (command === 'front') {
                window.location.href = '/front/mall/mall.html';
            } else if (command === 'logout') {
                this.handleLogout();
            }
        },
        handleUserInfoUpdate(event) {
            // 更新用户信息
            this.userInfo = event.detail.userInfo;
        }
    },
    template: `
        <el-container class="modern-admin-container">
            <!-- 左侧菜单 - 新设计 -->
            <el-aside :width="isCollapse ? '80px' : '260px'" class="modern-sidebar">
                <div class="sidebar-header">
                    <div class="logo-wrapper" v-if="!isCollapse">
                        <div class="logo-icon-admin">
                            <i class="el-icon-s-platform"></i>
                        </div>
                        <div class="logo-text-wrapper">
                            <h3 class="logo-title">{{ systemConfig.title }}</h3>
                            <span class="logo-subtitle">管理后台</span>
                        </div>
                    </div>
                    <div class="logo-icon-collapsed" v-else>
                        <i class="el-icon-s-platform"></i>
                    </div>
                </div>
                
                <div class="menu-wrapper">
                    <div 
                        v-for="item in menuItems" 
                        :key="item.index"
                        :class="['menu-item-admin', { 'is-active': activeMenu === item.index }]"
                        @click="handleMenuClick(item.index)">
                        <div class="menu-item-content">
                            <div class="menu-icon-box">
                                <i :class="item.icon"></i>
                            </div>
                            <span class="menu-title" v-if="!isCollapse">{{ item.title }}</span>
                            <div class="active-bar"></div>
                        </div>
                    </div>
                </div>
                
                <div class="sidebar-footer">
                    <el-button 
                        :icon="isCollapse ? 'el-icon-s-unfold' : 'el-icon-s-fold'"
                        class="collapse-btn-modern"
                        @click="toggleCollapse">
                        <span v-if="!isCollapse">收起菜单</span>
                    </el-button>
                </div>
            </el-aside>

            <!-- 主要内容区域 -->
            <el-container class="main-container">
                <!-- 顶部导航栏 - 新设计 -->
                <el-header class="modern-admin-header">
                    <div class="header-left">
                        <div class="breadcrumb-wrapper">
                            <i class="el-icon-location-outline"></i>
                            <el-breadcrumb separator="/">
                                <el-breadcrumb-item>首页</el-breadcrumb-item>
                                <el-breadcrumb-item>{{ menuItems.find(item => item.index === activeMenu)?.title || '页面' }}</el-breadcrumb-item>
                            </el-breadcrumb>
                        </div>
                    </div>
                    
                    <div class="header-right">
                        <el-dropdown @command="handleCommand" class="admin-user-dropdown">
                            <div class="admin-user-card">
                                <el-avatar :src="userInfo && userInfo.avatar ? userInfo.avatar : systemConfig.defaultAvatar" :size="38"></el-avatar>
                                <div class="admin-user-info">
                                    <span class="admin-username">{{ userInfo && userInfo.nickname ? userInfo.nickname : '用户' }}</span>
                                    <span class="admin-role">{{ userInfo ? layoutConfig.utils.getRoleLabel(userInfo.role) : '后台用户' }}</span>
                                </div>
                                <i class="el-icon-caret-bottom"></i>
                            </div>
                            <el-dropdown-menu slot="dropdown" class="admin-dropdown-menu">
                                <el-dropdown-item command="profile">
                                    <i class="el-icon-user"></i> 个人中心
                                </el-dropdown-item>
                                <el-dropdown-item command="front">
                                    <i class="el-icon-s-home"></i> 前台首页
                                </el-dropdown-item>
                                <el-dropdown-item divided command="logout">
                                    <i class="el-icon-switch-button"></i> 退出登录
                                </el-dropdown-item>
                            </el-dropdown-menu>
                        </el-dropdown>
                    </div>
                </el-header>

                <!-- 内容区域 -->
                <el-main class="modern-admin-main">
                    <slot name="content"></slot>
                </el-main>
            </el-container>
        </el-container>
    `
});
