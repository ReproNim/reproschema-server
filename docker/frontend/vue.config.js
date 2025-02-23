const path = require('path');

module.exports = {
  outputDir: 'dist',
  assetsDir: 'assets',
  publicPath: process.env.ASSETS_PUBLIC_PATH || '/',
  transpileDependencies: ['reproschema-ui'],
  configureWebpack: {
    resolve: {
      symlinks: false,
      extensions: ['.js', '.vue', '.json'],
      modules: [
        path.resolve('/app/node_modules'),
        'node_modules'
      ],
      alias: {
        '@': path.resolve(__dirname, 'src'),
        'reproschema-ui': path.resolve('/app/node_modules/reproschema-ui')
      }
    }
  }
}