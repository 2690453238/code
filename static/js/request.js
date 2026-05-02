// 全局请求配置和拦截器
(function() {
    // 添加请求拦截器
    axios.interceptors.request.use(function (config) {
        // 从本地存储获取token
        const token = localStorage.getItem('token');
        if (token) {
            // 为所有需要授权的请求添加token
            config.headers.Authorization = 'Bearer ' + token;
        }
        return config;
    }, function (error) {
        return Promise.reject(error);
    });

    // 添加响应拦截器
    axios.interceptors.response.use(function (response) {
        return response;
    }, function (error) {
        if (error.response) {
            // 移除鉴权后，不再处理401错误跳转
            // 显示错误消息
            const message = error.response.data && error.response.data.message 
                ? error.response.data.message 
                : '请求失败';
            
            // 如果Vue和Element UI已加载，使用Element的消息提示
            if (window.Vue && window.ELEMENT) {
                ELEMENT.Message.error(message);
            } else {
                console.error(message);
            }
        }
        return Promise.reject(error);
    });
})(); 