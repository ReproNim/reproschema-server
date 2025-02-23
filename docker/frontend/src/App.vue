<template>
    <div id="app">
      <reproschema-ui
        :config="config"
        @submit="onSubmit"
      />
    </div>
  </template>
  
  <script>
  import axios from 'axios';
  import config from './config.js';
  import { ReproSchemaUi } from 'reproschema-ui'
  
  export default {
    name: 'App',
    components: {
      'reproschema-ui': ReproSchemaUi
    },
    data() {
      return {
        config: {
          githubSrc: config.githubSrc,
          banner: config.banner,
          startButton: config.startButton,
          assetsPublicPath: config.assetsPublicPath,
          backendServer: config.backendServer
        }
      }
    },
    methods: {
      async getAuthToken(project = 'default') {
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
      },
      async onSubmit(formData) {
        try {
          const token = localStorage.getItem('auth_token');
          const expiry = localStorage.getItem('token_expiry');
          
          if (!token || new Date(expiry) <= new Date()) {
            await this.getAuthToken();
          }
          
          await axios.post('/api/responses', formData, {
            headers: {
              'Authorization': localStorage.getItem('auth_token')
            }
          });
        } catch (error) {
          console.error('Form submission failed:', error);
          throw error;
        }
      }
    }
  }
  </script>