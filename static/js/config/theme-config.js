// 主题配色配置文件
const ThemeConfig = {
    // 默认主题 - 红色主题
    default: {
        name: '温暖橙色',
        colors: {
            primary: '#f59e0b',
            secondary: '#d97706',
            success: '#10b981',
            warning: '#f59e0b',
            danger: '#ef4444',
            info: '#64748b',
            text: '#1f2937',
            textLight: '#6b7280',
            textLighter: '#9ca3af',
            background: '#fffbeb',
            white: '#ffffff'
        },
        gradients: {
            background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
            header: 'linear-gradient(90deg, #f59e0b 0%, #d97706 100%)',
            button: 'linear-gradient(45deg, #f59e0b 0%, #d97706 100%)',
            card: 'linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.9) 100%)'
        }
    },
    
    // 清新绿色主题
    green: {
        name: '清新绿色',
        colors: {
            primary: '#10b981',
            secondary: '#059669',
            success: '#10b981',
            warning: '#f59e0b',
            danger: '#ef4444',
            info: '#64748b',
            text: '#1f2937',
            textLight: '#6b7280',
            textLighter: '#9ca3af',
            background: '#f0fdf4',
            white: '#ffffff'
        },
        gradients: {
            background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
            header: 'linear-gradient(90deg, #10b981 0%, #059669 100%)',
            button: 'linear-gradient(45deg, #10b981 0%, #059669 100%)',
            card: 'linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.9) 100%)'
        }
    },
    
    // 温暖橙色主题
    orange: {
        name: '温暖橙色',
        colors: {
            primary: '#f59e0b',
            secondary: '#d97706',
            success: '#10b981',
            warning: '#f59e0b',
            danger: '#ef4444',
            info: '#64748b',
            text: '#1f2937',
            textLight: '#6b7280',
            textLighter: '#9ca3af',
            background: '#fffbeb',
            white: '#ffffff'
        },
        gradients: {
            background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
            header: 'linear-gradient(90deg, #f59e0b 0%, #d97706 100%)',
            button: 'linear-gradient(45deg, #f59e0b 0%, #d97706 100%)',
            card: 'linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.9) 100%)'
        }
    },
    
    // 优雅紫色主题
    purple: {
        name: '优雅紫色',
        colors: {
            primary: '#8b5cf6',
            secondary: '#7c3aed',
            success: '#10b981',
            warning: '#f59e0b',
            danger: '#ef4444',
            info: '#64748b',
            text: '#1f2937',
            textLight: '#6b7280',
            textLighter: '#9ca3af',
            background: '#faf5ff',
            white: '#ffffff'
        },
        gradients: {
            background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
            header: 'linear-gradient(90deg, #8b5cf6 0%, #7c3aed 100%)',
            button: 'linear-gradient(45deg, #8b5cf6 0%, #7c3aed 100%)',
            card: 'linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.9) 100%)'
        }
    },
    
    // 商务蓝色主题
    business: {
        name: '商务蓝色',
        colors: {
            primary: '#2563eb',
            secondary: '#1d4ed8',
            success: '#10b981',
            warning: '#f59e0b',
            danger: '#ef4444',
            info: '#64748b',
            text: '#1f2937',
            textLight: '#6b7280',
            textLighter: '#9ca3af',
            background: '#eff6ff',
            white: '#ffffff'
        },
        gradients: {
            background: 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)',
            header: 'linear-gradient(90deg, #2563eb 0%, #1d4ed8 100%)',
            button: 'linear-gradient(45deg, #2563eb 0%, #1d4ed8 100%)',
            card: 'linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.9) 100%)'
        }
    },
    
    // 简约灰色主题
    minimal: {
        name: '简约灰色',
        colors: {
            primary: '#6b7280',
            secondary: '#4b5563',
            success: '#10b981',
            warning: '#f59e0b',
            danger: '#ef4444',
            info: '#64748b',
            text: '#1f2937',
            textLight: '#6b7280',
            textLighter: '#9ca3af',
            background: '#f9fafb',
            white: '#ffffff'
        },
        gradients: {
            background: 'linear-gradient(135deg, #6b7280 0%, #4b5563 100%)',
            header: 'linear-gradient(90deg, #6b7280 0%, #4b5563 100%)',
            button: 'linear-gradient(45deg, #6b7280 0%, #4b5563 100%)',
            card: 'linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.9) 100%)'
        }
    }
};

// 主题管理器
class ThemeManager {
    constructor() {
        this.currentTheme = localStorage.getItem('theme') || 'default';
        this.init();
    }
    
    init() {
        this.applyTheme(this.currentTheme);
    }
    
    // 应用主题
    applyTheme(themeName) {
        const theme = ThemeConfig[themeName];
        if (!theme) {
            console.warn(`主题 ${themeName} 不存在，使用默认主题`);
            themeName = 'default';
            theme = ThemeConfig.default;
        }
        
        this.currentTheme = themeName;
        localStorage.setItem('theme', themeName);
        
        // 应用CSS变量
        const root = document.documentElement;
        const colors = theme.colors;
        const gradients = theme.gradients;
        
        // 设置颜色变量
        Object.keys(colors).forEach(key => {
            root.style.setProperty(`--theme-${key}`, colors[key]);
        });
        
        // 设置渐变变量
        Object.keys(gradients).forEach(key => {
            root.style.setProperty(`--theme-gradient-${key}`, gradients[key]);
        });
        
        // 触发主题变更事件
        window.dispatchEvent(new CustomEvent('themeChanged', {
            detail: { theme: themeName, config: theme }
        }));
    }
    
    // 获取当前主题
    getCurrentTheme() {
        return this.currentTheme;
    }
    
    // 获取所有可用主题
    getAvailableThemes() {
        return Object.keys(ThemeConfig).map(key => ({
            key,
            name: ThemeConfig[key].name
        }));
    }
    
    // 切换主题
    switchTheme(themeName) {
        this.applyTheme(themeName);
    }
}

// 创建全局主题管理器实例
window.themeManager = new ThemeManager();

// 导出配置
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ThemeConfig, ThemeManager };
}
