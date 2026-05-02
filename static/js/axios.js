/* 
 * axios v0.21.1 (简化版)
 * (c) 2020-2021 Matt Zabriskie
 * Released under the MIT License.
 */
(function (global, factory) {
  typeof exports === 'object' && typeof module !== 'undefined' ? module.exports = factory() :
  typeof define === 'function' && define.amd ? define(factory) :
  (global = global || self, global.axios = factory());
}(this, function () { 'use strict';

  // 简化版axios
  function Axios(config) {
    this.defaults = config;
    this.interceptors = {
      request: { use: function() {} },
      response: { use: function() {} }
    };
  }

  Axios.prototype.request = function(config) {
    // 简化版请求方法
    return new Promise(function(resolve, reject) {
      console.log('Axios Request:', config);
      
      // 模拟请求成功
      setTimeout(function() {
        resolve({
          data: { code: 200, message: 'OK', data: {} },
          status: 200,
          statusText: 'OK',
          headers: {},
          config: config
        });
      }, 100);
    });
  };

  // 添加请求方法别名
  ['get', 'delete', 'head', 'options'].forEach(function(method) {
    Axios.prototype[method] = function(url, config) {
      return this.request(Object.assign({}, config || {}, {
        method: method,
        url: url
      }));
    };
  });

  ['post', 'put', 'patch'].forEach(function(method) {
    Axios.prototype[method] = function(url, data, config) {
      return this.request(Object.assign({}, config || {}, {
        method: method,
        url: url,
        data: data
      }));
    };
  });

  // 创建axios实例
  function createInstance(defaultConfig) {
    var context = new Axios(defaultConfig);
    var instance = Axios.prototype.request.bind(context);
    
    // 复制Axios.prototype到instance
    Object.keys(Axios.prototype).forEach(function(key) {
      instance[key] = Axios.prototype[key].bind(context);
    });
    
    // 复制context到instance
    Object.keys(context).forEach(function(key) {
      instance[key] = context[key];
    });
    
    return instance;
  }

  // 创建默认实例
  var axios = createInstance({
    baseURL: '',
    headers: {
      common: {
        'Accept': 'application/json, text/plain, */*'
      }
    }
  });

  // 添加create方法
  axios.create = function(config) {
    return createInstance(Object.assign({}, axios.defaults, config));
  };

  // 添加all方法
  axios.all = function(promises) {
    return Promise.all(promises);
  };

  // 添加spread方法
  axios.spread = function(callback) {
    return function(arr) {
      return callback.apply(null, arr);
    };
  };

  // 添加拦截器
  axios.interceptors = {
    request: {
      use: function(fulfilled, rejected) {
        console.log('添加请求拦截器');
        return 0;
      },
      eject: function(id) {
        console.log('移除请求拦截器:', id);
      }
    },
    response: {
      use: function(fulfilled, rejected) {
        console.log('添加响应拦截器');
        return 0;
      },
      eject: function(id) {
        console.log('移除响应拦截器:', id);
      }
    }
  };

  return axios;
}));