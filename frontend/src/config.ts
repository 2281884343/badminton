// API 配置
const API_BASE_URL = import.meta.env.PROD 
  ? `${window.location.protocol}//${window.location.hostname}:8080`
  : '';

export { API_BASE_URL };

