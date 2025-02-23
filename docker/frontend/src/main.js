import Vue from 'vue';
import ReproSchemaUi from 'reproschema-ui';
import axios from 'axios';
import config from './config.js';
import App from './App.vue';
import router from './router';
import store from './store';

console.log('Config loaded:', config);

axios.defaults.baseURL = config.backendServer;

// Add token management
const getAuthToken = async (project = 'default') => {
  try {
    const token = config.initialToken;
    const response = await axios.get(`/token?token=${token}&project=${project}`);
    const { auth_token, expires } = response.data;
    localStorage.setItem('auth_token', auth_token);
    localStorage.setItem('token_expiry', expires);
    return auth_token;
  } catch (error) {
    console.error('Token acquisition failed:', error);
    throw error;
  }
};

Vue.use(ReproSchemaUi);

store.commit('setConfig', config);

new Vue({
  router,
  store,
  render: h => h(App)
}).$mount('#app');