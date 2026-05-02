/**
 * 富文本编辑器组件
 * 可复用的富文本编辑器组件，支持多种配置选项
 * 
 * 使用方法：
 * const editor = new RichEditor({
 *     container: '#editor-container',
 *     placeholder: '请输入内容...',
 *     height: 300,
 *     toolbar: ['bold', 'italic', 'underline', 'link', 'image'],
 *     onChange: function(content) {
 *         console.log('内容变化:', content);
 *     }
 * });
 */

class RichEditor {
    constructor(options = {}) {
        this.options = {
            container: options.container || '#rich-editor',
            placeholder: options.placeholder || '请输入内容...',
            height: options.height || 300,
            toolbar: options.toolbar || [
                ['bold', 'italic', 'underline'],
                ['link', 'image'],
                [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                ['blockquote', 'code-block'],
                [{ 'header': [1, 2, 3, false] }],
                [{ 'color': [] }, { 'background': [] }],
                [{ 'align': [] }],
                ['clean']
            ],
            onChange: options.onChange || function() {},
            onReady: options.onReady || function() {},
            value: options.value || '',
            readonly: options.readonly || false
        };
        
        this.editor = null;
        this.container = null;
        this.isInitialized = false;
        
        this.init();
    }
    
    /**
     * 初始化编辑器
     */
    init() {
        try {
            this.container = document.querySelector(this.options.container);
            if (!this.container) {
                console.error('富文本编辑器容器未找到:', this.options.container);
                return;
            }
            
            this.createEditorHTML();
            this.initQuill();
            this.bindEvents();
            this.isInitialized = true;
            
            // 触发就绪回调
            if (typeof this.options.onReady === 'function') {
                this.options.onReady(this);
            }
        } catch (error) {
            console.error('富文本编辑器初始化失败:', error);
        }
    }
    
    /**
     * 创建编辑器HTML结构
     */
    createEditorHTML() {
        this.container.innerHTML = `
            <div class="rich-editor-wrapper">
                <div class="rich-editor-toolbar"></div>
                <div class="rich-editor-content"></div>
            </div>
        `;
        
        // 设置样式
        this.container.style.height = this.options.height + 'px';
        this.container.classList.add('rich-editor-container');
    }
    
    /**
     * 初始化Quill编辑器
     */
    initQuill() {
        if (typeof Quill === 'undefined') {
            console.error('Quill编辑器未加载，请确保已引入quill.min.js');
            return;
        }
        
        const contentDiv = this.container.querySelector('.rich-editor-content');
        
        this.editor = new Quill(contentDiv, {
            placeholder: this.options.placeholder,
            readOnly: this.options.readonly,
            theme: 'snow',
            modules: {
                toolbar: {
                    container: this.options.toolbar,
                    handlers: {
                        image: this.imageHandler.bind(this)
                    }
                }
            }
        });
        
        // 设置初始内容
        if (this.options.value) {
            this.setContent(this.options.value);
        }
    }
    
    /**
     * 绑定事件
     */
    bindEvents() {
        if (!this.editor) return;
        
        // 内容变化事件
        this.editor.on('text-change', (delta, oldDelta, source) => {
            if (source === 'user') {
                const content = this.getContent();
                if (typeof this.options.onChange === 'function') {
                    this.options.onChange(content, delta, oldDelta);
                }
            }
        });
        
        // 选择变化事件
        this.editor.on('selection-change', (range, oldRange, source) => {
            if (typeof this.options.onSelectionChange === 'function') {
                this.options.onSelectionChange(range, oldRange, source);
            }
        });
    }
    
    /**
     * 图片上传处理器
     */
    imageHandler() {
        const input = document.createElement('input');
        input.setAttribute('type', 'file');
        input.setAttribute('accept', 'image/*');
        input.style.display = 'none';
        
        input.addEventListener('change', () => {
            const file = input.files[0];
            if (file) {
                this.uploadImage(file);
            }
        });
        
        document.body.appendChild(input);
        input.click();
        document.body.removeChild(input);
    }
    
    /**
     * 上传图片到服务器
     * @param {File} file - 图片文件
     */
    uploadImage(file) {
        // 验证文件类型
        if (!file.type.startsWith('image/')) {
            this.showMessage('请选择图片文件', 'error');
            return;
        }
        
        // 验证文件大小 (5MB)
        if (file.size > 5 * 1024 * 1024) {
            this.showMessage('图片大小不能超过5MB', 'error');
            return;
        }
        
        const formData = new FormData();
        formData.append('file', file);
        
        // 显示上传进度
        this.showMessage('正在上传图片...', 'info');
        
        // 调用后端上传接口
        fetch('/open/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.code === 200) {
                // 上传成功，插入图片到编辑器
                const range = this.editor.getSelection();
                this.editor.insertEmbed(range.index, 'image', data.data.url);
                this.editor.setSelection(range.index + 1);
                this.showMessage('图片上传成功', 'success');
            } else {
                this.showMessage(data.message || '图片上传失败', 'error');
            }
        })
        .catch(error => {
            console.error('图片上传失败:', error);
            this.showMessage('图片上传失败，请重试', 'error');
        });
    }
    
    /**
     * 显示消息提示
     * @param {string} message - 消息内容
     * @param {string} type - 消息类型 (success, error, info)
     */
    showMessage(message, type = 'info') {
        // 如果页面有Element UI的消息组件，使用它
        if (typeof Vue !== 'undefined' && Vue.prototype.$message) {
            Vue.prototype.$message[type](message);
        } else {
            // 否则使用原生alert
            alert(message);
        }
    }
    
    /**
     * 获取编辑器内容
     * @param {string} format - 返回格式 ('html', 'text', 'delta')
     * @returns {string|Object} 编辑器内容
     */
    getContent(format = 'html') {
        if (!this.editor) return '';
        
        switch (format) {
            case 'html':
                return this.editor.root.innerHTML;
            case 'text':
                return this.editor.getText();
            case 'delta':
                return this.editor.getContents();
            default:
                return this.editor.root.innerHTML;
        }
    }
    
    /**
     * 设置编辑器内容
     * @param {string|Object} content - 内容
     * @param {string} format - 内容格式 ('html', 'text', 'delta')
     */
    setContent(content, format = 'html') {
        if (!this.editor) return;
        
        try {
            switch (format) {
                case 'html':
                    this.editor.root.innerHTML = content;
                    break;
                case 'text':
                    this.editor.setText(content);
                    break;
                case 'delta':
                    this.editor.setContents(content);
                    break;
                default:
                    this.editor.root.innerHTML = content;
            }
        } catch (error) {
            console.error('设置编辑器内容失败:', error);
        }
    }
    
    /**
     * 清空编辑器内容
     */
    clear() {
        if (!this.editor) return;
        this.editor.setContents([]);
    }
    
    /**
     * 设置编辑器为只读模式
     * @param {boolean} readonly - 是否只读
     */
    setReadOnly(readonly) {
        if (!this.editor) return;
        this.editor.enable(!readonly);
    }
    
    /**
     * 获取编辑器实例
     * @returns {Object} Quill编辑器实例
     */
    getEditor() {
        return this.editor;
    }
    
    /**
     * 销毁编辑器
     */
    destroy() {
        if (this.editor) {
            this.editor = null;
        }
        if (this.container) {
            this.container.innerHTML = '';
        }
        this.isInitialized = false;
    }
    
    /**
     * 重新初始化编辑器
     * @param {Object} newOptions - 新的配置选项
     */
    reinit(newOptions = {}) {
        this.destroy();
        this.options = { ...this.options, ...newOptions };
        this.init();
    }
    
    /**
     * 插入文本
     * @param {string} text - 要插入的文本
     * @param {Object} attributes - 文本属性
     */
    insertText(text, attributes = {}) {
        if (!this.editor) return;
        
        const range = this.editor.getSelection();
        if (range) {
            this.editor.insertText(range.index, text, attributes);
        } else {
            this.editor.insertText(0, text, attributes);
        }
    }
    
    /**
     * 插入HTML
     * @param {string} html - 要插入的HTML
     */
    insertHTML(html) {
        if (!this.editor) return;
        
        const range = this.editor.getSelection();
        if (range) {
            this.editor.clipboard.dangerouslyPasteHTML(range.index, html);
        } else {
            this.editor.clipboard.dangerouslyPasteHTML(0, html);
        }
    }
    
    /**
     * 格式化选中文本
     * @param {string} format - 格式名称
     * @param {*} value - 格式值
     */
    format(format, value) {
        if (!this.editor) return;
        this.editor.format(format, value);
    }
    
    /**
     * 获取选中文本的格式
     * @returns {Object} 格式信息
     */
    getFormat() {
        if (!this.editor) return {};
        return this.editor.getFormat();
    }
    
    /**
     * 聚焦编辑器
     */
    focus() {
        if (!this.editor) return;
        this.editor.focus();
    }
    
    /**
     * 失焦编辑器
     */
    blur() {
        if (!this.editor) return;
        this.editor.blur();
    }
}

// 导出组件
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RichEditor;
} else if (typeof window !== 'undefined') {
    window.RichEditor = RichEditor;
}