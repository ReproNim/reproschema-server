module.exports = {
  /* eslint-disable */
  githubSrc: '${SCHEMA_SOURCE}',  // Will be replaced if SCHEMA_SOURCE is set
  banner: '${banner}',
  startButton: 'Start',
  assetsPublicPath: '/',
  backendServer: '${BACKEND_URL}',
  modes: {
    url: true,  // Enable URL parameter mode
    admin: true,
    debug: true
  },
  studyPrefix: 'study',
  initialToken: '',
  schemaType: 'jsonld',
  validateSchema: true
};