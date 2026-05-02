// 定义一个全局的工具对象
window.Utils = {
    /**
     * 格式化日期时间
     * @param {string|Date} dateStr 日期字符串或Date对象
     * @param {string} format 格式化模式，默认：YYYY-MM-DD HH:mm:ss
     * @returns {string} 格式化后的日期字符串
     */
    formatDate(dateStr, format = 'YYYY-MM-DD HH:mm:ss') {
        if (!dateStr) return '';
        const date = typeof dateStr === 'string' ? new Date(dateStr) : dateStr;
        if (isNaN(date.getTime())) return '';

        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');

        return format
            .replace('YYYY', year)
            .replace('MM', month)
            .replace('DD', day)
            .replace('HH', hours)
            .replace('mm', minutes)
            .replace('ss', seconds);
    },

    /**
     * 格式化文件大小
     * @param {number} bytes 字节数
     * @returns {string} 格式化后的文件大小
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    /**
     * 防抖函数
     * @param {Function} func 要执行的函数
     * @param {number} wait 延迟时间（毫秒）
     * @returns {Function} 防抖后的函数
     */
    debounce(func, wait) {
        let timeout;
        return function (...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    },

    /**
     * 节流函数
     * @param {Function} func 要执行的函数
     * @param {number} wait 间隔时间（毫秒）
     * @returns {Function} 节流后的函数
     */
    throttle(func, wait) {
        let timeout;
        let previous = 0;
        return function (...args) {
            const now = Date.now();
            const remaining = wait - (now - previous);
            if (remaining <= 0) {
                clearTimeout(timeout);
                timeout = null;
                previous = now;
                func.apply(this, args);
            } else if (!timeout) {
                timeout = setTimeout(() => {
                    previous = Date.now();
                    timeout = null;
                    func.apply(this, args);
                }, remaining);
            }
        };
    },

    /**
     * 深拷贝对象
     * @param {Object} obj 要拷贝的对象
     * @returns {Object} 拷贝后的新对象
     */
    deepClone(obj) {
        if (obj === null || typeof obj !== 'object') return obj;
        const clone = Array.isArray(obj) ? [] : {};
        for (let key in obj) {
            if (Object.prototype.hasOwnProperty.call(obj, key)) {
                clone[key] = this.deepClone(obj[key]);
            }
        }
        return clone;
    },

    /**
     * 验证手机号
     * @param {string} phone 手机号
     * @returns {boolean} 是否是有效的手机号
     */
    isValidPhone(phone) {
        return /^1[3-9]\d{9}$/.test(phone);
    },

    /**
     * 验证邮箱
     * @param {string} email 邮箱
     * @returns {boolean} 是否是有效的邮箱
     */
    isValidEmail(email) {
        return /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(email);
    },

    /**
     * 验证身份证号
     * @param {string} idCard 身份证号
     * @returns {boolean} 是否是有效的身份证号
     */
    isValidIdCard(idCard) {
        return /(^\d{15}$)|(^\d{18}$)|(^\d{17}(\d|X|x)$)/.test(idCard);
    }
}; 