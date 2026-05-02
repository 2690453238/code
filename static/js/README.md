# 布局组件说明

## 文件结构

```
static/js/
├── config/
│   └── layout-config.js    # 统一布局配置文件
├── components/
│   └── layout.js          # 统一布局组件文件
└── README.md              # 说明文档
```

## 配置文件 (layout-config.js)

### 前台菜单配置
```javascript
frontMenu: [
    {
        index: '1',
        title: '首页',
        path: '/front/index.html',
        icon: 'el-icon-s-home'
    },
    // ... 更多菜单项
]
```

### 后台菜单配置
```javascript
adminMenu: [
    {
        index: 'dashboard',
        title: '仪表盘',
        path: '/admin/index.html',
        icon: 'el-icon-s-home'
    },
    // ... 更多菜单项
]
```

### 系统配置
```javascript
system: {
    title: '通用管理系统',
    logo: '/static/image/logo.png',
    defaultAvatar: '/static/image/profile.png'
}
```

## 使用方法

### 前台页面
```html
<!DOCTYPE html>
<html>
<head>
    <!-- 引入必要的CSS和JS -->
    <script src="/static/js/config/layout-config.js"></script>
    <script src="/static/js/components/layout.js"></script>
</head>
<body>
    <div id="app">
        <front-layout :active-menu="activeMenu">
            <!-- 页面内容 -->
        </front-layout>
    </div>
    
    <script>
        new Vue({
            el: '#app',
            data() {
                return {
                    activeMenu: '1'  // 当前激活的菜单项
                }
            }
        });
    </script>
</body>
</html>
```

### 后台页面
```html
<!DOCTYPE html>
<html>
<head>
    <!-- 引入必要的CSS和JS -->
    <script src="/static/js/config/layout-config.js"></script>
    <script src="/static/js/components/layout.js"></script>
</head>
<body>
    <div id="app">
        <admin-layout :active-menu="activeMenu">
            <template #content>
                <!-- 页面内容 -->
            </template>
        </admin-layout>
    </div>
    
    <script>
        new Vue({
            el: '#app',
            data() {
                return {
                    activeMenu: 'dashboard'  // 当前激活的菜单项
                }
            }
        });
    </script>
</body>
</html>
```

## 组件特性

### 前台布局组件 (front-layout)
- 顶部导航栏
- 水平菜单
- 用户信息下拉菜单
- 登录/注册按钮
- 底部版权信息

### 后台布局组件 (admin-layout)
- 左侧可折叠菜单
- 顶部导航栏
- 面包屑导航
- 用户信息下拉菜单
- 权限检查

## 配置说明

### 添加新菜单项
1. 在 `layout-config.js` 中的相应菜单数组中添加新项
2. 确保 `index` 唯一
3. 设置正确的 `path` 和 `icon`

### 修改系统配置
在 `layout-config.js` 的 `system` 对象中修改：
- `title`: 系统标题
- `logo`: 系统Logo路径
- `defaultAvatar`: 默认头像路径

## 注意事项

1. 确保在页面中先引入 `layout-config.js`，再引入 `layout.js`
2. 前台和后台的菜单配置是独立的，可以分别定制
3. 所有路径都使用绝对路径，以 `/` 开头
4. 图标使用 Element UI 的图标类名
