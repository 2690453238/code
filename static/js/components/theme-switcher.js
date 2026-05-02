// 主题切换组件
Vue.component('theme-switcher', {
    data() {
        return {
            currentTheme: 'default',
            availableThemes: [],
            showThemeList: false
        }
    },
    mounted() {
        this.initTheme();
        this.loadAvailableThemes();
        
        // 监听主题变更事件
        window.addEventListener('themeChanged', this.handleThemeChanged);
    },
    beforeDestroy() {
        window.removeEventListener('themeChanged', this.handleThemeChanged);
    },
    methods: {
        initTheme() {
            this.currentTheme = window.themeManager ? window.themeManager.getCurrentTheme() : 'default';
        },
        loadAvailableThemes() {
            if (window.themeManager) {
                this.availableThemes = window.themeManager.getAvailableThemes();
            }
        },
        handleThemeChanged(event) {
            this.currentTheme = event.detail.theme;
        },
        switchTheme(themeKey) {
            if (window.themeManager) {
                window.themeManager.switchTheme(themeKey);
                this.currentTheme = themeKey;
                this.showThemeList = false;
                this.$message.success(`已切换到${this.getThemeName(themeKey)}`);
            }
        },
        getThemeName(themeKey) {
            const theme = this.availableThemes.find(t => t.key === themeKey);
            return theme ? theme.name : themeKey;
        },
        toggleThemeList() {
            this.showThemeList = !this.showThemeList;
        }
    },
    template: `
        <div class="theme-switcher">
            <el-button 
                type="text" 
                @click="toggleThemeList"
                class="theme-trigger">
                <i class="el-icon-brush"></i>
                <span>主题</span>
                <i class="el-icon-arrow-down el-icon--right"></i>
            </el-button>
            
            <el-dropdown 
                v-show="showThemeList"
                @command="switchTheme"
                placement="bottom-end"
                trigger="click">
                <span class="theme-dropdown-trigger"></span>
                <el-dropdown-menu slot="dropdown">
                    <el-dropdown-item 
                        v-for="theme in availableThemes"
                        :key="theme.key"
                        :command="theme.key"
                        :class="{ 'is-active': currentTheme === theme.key }">
                        <i class="el-icon-check" v-if="currentTheme === theme.key"></i>
                        {{ theme.name }}
                    </el-dropdown-item>
                </el-dropdown-menu>
            </el-dropdown>
        </div>
    `
});

// 主题预览组件
Vue.component('theme-preview', {
    props: {
        themeKey: {
            type: String,
            required: true
        },
        themeName: {
            type: String,
            required: true
        }
    },
    data() {
        return {
            isActive: false
        }
    },
    mounted() {
        this.checkActive();
        window.addEventListener('themeChanged', this.handleThemeChanged);
    },
    beforeDestroy() {
        window.removeEventListener('themeChanged', this.handleThemeChanged);
    },
    methods: {
        checkActive() {
            this.isActive = window.themeManager ? 
                window.themeManager.getCurrentTheme() === this.themeKey : false;
        },
        handleThemeChanged(event) {
            this.isActive = event.detail.theme === this.themeKey;
        },
        applyTheme() {
            if (window.themeManager) {
                window.themeManager.switchTheme(this.themeKey);
            }
        }
    },
    template: `
        <div 
            class="theme-preview"
            :class="{ 'is-active': isActive }"
            @click="applyTheme">
            <div class="theme-preview-header">
                <div class="theme-preview-title">{{ themeName }}</div>
                <i class="el-icon-check" v-if="isActive"></i>
            </div>
            <div class="theme-preview-colors">
                <div 
                    class="color-swatch"
                    :style="{ backgroundColor: getThemeColor('primary') }">
                </div>
                <div 
                    class="color-swatch"
                    :style="{ backgroundColor: getThemeColor('secondary') }">
                </div>
                <div 
                    class="color-swatch"
                    :style="{ backgroundColor: getThemeColor('success') }">
                </div>
            </div>
        </div>
    `,
    methods: {
        ...Vue.component('theme-preview').methods,
        getThemeColor(colorKey) {
            // 这里可以根据主题配置返回对应的颜色
            const colorMap = {
                'default': { primary: '#667eea', secondary: '#764ba2', success: '#10b981' },
                'green': { primary: '#10b981', secondary: '#059669', success: '#10b981' },
                'orange': { primary: '#f59e0b', secondary: '#d97706', success: '#10b981' },
                'purple': { primary: '#8b5cf6', secondary: '#7c3aed', success: '#10b981' },
                'business': { primary: '#2563eb', secondary: '#1d4ed8', success: '#10b981' },
                'minimal': { primary: '#6b7280', secondary: '#4b5563', success: '#10b981' }
            };
            return colorMap[this.themeKey] ? colorMap[this.themeKey][colorKey] : '#667eea';
        }
    }
});
