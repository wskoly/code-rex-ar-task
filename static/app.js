/**
 * Virtual Try-On AR Application
 * ============================
 * Main application logic for handling AR face tracking, model management,
 * and user interactions with exclusive selection of accessories.
 * 
 * Author: AI Engineer Assessment
 */

class VirtualTryOnApp {
    constructor() {
        this.models = {
            hats: [],
            glasses: []
        };
        this.selectedModels = {
            hats: null,
            glasses: null
        };
        this.arScene = null;
        this.isInitialized = false;
        this.loadingCount = 0;
        
        this.init();
    }

    /**
     * Initialize the application
     */
    async init() {
        try {
            this.updateStatus('Initializing application...', 'loading');
            
            // Wait for DOM to be ready
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.setup());
            } else {
                await this.setup();
            }
        } catch (error) {
            console.error('Initialization error:', error);
            this.showToast('Failed to initialize application', 'error');
        }
    }

    /**
     * Setup application components
     */
    async setup() {
        try {
            // Check browser compatibility first
            const compatibilityCheck = await this.checkBrowserCompatibility();
            if (!compatibilityCheck.compatible) {
                this.showCompatibilityMessage(compatibilityCheck.message);
                this.updateStatus(compatibilityCheck.message, 'error');
                return;
            }

            // Initialize AR scene reference
            this.arScene = document.querySelector('#arScene');
            
            // Setup event listeners
            this.setupEventListeners();
            
            // Load models from backend
            await this.loadModels();
            
            // Initialize AR scene
            await this.initializeARScene();
            
            this.updateStatus('Camera ready - Position your face in view', 'active');
            this.isInitialized = true;
            
        } catch (error) {
            console.error('Setup error:', error);
            
            // Show specific error messages
            if (error.message.includes('Camera access')) {
                this.showCompatibilityMessage('Camera access is required for AR features. Please allow camera permissions and refresh the page.');
            } else if (error.message.includes('AR Scene failed')) {
                this.showCompatibilityMessage('AR tracking failed to initialize. This might be due to device limitations or poor lighting conditions.');
            } else {
                this.showCompatibilityMessage('Failed to initialize AR features. Your device or browser might not support AR.');
            }
            
            this.updateStatus('AR initialization failed', 'error');
        }
    }

    /**
     * Check browser compatibility for AR features
     */
    async checkBrowserCompatibility() {
        // Check if we're in a secure context (HTTPS or localhost)
        if (location.protocol !== 'https:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
            return {
                compatible: false,
                message: 'Camera access requires HTTPS. Please use a secure connection.'
            };
        }

        // Check for required APIs
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            return {
                compatible: false,
                message: 'Camera access not supported by your browser.'
            };
        }

        // Check WebGL support
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        if (!gl) {
            return {
                compatible: false,
                message: '3D graphics not supported by your device.'
            };
        }

        // Test camera access
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ 
                video: { 
                    facingMode: 'user',
                    width: { ideal: 640 },
                    height: { ideal: 480 }
                } 
            });
            
            // Immediately stop the stream - we just needed to test access
            stream.getTracks().forEach(track => track.stop());
            
            return { compatible: true };
        } catch (error) {
            console.error('Camera access test failed:', error);
            
            let message = 'Camera access denied or unavailable.';
            
            if (error.name === 'NotAllowedError') {
                message = 'Camera permission denied. Please allow camera access and refresh the page.';
            } else if (error.name === 'NotFoundError') {
                message = 'No camera found on your device.';
            } else if (error.name === 'NotSupportedError') {
                message = 'Camera not supported by your browser.';
            }
            
            return {
                compatible: false,
                message: message
            };
        }
    }

    /**
     * Show compatibility message for unsupported devices
     */
    showCompatibilityMessage(message) {
        const compatibilityDiv = document.getElementById('compatibilityMessage');
        const compatibilityText = document.getElementById('compatibilityText');
        
        if (compatibilityDiv && compatibilityText) {
            compatibilityText.textContent = message;
            compatibilityDiv.style.display = 'block';
        }
    }

    /**
     * Setup all event listeners
     */
    setupEventListeners() {
        // Toggle panel functionality
        const toggleBtn = document.getElementById('toggleBtn');
        const controlPanel = document.getElementById('controlPanel');
        
        if (toggleBtn && controlPanel) {
            toggleBtn.addEventListener('click', () => {
                controlPanel.classList.toggle('collapsed');
                toggleBtn.classList.toggle('collapsed');
            });
        }

        // Tab switching
        const tabButtons = document.querySelectorAll('.tab-button');
        tabButtons.forEach(button => {
            button.addEventListener('click', (e) => this.switchTab(e.target.closest('.tab-button').dataset.tab));
        });

        // Clear all button
        const clearAllBtn = document.getElementById('clearAllBtn');
        if (clearAllBtn) {
            clearAllBtn.addEventListener('click', () => this.clearAllAccessories());
        }

        // AR Scene events
        if (this.arScene) {
            this.arScene.addEventListener('renderstart', () => {
                console.log('AR Scene rendering started');
            });
        }
    }

    /**
     * Switch between tabs (hats/glasses)
     */
    switchTab(tabName) {
        // Update tab buttons
        const tabButtons = document.querySelectorAll('.tab-button');
        tabButtons.forEach(button => {
            button.classList.remove('active');
            if (button.dataset.tab === tabName) {
                button.classList.add('active');
            }
        });

        // Update tab content
        const tabContents = document.querySelectorAll('.tab-content');
        tabContents.forEach(content => {
            content.classList.remove('active');
        });

        const activeTab = document.getElementById(`${tabName}-tab`);
        if (activeTab) {
            activeTab.classList.add('active');
        }

        console.log(`Switched to ${tabName} tab`);
    }

    /**
     * Load models from backend API
     */
    async loadModels() {
        try {
            this.updateStatus('Loading 3D models...', 'loading');
            
            const response = await fetch('/api/models');
            const result = await response.json();
            
            if (result.status === 'success') {
                this.models = result.data;
                this.renderModelGrids();
                this.updateModelCounts();
                console.log('Models loaded successfully:', this.models);
            } else {
                throw new Error(result.message || 'Failed to load models');
            }
        } catch (error) {
            console.error('Error loading models:', error);
            this.showToast('Failed to load 3D models from database', 'error');
            
            // Use fallback models if backend fails
            this.loadFallbackModels();
        }
    }

    /**
     * Load fallback models if backend is not available
     */
    loadFallbackModels() {
        console.warn('Using fallback models - backend unavailable');
        this.models = {
            hats: [
                {
                    id: 'hat1-fallback',
                    name: 'Classic Hat',
                    filename: 'hat.glb',
                    thumbnail: null, // No placeholder thumbnails
                    position: [0, -0.2, -0.7],
                    rotation: [0, -90, 0],
                    scale: [0.27, 0.27, 0.27],
                    anchor_index: 10
                },
                {
                    id: 'hat2-fallback',
                    name: 'Cowboy Hat',
                    filename: 'cowboy_hat_free.glb',
                    thumbnail: null, // No placeholder thumbnails
                    position: [0, 0, -0.75],
                    rotation: [0, 0, 0],
                    scale: [0.07, 0.07, 0.07],
                    anchor_index: 10
                }
            ],
            glasses: [
                {
                    id: 'glasses1-fallback',
                    name: 'Eyewear Specs',
                    filename: 'eyewear_specs.glb',
                    thumbnail: null, // No placeholder thumbnails
                    position: [-0.52, -0.25, -1.25],
                    rotation: [0, 90, 0],
                    scale: [0.35, 0.35, 0.35],
                    anchor_index: 168
                },
                {
                    id: 'glasses2-fallback',
                    name: 'Wooden Sunglasses',
                    filename: 'wooden_sunglasses.glb',
                    thumbnail: null, // No placeholder thumbnails
                    position: [0, -0.05, 0],
                    rotation: [5, 0, 0],
                    scale: [0.23, 0.23, 0.23],
                    anchor_index: 168
                }
            ]
        };
        
        this.renderModelGrids();
        this.updateModelCounts();
        this.showToast('Using offline models - some features limited', 'error');
        console.log('Fallback models loaded');
    }

    /**
     * Render model grids in the UI
     */
    renderModelGrids() {
        this.renderCategoryGrid('hats');
        this.renderCategoryGrid('glasses');
    }

    /**
     * Render models for a specific category
     */
    renderCategoryGrid(category) {
        const gridElement = document.getElementById(`${category}Grid`);
        if (!gridElement) return;

        gridElement.innerHTML = '';

        this.models[category].forEach(model => {
            const modelCard = this.createModelCard(model, category);
            gridElement.appendChild(modelCard);
        });
    }

    /**
     * Create a model card element
     */
    createModelCard(model, category) {
        const card = document.createElement('div');
        card.className = 'model-card';
        card.dataset.modelId = model.id;
        card.dataset.category = category;

        // Create thumbnail
        const thumbnail = document.createElement('div');
        thumbnail.className = 'model-thumbnail';
        
        if (model.thumbnail) {
            const img = document.createElement('img');
            img.src = model.thumbnail;
            img.alt = model.name;
            img.onerror = () => {
                // If thumbnail fails to load, show category icon instead
                thumbnail.innerHTML = `<i class="fas fa-${category === 'hats' ? 'hat-wizard' : 'glasses'}"></i>`;
            };
            thumbnail.appendChild(img);
        } else {
            // No thumbnail available - show category icon
            thumbnail.innerHTML = `<i class="fas fa-${category === 'hats' ? 'hat-wizard' : 'glasses'}"></i>`;
        }

        // Create model info
        const info = document.createElement('div');
        info.className = 'model-info';
        
        const name = document.createElement('div');
        name.className = 'model-name';
        name.textContent = model.name;

        info.appendChild(name);

        card.appendChild(thumbnail);
        card.appendChild(info);

        // Add click event listener
        card.addEventListener('click', () => this.toggleModel(model, category));

        return card;
    }

    /**
     * Toggle model selection with exclusive logic
     */
    async toggleModel(model, category) {
        try {
            const wasSelected = this.selectedModels[category]?.id === model.id;
            
            // Update UI immediately for better UX
            this.updateModelSelection(category, wasSelected ? null : model);
            
            if (wasSelected) {
                // Deselect current model
                await this.removeModelFromScene(model);
                this.selectedModels[category] = null;
                this.showToast(`${model.name} removed`, 'success');
            } else {
                // Remove currently selected model in this category (exclusive selection)
                if (this.selectedModels[category]) {
                    await this.removeModelFromScene(this.selectedModels[category]);
                }
                
                // Add new model
                await this.addModelToScene(model, category);
                this.selectedModels[category] = model;
                this.showToast(`${model.name} applied`, 'success');
            }
            
        } catch (error) {
            console.error('Error toggling model:', error);
            this.showToast('Failed to apply model', 'error');
        }
    }

    /**
     * Update model selection UI
     */
    updateModelSelection(category, selectedModel) {
        const cards = document.querySelectorAll(`[data-category="${category}"]`);
        cards.forEach(card => {
            card.classList.remove('selected');
            if (selectedModel && card.dataset.modelId === selectedModel.id) {
                card.classList.add('selected');
            }
        });
    }

    /**
     * Add model to AR scene
     */
    async addModelToScene(model, category) {
        try {
            // First, ensure the model asset exists
            await this.ensureModelAsset(model);
            
            // Create AR entity
            const entity = document.createElement('a-entity');
            entity.setAttribute('mindar-face-target', `anchorIndex: ${model.anchor_index}`);
            entity.setAttribute('id', `model-${model.id}`);

            // Create GLTF model
            const gltfModel = document.createElement('a-gltf-model');
            gltfModel.setAttribute('src', `#asset-${model.id}`);
            gltfModel.setAttribute('position', model.position.join(' '));
            gltfModel.setAttribute('rotation', model.rotation.join(' '));
            gltfModel.setAttribute('scale', model.scale.join(' '));
            gltfModel.setAttribute('class', `${category}-entity`);

            entity.appendChild(gltfModel);
            this.arScene.appendChild(entity);

            console.log(`Added ${model.name} to scene`);
        } catch (error) {
            console.error('Error adding model to scene:', error);
            throw error;
        }
    }

    /**
     * Remove model from AR scene
     */
    async removeModelFromScene(model) {
        try {
            const entity = document.querySelector(`#model-${model.id}`);
            if (entity) {
                entity.parentNode.removeChild(entity);
                console.log(`Removed ${model.name} from scene`);
            }
        } catch (error) {
            console.error('Error removing model from scene:', error);
        }
    }

    /**
     * Ensure model asset is loaded
     */
    async ensureModelAsset(model) {
        const assetId = `asset-${model.id}`;
        let asset = document.querySelector(`#${assetId}`);
        
        if (!asset) {
            asset = document.createElement('a-asset-item');
            asset.setAttribute('id', assetId);
            asset.setAttribute('src', `/models/${model.filename}`);
            
            const assets = document.querySelector('#arAssets');
            assets.appendChild(asset);
            
            // Wait for asset to load
            return new Promise((resolve, reject) => {
                const timeout = setTimeout(() => {
                    reject(new Error('Asset load timeout'));
                }, 10000);

                asset.addEventListener('loaded', () => {
                    clearTimeout(timeout);
                    resolve();
                });

                asset.addEventListener('error', () => {
                    clearTimeout(timeout);
                    reject(new Error('Asset failed to load'));
                });
            });
        }
    }

    /**
     * Initialize AR Scene
     */
    async initializeARScene() {
        return new Promise((resolve, reject) => {
            if (!this.arScene) {
                reject(new Error('AR Scene not found'));
                return;
            }

            const timeout = setTimeout(() => {
                reject(new Error('AR Scene failed to start. Try refreshing the page or check camera permissions.'));
            }, 20000); // Increased timeout for mobile devices

            // Listen for different AR scene events
            this.arScene.addEventListener('renderstart', () => {
                clearTimeout(timeout);
                console.log('AR Scene started successfully');
                resolve();
            });

            this.arScene.addEventListener('arReady', () => {
                clearTimeout(timeout);
                console.log('AR tracking ready');
                resolve();
            });

            // Listen for AR errors
            this.arScene.addEventListener('arError', (event) => {
                clearTimeout(timeout);
                console.error('AR Error:', event.detail);
                reject(new Error('AR failed to initialize: ' + (event.detail || 'Unknown error')));
            });

            // Check if scene is already rendered
            if (this.arScene.hasLoaded) {
                clearTimeout(timeout);
                resolve();
            }

            // Additional fallback for mobile browsers
            setTimeout(() => {
                if (this.arScene.object3D && this.arScene.object3D.visible) {
                    clearTimeout(timeout);
                    resolve();
                }
            }, 5000);
        });
    }

    /**
     * Handle file upload
     */
    async handleFileUpload(event) {
        // Upload functionality removed - use admin interface at /admin
        this.showToast('Upload functionality moved to admin panel at /admin', 'error');
        console.log('Upload attempted - redirected to admin panel');
    }

    /**
     * Upload model file to backend
     */
    async uploadModelFile(file, category, name) {
        // Upload functionality removed - use admin interface
        throw new Error('Upload functionality moved to admin panel');
    }

    /**
     * Prompt user for model category
     */
    async promptModelCategory() {
        // Not needed anymore - admin panel handles this
        return 'glasses';
    }

    /**
     * Prompt user for model name
     */
    async promptModelName(filename) {
        // Not needed anymore - admin panel handles this
        return filename.replace(/\.[^/.]+$/, '');
    }

    /**
     * Clear all accessories
     */
    clearAllAccessories() {
        Object.keys(this.selectedModels).forEach(category => {
            if (this.selectedModels[category]) {
                this.removeModelFromScene(this.selectedModels[category]);
                this.selectedModels[category] = null;
                this.updateModelSelection(category, null);
            }
        });

        this.showToast('All accessories cleared', 'success');
    }

    /**
     * Update model counts in UI
     */
    updateModelCounts() {
        const hatsCount = document.getElementById('hatsCount');
        const glassesCount = document.getElementById('glassesCount');
        
        if (hatsCount) {
            hatsCount.textContent = `${this.models.hats?.length || 0}`;
        }
        
        if (glassesCount) {
            glassesCount.textContent = `${this.models.glasses?.length || 0}`;
        }
    }

    /**
     * Update status bar
     */
    updateStatus(text, type = 'loading') {
        const statusBar = document.getElementById('statusBar');
        const statusText = document.getElementById('statusText');
        
        if (statusBar && statusText) {
            statusText.textContent = text;
            statusBar.className = `status-bar ${type}`;
        }
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'success') {
        const toast = document.getElementById('toast');
        if (!toast) return;

        toast.textContent = message;
        toast.className = `toast ${type} show`;

        setTimeout(() => {
            toast.className = `toast ${type}`;
        }, 3000);
    }
}

// Initialize the application when the page loads
window.addEventListener('load', () => {
    window.virtualTryOnApp = new VirtualTryOnApp();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        console.log('App paused');
    } else {
        console.log('App resumed');
    }
});