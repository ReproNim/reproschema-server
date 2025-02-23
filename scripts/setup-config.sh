#!/bin/bash
set -e

# Enhanced logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Get schema config values
get_schema_config() {
    local SCHEMA_SOURCE="$1"
    local temp_config="/tmp/schema_config.js"

    log "=== Processing Schema Config ==="
    log "SCHEMA_SOURCE: ${SCHEMA_SOURCE}"

    if [[ "$SCHEMA_SOURCE" == http* ]] && [[ "$SCHEMA_SOURCE" == *"github"* ]]; then
        local repo_path branch
        repo_path=$(echo "$SCHEMA_SOURCE" | sed -E 's|https://raw.githubusercontent.com/([^/]+/[^/]+)/.*|\1|')
        branch=$(echo "$SCHEMA_SOURCE" | sed -E 's|https://raw.githubusercontent.com/[^/]+/[^/]+/([^/]+)/.*|\1|')
        
        log "Extracted repo_path: ${repo_path}"
        log "Extracted branch: ${branch}"
        
        local config_url="https://raw.githubusercontent.com/${repo_path}/${branch}/ui-changes/src/config.js"
        log "Trying to fetch config from: ${config_url}"
        
        if curl --location --silent "$config_url" > "$temp_config" 2>/dev/null; then
            log "Config file downloaded to: ${temp_config}"
            log "Config contents:"
            cat "$temp_config"
            
            if [ -s "$temp_config" ] && grep -q "module.exports" "$temp_config"; then
                banner=$(grep "banner:" "$temp_config" | sed "s/.*banner: '\([^']*\)'.*/\1/")
                assets_path=$(grep "assetsPublicPath:" "$temp_config" | sed "s/.*assetsPublicPath: '\([^']*\)'.*/\1/")
                log "Extracted values:"
                log "  banner: ${banner}"
                log "  assets_path: ${assets_path}"
                log "Extracted assetsPublicPath: ${assets_path}"
                # Save for both build and runtime
                echo "${assets_path}" > /tmp/assets_path
                export ASSETS_PUBLIC_PATH="$(cat /tmp/assets_path)"
            fi
        fi
    else
        log "SCHEMA_SOURCE is not a GitHub URL, skipping config fetch"
    fi
}

# Update config for webpack build
setup_config() {
    # Get schema values
    get_schema_config "$SCHEMA_SOURCE"
    
    log "=== Building Final Config ==="
    log "Environment variables:"
    log "  SCHEMA_SOURCE: ${SCHEMA_SOURCE}"
    log "  BACKEND_URL: ${BACKEND_URL}"
    log "  INITIAL_TOKEN: ${INITIAL_TOKEN}"
    log "Schema values:"
    log "  banner: ${banner}"
    log "  assets_path: ${assets_path}"
    
    # Write config file with all values
    cat > src/config.js << EOL
module.exports = {
    /* eslint-disable */
    githubSrc: '${SCHEMA_SOURCE:-##SCHEMA_SOURCE##}',
    banner: '${banner:-Default Banner}',
    startButton: 'Start',
    assetsPublicPath: '${assets_path:-/}',
    backendServer: '${BACKEND_URL}',
    modes: {
        url: true,
        admin: true,
        debug: true
    },
    studyPrefix: 'study',
    initialToken: '${INITIAL_TOKEN}',
    schemaType: 'jsonld',
    validateSchema: true
};
EOL

    log "=== Final webpack config.js ==="
    cat src/config.js
}

# Run setup
setup_config 