// Version Picker for Sentinel Documentation
(function() {
    'use strict';

    // Configuration - will be updated by build script
    const CURRENT_VERSION = '25.12';

    // Detect base path from current URL
    function getBasePath() {
        const path = window.location.pathname;
        const versionMatch = path.match(/^(.*?)\/\d+\.\d+\//);
        return versionMatch ? versionMatch[1] : '';
    }

    const BASE_PATH = getBasePath();
    const VERSIONS_URL = BASE_PATH + '/versions.json';

    // Fetch versions and initialize picker
    async function initVersionPicker() {
        try {
            const response = await fetch(VERSIONS_URL);
            if (!response.ok) {
                console.warn('Could not load versions.json');
                return;
            }

            const data = await response.json();
            createVersionPicker(data.versions, data.default);
            checkOutdatedVersion(data.versions);
        } catch (error) {
            console.warn('Error loading version picker:', error);
        }
    }

    // Create the version picker dropdown
    function createVersionPicker(versions, defaultVersion) {
        const menuBar = document.querySelector('.right-buttons');
        if (!menuBar) return;

        const picker = document.createElement('div');
        picker.className = 'version-picker';

        const label = document.createElement('label');
        label.textContent = 'Version:';
        label.setAttribute('for', 'version-select');

        const select = document.createElement('select');
        select.id = 'version-select';
        select.setAttribute('aria-label', 'Select documentation version');

        versions.forEach(v => {
            const option = document.createElement('option');
            option.value = v.path;
            option.textContent = v.title;
            if (v.path === CURRENT_VERSION) {
                option.selected = true;
            }
            select.appendChild(option);
        });

        select.addEventListener('change', function() {
            const selectedVersion = this.value;
            const currentPath = window.location.pathname;

            // Replace version in path, preserving the base path
            const versionPattern = /\/(\d+\.\d+)\//;
            let newPath;

            if (versionPattern.test(currentPath)) {
                newPath = currentPath.replace(versionPattern, '/' + selectedVersion + '/');
            } else {
                newPath = BASE_PATH + '/' + selectedVersion + '/';
            }

            window.location.href = newPath;
        });

        picker.appendChild(label);
        picker.appendChild(select);

        // Add version badge
        const currentVersionData = versions.find(v => v.path === CURRENT_VERSION);
        if (currentVersionData) {
            const badge = document.createElement('span');
            badge.className = 'version-badge' + (currentVersionData.latest ? ' latest' : ' outdated');
            badge.textContent = currentVersionData.latest ? 'Latest' : 'Outdated';
            picker.appendChild(badge);
        }

        menuBar.insertBefore(picker, menuBar.firstChild);
    }

    // Show warning if viewing outdated version
    function checkOutdatedVersion(versions) {
        const currentVersionData = versions.find(v => v.path === CURRENT_VERSION);
        const latestVersion = versions.find(v => v.latest);

        if (currentVersionData && !currentVersionData.latest && latestVersion) {
            const warning = document.createElement('div');
            warning.className = 'outdated-warning show';
            warning.innerHTML = `
                <strong>You are viewing documentation for Sentinel ${CURRENT_VERSION}.</strong>
                The latest version is <a href="${BASE_PATH}/${latestVersion.path}/">${latestVersion.version}</a>.
            `;

            const content = document.querySelector('.content');
            if (content && content.firstChild) {
                content.insertBefore(warning, content.firstChild);
            }
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initVersionPicker);
    } else {
        initVersionPicker();
    }
})();
