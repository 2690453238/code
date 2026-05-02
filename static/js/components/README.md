# 富文本编辑器组件

基于 Quill.js 构建的可复用富文本编辑器组件，支持多种配置选项和丰富的功能。

## 快速开始

### 1. 引入依赖

```html
<!-- Quill.js 富文本编辑器 -->
<link href="https://cdn.quilljs.com/1.3.6/quill.snow.css" rel="stylesheet">
<script src="https://cdn.quilljs.com/1.3.6/quill.min.js"></script>
<!-- 富文本编辑器组件样式 -->
<link rel="stylesheet" href="/static/css/rich-editor.css">
<!-- 富文本编辑器组件 -->
<script src="/static/js/components/rich-editor.js"></script>
```

### 2. 创建编辑器

```html
<div id="editor" style="height: 300px;"></div>
```

```javascript
const editor = new RichEditor({
    container: '#editor',
    placeholder: '请输入内容...',
    height: 300
});
```

## 配置选项

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| container | string | '#rich-editor' | 容器选择器 |
| placeholder | string | '请输入内容...' | 占位符文本 |
| height | number | 300 | 编辑器高度 |
| toolbar | array | 默认工具栏 | 工具栏配置 |
| onChange | function | function() {} | 内容变化回调 |
| onReady | function | function() {} | 编辑器就绪回调 |
| value | string | '' | 初始内容 |
| readonly | boolean | false | 是否只读 |

## 主要方法

### 内容操作

```javascript
// 获取内容
const html = editor.getContent('html');    // HTML格式
const text = editor.getContent('text');    // 纯文本
const delta = editor.getContent('delta');   // Delta格式

// 设置内容
editor.setContent('<p>新内容</p>');

// 清空内容
editor.clear();
```

### 文本操作

```javascript
// 插入文本
editor.insertText('文本', { bold: true });

// 插入HTML
editor.insertHTML('<p>HTML内容</p>');

// 格式化选中文本
editor.format('bold', true);

// 获取选中文本格式
const format = editor.getFormat();
```

### 编辑器控制

```javascript
// 设置只读模式
editor.setReadOnly(true);

// 聚焦/失焦
editor.focus();
editor.blur();

// 获取编辑器实例
const quillEditor = editor.getEditor();

// 销毁编辑器
editor.destroy();
```

## 工具栏配置

```javascript
const editor = new RichEditor({
    container: '#editor',
    toolbar: [
        ['bold', 'italic', 'underline'],           // 基本格式
        ['link', 'image'],                         // 链接和图片
        [{ 'list': 'ordered'}, { 'list': 'bullet' }], // 列表
        ['blockquote', 'code-block'],              // 引用和代码
        [{ 'header': [1, 2, 3, false] }],         // 标题
        [{ 'color': [] }, { 'background': [] }],  // 颜色
        [{ 'align': [] }],                        // 对齐
        ['clean']                                 // 清除格式
    ]
});
```

## 事件处理

```javascript
const editor = new RichEditor({
    container: '#editor',
    onChange: function(content, delta, oldDelta) {
        console.log('内容变化:', content);
    },
    onReady: function(editor) {
        console.log('编辑器就绪');
    }
});
```

## 完整示例

```html
<!DOCTYPE html>
<html>
<head>
    <link href="https://cdn.quilljs.com/1.3.6/quill.snow.css" rel="stylesheet">
    <script src="https://cdn.quilljs.com/1.3.6/quill.min.js"></script>
    <link rel="stylesheet" href="/static/css/rich-editor.css">
    <script src="/static/js/components/rich-editor.js"></script>
</head>
<body>
    <div id="editor" style="height: 300px;"></div>
    
    <script>
        const editor = new RichEditor({
            container: '#editor',
            placeholder: '请输入内容...',
            height: 300,
            toolbar: [
                ['bold', 'italic', 'underline'],
                ['link', 'image'],
                [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                ['blockquote', 'code-block'],
                [{ 'header': [1, 2, 3, false] }],
                [{ 'color': [] }, { 'background': [] }],
                [{ 'align': [] }],
                ['clean']
            ],
            onChange: function(content) {
                console.log('内容变化:', content);
            },
            onReady: function(editor) {
                console.log('编辑器就绪');
            }
        });

        // 获取内容
        function getContent() {
            const content = editor.getContent();
            console.log('编辑器内容:', content);
        }

        // 设置内容
        function setContent() {
            editor.setContent('<p>这是新内容</p>');
        }
    </script>
</body>
</html>
```

## 样式定制

组件提供了丰富的CSS类名，可以自定义样式：

```css
/* 编辑器容器 */
.rich-editor-container {
    border: 1px solid #dcdfe6;
    border-radius: 4px;
}

/* 工具栏 */
.rich-editor-container .ql-toolbar {
    background: #fafafa;
    border-bottom: 1px solid #e4e7ed;
}

/* 编辑区域 */
.rich-editor-container .ql-editor {
    min-height: 200px;
    font-size: 14px;
    line-height: 1.5;
}

/* 只读模式 */
.rich-editor-container.readonly {
    background: #f5f7fa;
}

/* 错误状态 */
.rich-editor-container.error {
    border-color: #f56c6c;
}

/* 禁用状态 */
.rich-editor-container.disabled {
    background: #f5f7fa;
    cursor: not-allowed;
}
```

## 注意事项

1. 确保在使用前已正确引入 Quill.js 和相关样式
2. 编辑器容器必须有明确的高度
3. 在组件销毁时调用 `destroy()` 方法清理资源
4. 图片上传需要单独配置处理逻辑
5. 支持响应式设计，在移动端会自动调整工具栏

## 浏览器支持

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## 更新日志

### v1.0.0
- 初始版本发布
- 支持基本的富文本编辑功能
- 支持自定义工具栏配置
- 支持只读模式
- 支持内容变化监听
- 支持多种内容格式获取
- 支持程序化内容操作
