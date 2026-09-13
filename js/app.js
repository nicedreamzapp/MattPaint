/**
 * MattPaint - A faithful recreation of MS Paint Windows 10 for Mac
 * Complete rewrite with proper selection handling
 */

(function() {
    'use strict';

    // ==================== STATE ====================
    const state = {
        // Canvas
        canvasWidth: 800,
        canvasHeight: 600,
        zoom: 1,

        // Colors
        color1: '#000000',
        color2: '#FFFFFF',

        // Tools
        currentTool: 'pencil',
        currentBrush: 'brush',
        currentShape: null,
        lineWidth: 3,

        // Shape options
        shapeOutline: 'solid',
        shapeFill: 'none',

        // Drawing state
        isDrawing: false,
        lastX: 0,
        lastY: 0,
        shapeStart: null,          // {x, y} - starting point for shape drawing

        // Clipboard
        clipboardData: null,       // {width, height, canvas} - internal clipboard

        // Selection - enhanced
        selection: null,           // {x, y, width, height} - the selection bounds
        selectionImageData: null,  // The actual pixel data of the selection
        floatingSelection: null,   // {x, y, imageData, canvas} - floating selection being moved
        isMovingSelection: false,
        selectionStartX: 0,
        selectionStartY: 0,
        isTransparentSelection: false,
        selectionMode: 'rect',     // 'rect' or 'free'
        freeformPoints: [],        // For free-form selection
        freeformPath: null,        // Path2D for free-form selection clipping

        // Text
        textX: 0,
        textY: 0,
        textStyles: {
            font: 'Arial',
            size: 14,
            bold: false,
            italic: false,
            underline: false,
            strikethrough: false
        },

        // History
        history: [],
        historyIndex: -1,
        maxHistory: 50,

        // File
        fileName: 'Untitled',
        isModified: false,

        // UI
        showRulers: false,
        showGridlines: false,
        showStatusBar: true,

        // Mirror drawing mode
        mirrorHorizontal: false,
        mirrorVertical: false
    };

    // ==================== DOM ELEMENTS ====================
    let mainCanvas, mainCtx;
    let previewCanvas, previewCtx;
    let selectionCanvas, selectionCtx;
    let canvasWrapper, canvasContainer;

    // ==================== COLOR PALETTE ====================
    const defaultColors = [
        // Row 1 - Dark colors
        '#000000', '#7F7F7F', '#880015', '#ED1C24', '#FF7F27', '#FFF200',
        '#22B14C', '#00A2E8', '#3F48CC', '#A349A4',
        // Row 2 - Light colors
        '#FFFFFF', '#C3C3C3', '#B97A57', '#FFAEC9', '#FFC90E', '#EFE4B0',
        '#B5E61D', '#99D9EA', '#7092BE', '#C8BFE7',
        // Row 3 - Additional colors
        '#404040', '#808080', '#993300', '#CC6600', '#FFCC00', '#99CC00',
        '#009999', '#0066CC', '#663399', '#CC3399'
    ];

    const basicColors = [
        '#FF0000', '#FF8000', '#FFFF00', '#80FF00', '#00FF00', '#00FF80', '#00FFFF', '#0080FF',
        '#0000FF', '#8000FF', '#FF00FF', '#FF0080', '#FFFFFF', '#C0C0C0', '#808080', '#404040',
        '#000000', '#804000', '#FF8080', '#FFFF80', '#80FF80', '#80FFFF', '#8080FF', '#FF80FF',
        '#FF0080', '#FF8040', '#FFFF80', '#80FF40', '#00FF80', '#40FFFF', '#4080FF', '#8040FF',
        '#FF40FF', '#804040', '#FF4040', '#804000', '#408000', '#004080', '#400080', '#800040',
        '#400000', '#804040', '#FF8080', '#FFBF80', '#FFFF80', '#BFFF80', '#80FF80', '#80FFBF'
    ];

    let customColors = new Array(16).fill('#FFFFFF');

    // Selection animation
    let selectionAnimationId = null;
    let marchingAntsOffset = 0;

    // Brush stroke tracking for smooth interpolation
    let lastBrushX = null;
    let lastBrushY = null;

    // ==================== INITIALIZATION ====================
    function init() {
        mainCanvas = document.getElementById('main-canvas');
        previewCanvas = document.getElementById('preview-canvas');
        selectionCanvas = document.getElementById('selection-canvas');
        canvasWrapper = document.getElementById('canvas-wrapper');
        canvasContainer = document.getElementById('canvas-container');

        // On a phone, start with a canvas that fits the screen instead of 800x600
        if (window.innerWidth < 700) {
            const rect = canvasContainer.getBoundingClientRect();
            state.canvasWidth = Math.max(200, Math.floor(rect.width) - 24);
            state.canvasHeight = Math.max(200, Math.floor(rect.height) - 24);
        }

        initCanvas();
        initColorPalette();
        initColorPicker();
        setupEventListeners();
        setupWindowControls();
        setupSaveAsDialog();
        saveHistory();
        updateStatus();
        updateTitle();
        updateToolStatus();

        // Initialize tool state
        updateToolButtons();
        updateCursor();
        updateSizeButtons();
        updateOutlineFillButtons();

    }

    // Window control buttons (decorative in web, functional in Electron)
    function setupWindowControls() {
        const minimizeBtn = document.querySelector('.window-btn.minimize');
        const maximizeBtn = document.querySelector('.window-btn.maximize');
        const closeBtn = document.querySelector('.window-btn.close');

        if (minimizeBtn) {
            minimizeBtn.addEventListener('click', () => {
                // In a web app, we can't truly minimize, but we could toggle visibility
                // In Electron, this would call: window.minimize()
            });
        }

        if (maximizeBtn) {
            maximizeBtn.addEventListener('click', () => {
                toggleFullscreen();
            });
        }

        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                exitApp();
            });
        }
    }

    // Save As Dialog functionality
    function setupSaveAsDialog() {
        const saveAsOk = document.getElementById('save-as-ok');
        const saveAsCancel = document.getElementById('save-as-cancel');
        const formatOptions = document.querySelectorAll('.save-format-option');

        if (saveAsOk) {
            saveAsOk.addEventListener('click', executeSaveAs);
        }

        if (saveAsCancel) {
            saveAsCancel.addEventListener('click', closeAllDialogs);
        }

        // Handle format option selection styling
        formatOptions.forEach(option => {
            option.addEventListener('click', () => {
                formatOptions.forEach(o => o.classList.remove('selected'));
                option.classList.add('selected');
            });
        });
    }

    function updateToolStatus() {
        const toolNames = {
            'pencil': 'Pencil',
            'brush': 'Brush',
            'eraser': 'Eraser',
            'fill': 'Fill',
            'text': 'Text',
            'picker': 'Color Picker',
            'magnifier': 'Magnifier',
            'select': 'Select'
        };

        const statusTool = document.getElementById('status-tool');
        if (statusTool) {
            let toolName = toolNames[state.currentTool] || state.currentTool;
            if (state.currentShape) {
                toolName = 'Shape: ' + state.currentShape;
            }
            statusTool.textContent = toolName;
        }
    }

    function initCanvas() {
        mainCanvas.width = state.canvasWidth;
        mainCanvas.height = state.canvasHeight;
        previewCanvas.width = state.canvasWidth;
        previewCanvas.height = state.canvasHeight;
        selectionCanvas.width = state.canvasWidth;
        selectionCanvas.height = state.canvasHeight;

        mainCtx = mainCanvas.getContext('2d', { willReadFrequently: true });
        previewCtx = previewCanvas.getContext('2d');
        selectionCtx = selectionCanvas.getContext('2d');

        mainCtx.fillStyle = '#FFFFFF';
        mainCtx.fillRect(0, 0, state.canvasWidth, state.canvasHeight);

        updateCanvasSize();
    }

    function updateCanvasSize() {
        const w = state.canvasWidth * state.zoom;
        const h = state.canvasHeight * state.zoom;

        canvasWrapper.style.width = w + 'px';
        canvasWrapper.style.height = h + 'px';

        mainCanvas.style.width = w + 'px';
        mainCanvas.style.height = h + 'px';
        previewCanvas.style.width = w + 'px';
        previewCanvas.style.height = h + 'px';
        selectionCanvas.style.width = w + 'px';
        selectionCanvas.style.height = h + 'px';
    }

    function resizeAllCanvases(newWidth, newHeight, preserveContent = true) {
        const tempCanvas = document.createElement('canvas');
        if (preserveContent) {
            tempCanvas.width = state.canvasWidth;
            tempCanvas.height = state.canvasHeight;
            tempCanvas.getContext('2d').drawImage(mainCanvas, 0, 0);
        }

        state.canvasWidth = newWidth;
        state.canvasHeight = newHeight;
        mainCanvas.width = newWidth;
        mainCanvas.height = newHeight;
        previewCanvas.width = newWidth;
        previewCanvas.height = newHeight;
        selectionCanvas.width = newWidth;
        selectionCanvas.height = newHeight;

        mainCtx.fillStyle = state.color2;
        mainCtx.fillRect(0, 0, newWidth, newHeight);

        if (preserveContent) {
            mainCtx.drawImage(tempCanvas, 0, 0);
        }

        updateCanvasSize();
        updateStatus();

        // Redraw overlays after resize
        if (state.showGridlines) drawGridlines();
        if (state.showRulers) drawRulers();
    }

    function initColorPalette() {
        const palette = document.getElementById('color-palette');
        palette.innerHTML = '';

        defaultColors.forEach((color) => {
            const swatch = document.createElement('button');
            swatch.className = 'color-swatch';
            swatch.style.background = color;
            swatch.addEventListener('click', () => {
                state.color1 = color;
                updateColorBoxes();
            });
            swatch.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                state.color2 = color;
                updateColorBoxes();
            });
            palette.appendChild(swatch);
        });

        updateColorBoxes();
    }

    function updateColorBoxes() {
        document.getElementById('color1').style.background = state.color1;
        document.getElementById('color2').style.background = state.color2;
    }

    // ==================== EVENT LISTENERS ====================
    function setupEventListeners() {
        // Canvas events - Mouse
        mainCanvas.addEventListener('mousedown', handleMouseDown);
        mainCanvas.addEventListener('mousemove', handleMouseMove);
        mainCanvas.addEventListener('mouseup', handleMouseUp);
        mainCanvas.addEventListener('mouseleave', handleMouseUp);
        mainCanvas.addEventListener('contextmenu', (e) => e.preventDefault());

        // Canvas events - Touch support
        mainCanvas.addEventListener('touchstart', handleTouchStart, { passive: false });
        mainCanvas.addEventListener('touchmove', handleTouchMove, { passive: false });
        mainCanvas.addEventListener('touchend', handleTouchEnd, { passive: false });
        mainCanvas.addEventListener('touchcancel', handleTouchEnd, { passive: false });

        // Tool buttons
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                commitFloatingSelection();
                selectTool(btn.id.replace('tool-', ''));
            });
        });

        // Shape buttons
        document.querySelectorAll('.shape-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                commitFloatingSelection();
                selectShape(btn.dataset.shape);
            });
        });

        // Ribbon tabs
        document.querySelectorAll('.ribbon-tab').forEach(tab => {
            tab.addEventListener('click', () => switchTab(tab.dataset.tab));
        });

        // File menu
        document.getElementById('file-menu-btn').addEventListener('click', toggleFileMenu);
        document.getElementById('menu-new').addEventListener('click', () => { hideFileMenu(); newFile(); });
        document.getElementById('menu-open').addEventListener('click', () => { hideFileMenu(); openFile(); });
        document.getElementById('menu-save').addEventListener('click', () => { hideFileMenu(); saveFile(); });
        document.getElementById('menu-save-as').addEventListener('click', () => { hideFileMenu(); saveFileAs(); });
        document.getElementById('menu-print').addEventListener('click', () => { hideFileMenu(); printFile(); });
        document.getElementById('menu-camera').addEventListener('click', () => { hideFileMenu(); openCamera(); });
        document.getElementById('menu-copy-image').addEventListener('click', () => { hideFileMenu(); copyWholeImage(); });
        const shareItem = document.getElementById('menu-share');
        shareItem.addEventListener('click', () => { hideFileMenu(); shareImage(); });
        try {
            const probe = new File([new Blob([new Uint8Array(4)], { type: 'image/png' })], 'p.png', { type: 'image/png' });
            if (navigator.canShare && navigator.canShare({ files: [probe] })) shareItem.classList.remove('hidden');
        } catch (e) {}
        document.getElementById('menu-email').addEventListener('click', () => { hideFileMenu(); sendEmail(); });
        document.getElementById('menu-wallpaper').addEventListener('click', () => { hideFileMenu(); setAsWallpaper(); });
        document.getElementById('menu-properties').addEventListener('click', () => { hideFileMenu(); showProperties(); });
        document.getElementById('menu-about').addEventListener('click', () => { hideFileMenu(); showAbout(); });
        document.getElementById('menu-exit').addEventListener('click', () => { hideFileMenu(); exitApp(); });

        // Help button
        document.getElementById('help-btn').addEventListener('click', showAbout);

        // Quick access
        document.getElementById('qat-save').addEventListener('click', saveFile);
        document.getElementById('qat-undo').addEventListener('click', undo);
        document.getElementById('qat-redo').addEventListener('click', redo);

        // Clipboard
        document.getElementById('btn-paste').addEventListener('click', (e) => toggleDropdown(e, 'paste-dropdown'));
        document.getElementById('btn-cut').addEventListener('click', cut);
        document.getElementById('btn-copy').addEventListener('click', copy);

        // Select dropdown
        document.getElementById('btn-select').addEventListener('click', (e) => toggleDropdown(e, 'select-dropdown'));

        // Rotate dropdown
        document.getElementById('btn-rotate').addEventListener('click', (e) => toggleDropdown(e, 'rotate-dropdown'));

        // Brushes
        document.getElementById('btn-brushes').addEventListener('click', (e) => toggleDropdown(e, 'brushes-dropdown'));
        document.querySelectorAll('.brush-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                state.currentBrush = btn.dataset.brush;
                state.currentTool = 'brush';
                updateToolButtons();
                updateBrushesButtonIcon();
                updateCursor();
                hideAllDropdowns();
            });
        });

        // Size
        document.getElementById('btn-size').addEventListener('click', (e) => toggleDropdown(e, 'size-dropdown'));
        document.querySelectorAll('.size-option').forEach(btn => {
            btn.addEventListener('click', () => {
                state.lineWidth = parseInt(btn.dataset.size);
                updateSizeButtons();
                hideAllDropdowns();
            });
        });

        // Outline and Fill
        document.getElementById('btn-outline').addEventListener('click', (e) => toggleDropdown(e, 'outline-dropdown'));
        document.getElementById('btn-fill').addEventListener('click', (e) => toggleDropdown(e, 'fill-dropdown'));

        document.querySelectorAll('#outline-dropdown .menu-item').forEach(btn => {
            btn.addEventListener('click', () => {
                state.shapeOutline = btn.dataset.outline;
                updateOutlineFillButtons();
                hideAllDropdowns();
            });
        });

        document.querySelectorAll('#fill-dropdown .menu-item').forEach(btn => {
            btn.addEventListener('click', () => {
                state.shapeFill = btn.dataset.fill;
                updateOutlineFillButtons();
                hideAllDropdowns();
            });
        });

        // Resize and Crop
        document.getElementById('btn-resize').addEventListener('click', showResizeDialog);
        document.getElementById('btn-crop').addEventListener('click', cropToSelection);

        // View tab
        document.getElementById('btn-zoom-in').addEventListener('click', () => setZoom(state.zoom * 2));
        document.getElementById('btn-zoom-out').addEventListener('click', () => setZoom(state.zoom / 2));
        document.getElementById('btn-zoom-100').addEventListener('click', () => setZoom(1));
        document.getElementById('btn-fullscreen').addEventListener('click', toggleFullscreen);

        document.getElementById('chk-rulers').addEventListener('change', (e) => {
            state.showRulers = e.target.checked;
            document.getElementById('ruler-horizontal').classList.toggle('hidden', !state.showRulers);
            document.getElementById('ruler-vertical').classList.toggle('hidden', !state.showRulers);
            if (state.showRulers) {
                drawRulers();
            }
        });

        document.getElementById('chk-statusbar').addEventListener('change', (e) => {
            state.showStatusBar = e.target.checked;
            document.getElementById('status-bar').classList.toggle('hidden', !state.showStatusBar);
        });

        document.getElementById('chk-gridlines').addEventListener('change', (e) => {
            state.showGridlines = e.target.checked;
            drawGridlines();
        });

        // Mirror mode checkboxes
        document.getElementById('chk-mirror-h').addEventListener('change', (e) => {
            state.mirrorHorizontal = e.target.checked;
            drawMirrorGuide();
        });

        document.getElementById('chk-mirror-v').addEventListener('change', (e) => {
            state.mirrorVertical = e.target.checked;
            drawMirrorGuide();
        });

        // Status bar zoom
        document.getElementById('status-zoom-in').addEventListener('click', () => setZoom(state.zoom * 1.25));
        document.getElementById('status-zoom-out').addEventListener('click', () => setZoom(state.zoom / 1.25));
        document.getElementById('status-zoom-slider').addEventListener('input', (e) => {
            setZoom(e.target.value / 100);
        });

        // Colors
        document.getElementById('color1').addEventListener('click', () => openColorPicker(1));
        document.getElementById('color2').addEventListener('click', () => openColorPicker(2));
        document.getElementById('btn-edit-colors').addEventListener('click', () => openColorPicker(1));

        // Rotate actions
        document.querySelectorAll('#rotate-dropdown .menu-item').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                if (action === 'rotate-right') rotateImage(90);
                else if (action === 'rotate-left') rotateImage(-90);
                else if (action === 'rotate-180') rotateImage(180);
                else if (action === 'flip-h') flipImage('horizontal');
                else if (action === 'flip-v') flipImage('vertical');
                hideAllDropdowns();
            });
        });

        // Select actions
        document.querySelectorAll('#select-dropdown .menu-item').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                if (action === 'rect-select') {
                    state.selectionMode = 'rect';
                    state.currentTool = 'select';
                    updateToolButtons();
                } else if (action === 'free-select') {
                    state.selectionMode = 'free';
                    state.currentTool = 'select';
                    updateToolButtons();
                } else if (action === 'select-all') {
                    selectAll();
                } else if (action === 'invert-select') {
                    invertSelection();
                } else if (action === 'delete-select') {
                    deleteSelection();
                }
                hideAllDropdowns();
            });
        });

        document.getElementById('transparent-select').addEventListener('change', (e) => {
            state.isTransparentSelection = e.target.checked;
        });

        // Paste actions
        document.querySelectorAll('#paste-dropdown .menu-item').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                if (action === 'paste') paste();
                else if (action === 'paste-from') pasteFromFile();
                hideAllDropdowns();
            });
        });

        // Canvas resize handles
        document.querySelectorAll('.resize-handle').forEach(handle => {
            handle.addEventListener('mousedown', startCanvasResize);
        });

        // Dialogs
        document.querySelectorAll('.dialog-close').forEach(btn => {
            btn.addEventListener('click', closeAllDialogs);
        });

        document.getElementById('resize-ok').addEventListener('click', applyResize);
        document.getElementById('resize-cancel').addEventListener('click', closeAllDialogs);

        // Resize dialog inputs
        document.querySelectorAll('input[name="resize-unit"]').forEach(radio => {
            radio.addEventListener('change', updateResizeUnitLabels);
        });
        document.getElementById('resize-h').addEventListener('input', () => handleResizeAspectRatio('h'));
        document.getElementById('resize-v').addEventListener('input', () => handleResizeAspectRatio('v'));
        document.getElementById('props-ok').addEventListener('click', closeAllDialogs);
        document.getElementById('about-ok').addEventListener('click', closeAllDialogs);
        document.getElementById('color-ok').addEventListener('click', applyColor);
        document.getElementById('color-cancel').addEventListener('click', closeAllDialogs);

        // Camera
        document.getElementById('camera-capture').addEventListener('click', captureCamera);
        document.getElementById('camera-cancel').addEventListener('click', () => {
            stopCamera();
            closeAllDialogs();
        });

        // File input
        document.getElementById('file-input').addEventListener('change', handleFileOpen);
        document.getElementById('paste-file-input').addEventListener('change', handlePasteFromFile);

        // Keyboard shortcuts
        document.addEventListener('keydown', handleKeyboard);

        // Close dropdowns when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.dropdown-menu') && !e.target.closest('.has-dropdown') &&
                !e.target.closest('#file-menu-btn') && !e.target.closest('#file-menu')) {
                hideAllDropdowns();
                hideFileMenu();
            }
        });

        // Text tool - commit on blur unless clicking on text options
        const textInput = document.getElementById('text-input');
        textInput.addEventListener('blur', (e) => {
            // Small delay to check if we're clicking on text options
            setTimeout(() => {
                const activeEl = document.activeElement;
                const textGroup = document.getElementById('text-options-group');
                if (!textGroup || !textGroup.contains(activeEl)) {
                    commitText();
                }
            }, 100);
        });

        // Handle keyboard in text input - stop all events from triggering shortcuts
        textInput.addEventListener('keydown', (e) => {
            e.stopPropagation(); // Don't let key events bubble to main handler
            if (e.key === 'Escape') {
                e.preventDefault();
                commitText();
            }
            // Don't prevent default for normal typing
        });

        textInput.addEventListener('keyup', (e) => {
            e.stopPropagation();
        });

        textInput.addEventListener('keypress', (e) => {
            e.stopPropagation();
        });

        document.getElementById('text-bold').addEventListener('click', () => toggleTextStyle('bold'));
        document.getElementById('text-italic').addEventListener('click', () => toggleTextStyle('italic'));
        document.getElementById('text-underline').addEventListener('click', () => toggleTextStyle('underline'));
        document.getElementById('text-strikethrough').addEventListener('click', () => toggleTextStyle('strikethrough'));
        document.getElementById('text-font').addEventListener('change', (e) => {
            state.textStyles.font = e.target.value;
            updateTextInputStyle();
        });
        document.getElementById('text-size').addEventListener('change', (e) => {
            state.textStyles.size = parseInt(e.target.value);
            updateTextInputStyle();
        });

        // Drag and drop
        canvasContainer.addEventListener('dragover', handleDragOver);
        canvasContainer.addEventListener('dragleave', handleDragLeave);
        canvasContainer.addEventListener('drop', handleDrop);
        document.body.addEventListener('dragover', handleDragOver);
        document.body.addEventListener('drop', handleDrop);
    }

    // ==================== MOUSE HANDLING ====================
    function getCanvasCoords(e) {
        const rect = mainCanvas.getBoundingClientRect();
        let x = (e.clientX - rect.left) / state.zoom;
        let y = (e.clientY - rect.top) / state.zoom;

        // Clamp coordinates to canvas bounds
        x = Math.max(0, Math.min(state.canvasWidth - 1, x));
        y = Math.max(0, Math.min(state.canvasHeight - 1, y));

        return { x, y };
    }

    function handleMouseDown(e) {
        const coords = getCanvasCoords(e);
        const x = coords.x;
        const y = coords.y;

        state.isDrawing = true;
        state.lastX = x;
        state.lastY = y;

        const isRightClick = e.button === 2;
        const color = isRightClick ? state.color2 : state.color1;

        // Check if clicking inside floating selection to move it
        if (state.floatingSelection) {
            const fs = state.floatingSelection;
            if (x >= fs.x && x <= fs.x + fs.width && y >= fs.y && y <= fs.y + fs.height) {
                state.isMovingSelection = true;
                state.selectionStartX = x - fs.x;
                state.selectionStartY = y - fs.y;
                return;
            } else {
                // Clicked outside - commit the floating selection
                commitFloatingSelection();
            }
        }

        // Check if clicking inside existing selection to start moving it
        if (state.selection && !state.floatingSelection && state.currentTool === 'select') {
            const sel = state.selection;
            if (x >= sel.x && x <= sel.x + sel.width && y >= sel.y && y <= sel.y + sel.height) {
                // Lift the selection to make it floating
                liftSelection();
                state.isMovingSelection = true;
                state.selectionStartX = x - state.floatingSelection.x;
                state.selectionStartY = y - state.floatingSelection.y;
                return;
            }
        }

        switch (state.currentTool) {
            case 'pencil':
                if (state.mirrorHorizontal || state.mirrorVertical) {
                    drawMirroredPoint(x, y, color, state.lineWidth, 'round');
                } else {
                    mainCtx.beginPath();
                    mainCtx.moveTo(x, y);
                    mainCtx.strokeStyle = color;
                    mainCtx.lineWidth = state.lineWidth;
                    mainCtx.lineCap = 'round';
                    mainCtx.lineJoin = 'round';
                    mainCtx.lineTo(x + 0.1, y + 0.1);
                    mainCtx.stroke();
                }
                break;

            case 'brush':
                drawBrushStroke(x, y, color, true);
                break;

            case 'eraser':
                if (state.mirrorHorizontal || state.mirrorVertical) {
                    drawMirroredPoint(x, y, state.color2, state.lineWidth * 3, 'square');
                } else {
                    mainCtx.beginPath();
                    mainCtx.moveTo(x, y);
                    mainCtx.strokeStyle = state.color2;
                    mainCtx.lineWidth = state.lineWidth * 3;
                    mainCtx.lineCap = 'square';
                    mainCtx.lineJoin = 'miter';
                    mainCtx.lineTo(x + 0.1, y + 0.1);
                    mainCtx.stroke();
                }
                break;

            case 'fill':
                floodFill(Math.floor(x), Math.floor(y), color);
                saveHistory();
                break;

            case 'picker':
                pickColor(x, y, isRightClick);
                break;

            case 'magnifier':
                if (isRightClick) {
                    setZoom(state.zoom / 2);
                } else {
                    setZoom(state.zoom * 2);
                }
                break;

            case 'text':
                showTextInput(x, y);
                break;

            case 'select':
                clearSelection();
                if (state.selectionMode === 'rect') {
                    state.selection = { x: x, y: y, width: 0, height: 0, startX: x, startY: y };
                } else {
                    state.freeformPoints = [{ x, y }];
                }
                break;

            default:
                if (state.currentShape) {
                    state.shapeStart = { x, y };
                }
                break;
        }

        updateStatus(x, y);
    }

    function handleMouseMove(e) {
        const coords = getCanvasCoords(e);
        const x = coords.x;
        const y = coords.y;

        updateStatus(x, y);

        if (!state.isDrawing) return;

        const isRightClick = e.buttons === 2;
        const color = isRightClick ? state.color2 : state.color1;

        // Moving floating selection
        if (state.isMovingSelection && state.floatingSelection) {
            state.floatingSelection.x = x - state.selectionStartX;
            state.floatingSelection.y = y - state.selectionStartY;
            state.selection.x = state.floatingSelection.x;
            state.selection.y = state.floatingSelection.y;
            drawFloatingSelection();
            drawSelectionRect();
            return;
        }

        switch (state.currentTool) {
            case 'pencil':
                if (state.mirrorHorizontal || state.mirrorVertical) {
                    drawMirroredStroke(state.lastX, state.lastY, x, y, color, state.lineWidth, 'round', 'round');
                } else {
                    mainCtx.strokeStyle = color;
                    mainCtx.lineWidth = state.lineWidth;
                    mainCtx.lineTo(x, y);
                    mainCtx.stroke();
                    mainCtx.beginPath();
                    mainCtx.moveTo(x, y);
                }
                break;

            case 'brush':
                drawBrushStroke(x, y, color, false);
                break;

            case 'eraser':
                if (state.mirrorHorizontal || state.mirrorVertical) {
                    drawMirroredStroke(state.lastX, state.lastY, x, y, state.color2, state.lineWidth * 3, 'square', 'miter');
                } else {
                    mainCtx.strokeStyle = state.color2;
                    mainCtx.lineWidth = state.lineWidth * 3;
                    mainCtx.lineTo(x, y);
                    mainCtx.stroke();
                    mainCtx.beginPath();
                    mainCtx.moveTo(x, y);
                }
                break;

            case 'select':
                if (state.selectionMode === 'rect' && state.selection) {
                    const startX = state.selection.startX;
                    const startY = state.selection.startY;
                    state.selection.x = Math.min(startX, x);
                    state.selection.y = Math.min(startY, y);
                    state.selection.width = Math.abs(x - startX);
                    state.selection.height = Math.abs(y - startY);
                    drawSelectionRect();
                } else if (state.selectionMode === 'free') {
                    state.freeformPoints.push({ x, y });
                    drawFreeformSelection();
                }
                break;

            default:
                if (state.currentShape && state.shapeStart) {
                    drawShapePreview(x, y, color);
                }
                break;
        }

        state.lastX = x;
        state.lastY = y;
    }

    function handleMouseUp(e) {
        if (!state.isDrawing) return;

        const coords = getCanvasCoords(e);
        const x = coords.x;
        const y = coords.y;
        const isRightClick = e.button === 2;
        const color = isRightClick ? state.color2 : state.color1;

        if (state.isMovingSelection) {
            state.isMovingSelection = false;
            state.isDrawing = false;
            return;
        }

        if (state.currentShape && state.shapeStart) {
            drawShape(state.shapeStart.x, state.shapeStart.y, x, y, color);
            clearPreview();
            state.shapeStart = null;
            saveHistory();
        } else if (state.currentTool === 'pencil' || state.currentTool === 'brush' || state.currentTool === 'eraser') {
            saveHistory();
            // Reset brush tracking for next stroke
            lastBrushX = null;
            lastBrushY = null;
        } else if (state.currentTool === 'select') {
            if (state.selectionMode === 'rect' && state.selection) {
                if (state.selection.width > 1 && state.selection.height > 1) {
                    startSelectionAnimation();
                } else {
                    clearSelection();
                }
            } else if (state.selectionMode === 'free' && state.freeformPoints.length > 2) {
                finalizeFreeformSelection();
                startSelectionAnimation();
            }
        }

        state.isDrawing = false;
    }

    // ==================== TOUCH HANDLING ====================
    function getTouchCoords(e) {
        const touch = e.touches[0] || e.changedTouches[0];
        const rect = mainCanvas.getBoundingClientRect();
        let x = (touch.clientX - rect.left) / state.zoom;
        let y = (touch.clientY - rect.top) / state.zoom;

        // Clamp coordinates to canvas bounds
        x = Math.max(0, Math.min(state.canvasWidth - 1, x));
        y = Math.max(0, Math.min(state.canvasHeight - 1, y));

        return { x, y };
    }

    function handleTouchStart(e) {
        e.preventDefault();
        const fakeEvent = {
            clientX: e.touches[0].clientX,
            clientY: e.touches[0].clientY,
            button: 0,
            buttons: 1
        };
        handleMouseDown(fakeEvent);
    }

    function handleTouchMove(e) {
        e.preventDefault();
        if (!state.isDrawing) return;

        const fakeEvent = {
            clientX: e.touches[0].clientX,
            clientY: e.touches[0].clientY,
            button: 0,
            buttons: 1
        };
        handleMouseMove(fakeEvent);
    }

    function handleTouchEnd(e) {
        e.preventDefault();
        const touch = e.changedTouches[0];
        const fakeEvent = {
            clientX: touch.clientX,
            clientY: touch.clientY,
            button: 0,
            buttons: 0
        };
        handleMouseUp(fakeEvent);
    }

    // ==================== SELECTION SYSTEM ====================
    function liftSelection() {
        if (!state.selection) return;

        const sel = state.selection;
        const x = Math.floor(sel.x);
        const y = Math.floor(sel.y);
        const w = Math.floor(sel.width);
        const h = Math.floor(sel.height);

        if (w <= 0 || h <= 0) return;

        // Create a canvas for the floating selection
        const floatCanvas = document.createElement('canvas');
        floatCanvas.width = w;
        floatCanvas.height = h;
        const floatCtx = floatCanvas.getContext('2d');

        // Handle free-form selection with clipping path
        if (sel.isFreeform && sel.points && sel.points.length > 2) {
            // Create clipping path from free-form points
            floatCtx.beginPath();
            floatCtx.moveTo(sel.points[0].x, sel.points[0].y);
            for (let i = 1; i < sel.points.length; i++) {
                floatCtx.lineTo(sel.points[i].x, sel.points[i].y);
            }
            floatCtx.closePath();
            floatCtx.clip();

            // Draw the selected portion
            floatCtx.drawImage(mainCanvas, x, y, w, h, 0, 0, w, h);

            // Clear the original area with clipping
            mainCtx.save();
            mainCtx.beginPath();
            mainCtx.moveTo(x + sel.points[0].x, y + sel.points[0].y);
            for (let i = 1; i < sel.points.length; i++) {
                mainCtx.lineTo(x + sel.points[i].x, y + sel.points[i].y);
            }
            mainCtx.closePath();
            mainCtx.clip();
            mainCtx.fillStyle = state.color2;
            mainCtx.fillRect(x, y, w, h);
            mainCtx.restore();

            // Store the path for later use
            state.freeformPath = new Path2D();
            state.freeformPath.moveTo(sel.points[0].x, sel.points[0].y);
            for (let i = 1; i < sel.points.length; i++) {
                state.freeformPath.lineTo(sel.points[i].x, sel.points[i].y);
            }
            state.freeformPath.closePath();
        } else {
            // Regular rectangular selection
            const imageData = mainCtx.getImageData(x, y, w, h);
            floatCtx.putImageData(imageData, 0, 0);

            // Fill the original area with background color
            mainCtx.fillStyle = state.color2;
            mainCtx.fillRect(x, y, w, h);

            state.freeformPath = null;
        }

        // Create floating selection
        state.floatingSelection = {
            x: x,
            y: y,
            width: w,
            height: h,
            canvas: floatCanvas,
            isFreeform: sel.isFreeform || false,
            points: sel.points || null
        };

        drawFloatingSelection();
    }

    function drawFloatingSelection() {
        if (!state.floatingSelection) return;

        // Clear and redraw preview canvas with floating selection
        previewCtx.clearRect(0, 0, previewCanvas.width, previewCanvas.height);

        const fs = state.floatingSelection;

        if (state.isTransparentSelection) {
            // Draw with transparency (white = transparent)
            const tempCanvas = document.createElement('canvas');
            tempCanvas.width = fs.width;
            tempCanvas.height = fs.height;
            const tempCtx = tempCanvas.getContext('2d');
            tempCtx.drawImage(fs.canvas, 0, 0);

            const imgData = tempCtx.getImageData(0, 0, fs.width, fs.height);
            const data = imgData.data;

            for (let i = 0; i < data.length; i += 4) {
                // If pixel is white (or very close), make it transparent
                if (data[i] > 250 && data[i + 1] > 250 && data[i + 2] > 250) {
                    data[i + 3] = 0;
                }
            }

            tempCtx.putImageData(imgData, 0, 0);
            previewCtx.drawImage(tempCanvas, fs.x, fs.y);
        } else {
            previewCtx.drawImage(fs.canvas, fs.x, fs.y);
        }
    }

    function commitFloatingSelection() {
        if (!state.floatingSelection) return;

        const fs = state.floatingSelection;

        if (state.isTransparentSelection) {
            // Draw with transparency
            const tempCanvas = document.createElement('canvas');
            tempCanvas.width = fs.width;
            tempCanvas.height = fs.height;
            const tempCtx = tempCanvas.getContext('2d');
            tempCtx.drawImage(fs.canvas, 0, 0);

            const imgData = tempCtx.getImageData(0, 0, fs.width, fs.height);
            const data = imgData.data;

            for (let i = 0; i < data.length; i += 4) {
                if (data[i] > 250 && data[i + 1] > 250 && data[i + 2] > 250) {
                    data[i + 3] = 0;
                }
            }

            tempCtx.putImageData(imgData, 0, 0);
            mainCtx.drawImage(tempCanvas, fs.x, fs.y);
        } else {
            mainCtx.drawImage(fs.canvas, fs.x, fs.y);
        }

        previewCtx.clearRect(0, 0, previewCanvas.width, previewCanvas.height);
        state.floatingSelection = null;
        clearSelection();
        saveHistory();
    }

    function drawSelectionRect() {
        selectionCtx.clearRect(0, 0, selectionCanvas.width, selectionCanvas.height);

        if (!state.selection) {
            stopSelectionAnimation();
            return;
        }

        const { x, y, width, height } = state.selection;

        if (width <= 0 || height <= 0) return;

        // Draw white background line
        selectionCtx.setLineDash([]);
        selectionCtx.strokeStyle = '#FFF';
        selectionCtx.lineWidth = 1;
        selectionCtx.strokeRect(x + 0.5, y + 0.5, width - 1, height - 1);

        // Draw marching ants
        selectionCtx.setLineDash([4, 4]);
        selectionCtx.strokeStyle = '#000';
        selectionCtx.lineDashOffset = -marchingAntsOffset;
        selectionCtx.strokeRect(x + 0.5, y + 0.5, width - 1, height - 1);
    }

    function drawFreeformSelection() {
        selectionCtx.clearRect(0, 0, selectionCanvas.width, selectionCanvas.height);

        if (state.freeformPoints.length < 2) return;

        selectionCtx.beginPath();
        selectionCtx.moveTo(state.freeformPoints[0].x, state.freeformPoints[0].y);

        for (let i = 1; i < state.freeformPoints.length; i++) {
            selectionCtx.lineTo(state.freeformPoints[i].x, state.freeformPoints[i].y);
        }

        selectionCtx.setLineDash([4, 4]);
        selectionCtx.strokeStyle = '#000';
        selectionCtx.lineWidth = 1;
        selectionCtx.stroke();
    }

    function finalizeFreeformSelection() {
        if (state.freeformPoints.length < 3) return;

        // Calculate bounding box
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        for (const p of state.freeformPoints) {
            minX = Math.min(minX, p.x);
            minY = Math.min(minY, p.y);
            maxX = Math.max(maxX, p.x);
            maxY = Math.max(maxY, p.y);
        }

        state.selection = {
            x: Math.floor(minX),
            y: Math.floor(minY),
            width: Math.ceil(maxX - minX),
            height: Math.ceil(maxY - minY),
            isFreeform: true,
            points: state.freeformPoints.map(p => ({ x: p.x - minX, y: p.y - minY }))
        };

        state.freeformPoints = [];
        drawSelectionRect();
    }

    function animateSelection() {
        if (!state.selection) {
            stopSelectionAnimation();
            return;
        }

        marchingAntsOffset = (marchingAntsOffset + 0.5) % 8;
        drawSelectionRect();
        selectionAnimationId = requestAnimationFrame(animateSelection);
    }

    function startSelectionAnimation() {
        if (!selectionAnimationId && state.selection) {
            animateSelection();
        }
    }

    function stopSelectionAnimation() {
        if (selectionAnimationId) {
            cancelAnimationFrame(selectionAnimationId);
            selectionAnimationId = null;
            marchingAntsOffset = 0;
        }
    }

    function selectAll() {
        commitFloatingSelection();
        state.selection = {
            x: 0,
            y: 0,
            width: state.canvasWidth,
            height: state.canvasHeight
        };
        drawSelectionRect();
        startSelectionAnimation();
    }

    function invertSelection() {
        // Invert colors within the selected area (or entire canvas if no selection)
        let x, y, width, height;

        if (state.floatingSelection) {
            // Invert the floating selection
            const floatCtx = state.floatingSelection.canvas.getContext('2d');
            const imageData = floatCtx.getImageData(0, 0, state.floatingSelection.canvas.width, state.floatingSelection.canvas.height);
            invertImageData(imageData);
            floatCtx.putImageData(imageData, 0, 0);
            // Redraw preview
            previewCtx.clearRect(0, 0, previewCanvas.width, previewCanvas.height);
            previewCtx.drawImage(state.floatingSelection.canvas, state.floatingSelection.x, state.floatingSelection.y);
            return;
        }

        if (state.selection) {
            x = state.selection.x;
            y = state.selection.y;
            width = state.selection.width;
            height = state.selection.height;
        } else {
            // Invert entire canvas if no selection
            x = 0;
            y = 0;
            width = state.canvasWidth;
            height = state.canvasHeight;
        }

        // Get the image data for the selection area
        const imageData = mainCtx.getImageData(x, y, width, height);
        invertImageData(imageData);
        mainCtx.putImageData(imageData, x, y);
        saveHistory();
    }

    function invertImageData(imageData) {
        const data = imageData.data;
        for (let i = 0; i < data.length; i += 4) {
            // Invert RGB values (255 - value), keep alpha unchanged
            data[i] = 255 - data[i];         // Red
            data[i + 1] = 255 - data[i + 1]; // Green
            data[i + 2] = 255 - data[i + 2]; // Blue
            // data[i + 3] stays the same (Alpha)
        }
    }

    function deleteSelection() {
        if (state.floatingSelection) {
            // Just discard the floating selection
            previewCtx.clearRect(0, 0, previewCanvas.width, previewCanvas.height);
            state.floatingSelection = null;
            clearSelection();
            saveHistory();
            return;
        }

        if (!state.selection) return;

        const { x, y, width, height } = state.selection;
        mainCtx.fillStyle = state.color2;
        mainCtx.fillRect(x, y, width, height);

        clearSelection();
        saveHistory();
    }

    function clearSelection() {
        state.selection = null;
        state.floatingSelection = null;
        state.freeformPoints = [];
        stopSelectionAnimation();
        selectionCtx.clearRect(0, 0, selectionCanvas.width, selectionCanvas.height);
        previewCtx.clearRect(0, 0, previewCanvas.width, previewCanvas.height);
    }

    function cropToSelection() {
        if (state.floatingSelection) {
            commitFloatingSelection();
        }

        if (!state.selection) return;

        const { x, y, width, height } = state.selection;
        const imageData = mainCtx.getImageData(x, y, width, height);

        resizeAllCanvases(width, height, false);
        mainCtx.putImageData(imageData, 0, 0);

        clearSelection();
        saveHistory();
    }

    // ==================== CLIPBOARD ====================
    function showToast(msg, ms = 1800) {
        const t = document.getElementById('toast');
        if (!t) return;
        t.textContent = msg;
        t.classList.remove('hidden');
        clearTimeout(showToast._timer);
        showToast._timer = setTimeout(() => t.classList.add('hidden'), ms);
    }

    // Copy the whole picture to the system clipboard (File > Copy image, or Copy with nothing selected)
    function copyWholeImage() {
        commitFloatingSelection();
        state.clipboardData = null;
        try {
            mainCanvas.toBlob(blob => {
                if (!blob || !navigator.clipboard || !window.ClipboardItem) {
                    showToast('Copy not supported here. Use File > Save instead.');
                    return;
                }
                navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
                    .then(() => showToast('Picture copied. Paste it anywhere.'))
                    .catch(() => showToast('Copy blocked by the browser. Use File > Save instead.'));
            }, 'image/png');
        } catch (e) {
            showToast('Copy not supported here. Use File > Save instead.');
        }
    }

    // Phone/tablet share sheet (Web Share API with files)
    function shareImage() {
        commitFloatingSelection();
        mainCanvas.toBlob(blob => {
            if (!blob) return;
            const file = new File([blob], (state.fileName || 'Untitled') + '.png', { type: 'image/png' });
            if (navigator.canShare && navigator.canShare({ files: [file] })) {
                navigator.share({ files: [file], title: 'MattPaint' }).catch(() => {});
            } else {
                showToast('Sharing not supported here. Use File > Save instead.');
            }
        }, 'image/png');
    }

    function copy() {
        if (!state.floatingSelection && !state.selection) {
            copyWholeImage();
            return;
        }
        if (state.floatingSelection) {
            state.clipboardData = {
                width: state.floatingSelection.width,
                height: state.floatingSelection.height,
                canvas: state.floatingSelection.canvas
            };
        } else if (state.selection) {
            const { x, y, width, height } = state.selection;
            const imageData = mainCtx.getImageData(x, y, width, height);

            const tempCanvas = document.createElement('canvas');
            tempCanvas.width = width;
            tempCanvas.height = height;
            tempCanvas.getContext('2d').putImageData(imageData, 0, 0);

            state.clipboardData = {
                width: width,
                height: height,
                canvas: tempCanvas
            };

            // Try to copy to system clipboard
            try {
                tempCanvas.toBlob(blob => {
                    if (blob) {
                        navigator.clipboard.write([
                            new ClipboardItem({ 'image/png': blob })
                        ]).catch(() => {});
                    }
                });
            } catch (e) {}
        }
    }

    function cut() {
        copy();
        deleteSelection();
    }

    function paste() {
        commitFloatingSelection();

        // Try system clipboard first
        navigator.clipboard.read().then(items => {
            for (const item of items) {
                for (const type of item.types) {
                    if (type.startsWith('image/')) {
                        item.getType(type).then(blob => {
                            const img = new Image();
                            img.onload = () => {
                                pasteImage(img);
                                URL.revokeObjectURL(img.src);
                            };
                            img.src = URL.createObjectURL(blob);
                        });
                        return;
                    }
                }
            }
            // No image in system clipboard, use internal
            pasteInternal();
        }).catch(() => {
            pasteInternal();
        });
    }

    function pasteInternal() {
        if (!state.clipboardData) return;

        const clip = state.clipboardData;

        // Expand canvas if needed
        if (clip.width > state.canvasWidth || clip.height > state.canvasHeight) {
            resizeAllCanvases(
                Math.max(state.canvasWidth, clip.width),
                Math.max(state.canvasHeight, clip.height),
                true
            );
        }

        // Create floating selection
        state.floatingSelection = {
            x: 0,
            y: 0,
            width: clip.width,
            height: clip.height,
            canvas: clip.canvas
        };

        state.selection = {
            x: 0,
            y: 0,
            width: clip.width,
            height: clip.height
        };

        drawFloatingSelection();
        drawSelectionRect();
        startSelectionAnimation();
    }

    function pasteImage(img) {
        try {
            const imgW = img.naturalWidth || img.width;
            const imgH = img.naturalHeight || img.height;

            // Validate image dimensions
            if (!imgW || !imgH || imgW < 1 || imgH < 1) {
                console.error('Invalid image dimensions');
                return;
            }

            // Limit maximum paste size
            const maxPasteSize = MAX_CANVAS_SIZE;
            const pasteW = Math.min(imgW, maxPasteSize);
            const pasteH = Math.min(imgH, maxPasteSize);

            // Expand canvas if needed
            if (pasteW > state.canvasWidth || pasteH > state.canvasHeight) {
                resizeAllCanvases(
                    Math.max(state.canvasWidth, pasteW),
                    Math.max(state.canvasHeight, pasteH),
                    true
                );
            }

            // Create temp canvas for the image
            const tempCanvas = document.createElement('canvas');
            tempCanvas.width = pasteW;
            tempCanvas.height = pasteH;
            tempCanvas.getContext('2d').drawImage(img, 0, 0, pasteW, pasteH);

            // Create floating selection
            state.floatingSelection = {
                x: 0,
                y: 0,
                width: pasteW,
                height: pasteH,
                canvas: tempCanvas
            };

            state.selection = {
                x: 0,
                y: 0,
                width: pasteW,
                height: pasteH
            };

            drawFloatingSelection();
            drawSelectionRect();
            startSelectionAnimation();
        } catch (error) {
            console.error('Error pasting image:', error);
        }
    }

    function pasteFromFile() {
        document.getElementById('paste-file-input').click();
    }

    function handlePasteFromFile(e) {
        const file = e.target.files[0];
        if (!file) return;

        // Validate file type
        if (!file.type.startsWith('image/')) {
            alert('Please select a valid image file.');
            e.target.value = '';
            return;
        }

        const img = new Image();
        img.onload = () => {
            pasteImage(img);
            URL.revokeObjectURL(img.src);
        };
        img.onerror = () => {
            console.error('Failed to load image for paste');
            alert('Failed to load image. The file may be corrupted or unsupported.');
            URL.revokeObjectURL(img.src);
        };
        img.src = URL.createObjectURL(file);
        e.target.value = '';
    }

    // ==================== ROTATE/FLIP ====================
    function rotateImage(degrees) {
        if (state.floatingSelection) {
            rotateFloatingSelection(degrees);
        } else if (state.selection) {
            // Lift, rotate, keep floating
            liftSelection();
            rotateFloatingSelection(degrees);
        } else {
            rotateCanvas(degrees);
        }
    }

    function flipImage(direction) {
        if (state.floatingSelection) {
            flipFloatingSelection(direction);
        } else if (state.selection) {
            liftSelection();
            flipFloatingSelection(direction);
        } else {
            flipCanvas(direction);
        }
    }

    function rotateFloatingSelection(degrees) {
        if (!state.floatingSelection) return;

        const fs = state.floatingSelection;
        const oldCanvas = fs.canvas;

        const rad = degrees * Math.PI / 180;
        const sin = Math.abs(Math.sin(rad));
        const cos = Math.abs(Math.cos(rad));

        const newW = Math.floor(fs.width * cos + fs.height * sin);
        const newH = Math.floor(fs.width * sin + fs.height * cos);

        const newCanvas = document.createElement('canvas');
        newCanvas.width = newW;
        newCanvas.height = newH;
        const newCtx = newCanvas.getContext('2d');

        newCtx.translate(newW / 2, newH / 2);
        newCtx.rotate(rad);
        newCtx.drawImage(oldCanvas, -fs.width / 2, -fs.height / 2);

        fs.canvas = newCanvas;
        fs.width = newW;
        fs.height = newH;
        state.selection.width = newW;
        state.selection.height = newH;

        drawFloatingSelection();
        drawSelectionRect();
    }

    function flipFloatingSelection(direction) {
        if (!state.floatingSelection) return;

        const fs = state.floatingSelection;
        const oldCanvas = fs.canvas;

        const newCanvas = document.createElement('canvas');
        newCanvas.width = fs.width;
        newCanvas.height = fs.height;
        const newCtx = newCanvas.getContext('2d');

        if (direction === 'horizontal') {
            newCtx.translate(fs.width, 0);
            newCtx.scale(-1, 1);
        } else {
            newCtx.translate(0, fs.height);
            newCtx.scale(1, -1);
        }
        newCtx.drawImage(oldCanvas, 0, 0);

        fs.canvas = newCanvas;
        drawFloatingSelection();
    }

    function rotateCanvas(degrees) {
        const tempCanvas = document.createElement('canvas');
        const tempCtx = tempCanvas.getContext('2d');

        let newW, newH;
        if (degrees === 90 || degrees === -90) {
            newW = state.canvasHeight;
            newH = state.canvasWidth;
        } else {
            newW = state.canvasWidth;
            newH = state.canvasHeight;
        }

        tempCanvas.width = newW;
        tempCanvas.height = newH;

        tempCtx.translate(newW / 2, newH / 2);
        tempCtx.rotate(degrees * Math.PI / 180);
        tempCtx.drawImage(mainCanvas, -state.canvasWidth / 2, -state.canvasHeight / 2);

        resizeAllCanvases(newW, newH, false);
        mainCtx.drawImage(tempCanvas, 0, 0);
        saveHistory();
    }

    function flipCanvas(direction) {
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = state.canvasWidth;
        tempCanvas.height = state.canvasHeight;
        const tempCtx = tempCanvas.getContext('2d');

        if (direction === 'horizontal') {
            tempCtx.translate(state.canvasWidth, 0);
            tempCtx.scale(-1, 1);
        } else {
            tempCtx.translate(0, state.canvasHeight);
            tempCtx.scale(1, -1);
        }
        tempCtx.drawImage(mainCanvas, 0, 0);

        mainCtx.clearRect(0, 0, state.canvasWidth, state.canvasHeight);
        mainCtx.drawImage(tempCanvas, 0, 0);
        saveHistory();
    }

    // ==================== SHAPES ====================
    function selectShape(shape) {
        // Stop selection animation when switching to shape tool
        if (state.currentTool === 'select') {
            stopSelectionAnimation();
            clearSelection();
        }

        state.currentShape = shape;
        state.currentTool = 'shape';

        document.querySelectorAll('.shape-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.shape === shape);
        });
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        updateCursor();
        updateToolStatus();
    }

    function drawShapePreview(x, y, color) {
        clearPreview();
        drawShapeOnContext(previewCtx, state.shapeStart.x, state.shapeStart.y, x, y, color);
    }

    function drawShape(x1, y1, x2, y2, color) {
        drawShapeOnContext(mainCtx, x1, y1, x2, y2, color);
    }

    function applyBrushStyle(ctx, style, color) {
        // Apply different brush textures for shape outline/fill
        const rgb = hexToRgb(color);
        switch (style) {
            case 'crayon':
                // Rough crayon texture pattern
                const crayonPattern = ctx.createPattern(createTextureCanvas('crayon', color), 'repeat');
                if (crayonPattern) ctx.strokeStyle = crayonPattern;
                break;
            case 'marker':
                ctx.strokeStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.6)`;
                ctx.lineWidth = state.lineWidth * 2;
                break;
            case 'oil':
                ctx.lineWidth = state.lineWidth * 1.5;
                break;
            case 'pencil':
                ctx.lineWidth = Math.max(1, state.lineWidth * 0.5);
                break;
            case 'watercolor':
                ctx.strokeStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.4)`;
                ctx.lineWidth = state.lineWidth * 2;
                break;
        }
    }

    function createTextureCanvas(type, color) {
        const texCanvas = document.createElement('canvas');
        texCanvas.width = 8;
        texCanvas.height = 8;
        const texCtx = texCanvas.getContext('2d');
        const rgb = hexToRgb(color);

        switch (type) {
            case 'crayon':
                // Create crayon-like dots pattern
                texCtx.fillStyle = color;
                for (let i = 0; i < 12; i++) {
                    const x = Math.random() * 8;
                    const y = Math.random() * 8;
                    const alpha = 0.5 + Math.random() * 0.5;
                    texCtx.fillStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${alpha})`;
                    texCtx.fillRect(x, y, 1, 1);
                }
                break;
        }

        return texCanvas;
    }

    function drawShapeOnContext(ctx, x1, y1, x2, y2, strokeColor) {
        ctx.save();
        ctx.lineWidth = state.lineWidth;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        // Apply stroke style based on outline setting
        ctx.strokeStyle = strokeColor;
        if (state.shapeOutline !== 'none' && state.shapeOutline !== 'solid') {
            // Apply textured stroke
            applyBrushStyle(ctx, state.shapeOutline, strokeColor);
        }

        // Apply fill style based on fill setting
        ctx.fillStyle = state.color2;
        if (state.shapeFill !== 'none' && state.shapeFill !== 'solid') {
            // Apply textured fill
            applyBrushStyle(ctx, state.shapeFill, state.color2);
        }

        const width = x2 - x1;
        const height = y2 - y1;
        const centerX = (x1 + x2) / 2;
        const centerY = (y1 + y2) / 2;

        ctx.beginPath();

        switch (state.currentShape) {
            case 'line':
                ctx.moveTo(x1, y1);
                ctx.lineTo(x2, y2);
                break;
            case 'curve':
                ctx.moveTo(x1, y1);
                // Curve direction based on drag direction
                const curveOffset = height < 0 ? Math.abs(height) : -Math.abs(height);
                ctx.quadraticCurveTo(centerX, centerY + curveOffset, x2, y2);
                break;
            case 'oval':
                ctx.ellipse(centerX, centerY, Math.abs(width/2), Math.abs(height/2), 0, 0, Math.PI * 2);
                break;
            case 'rect':
                ctx.rect(x1, y1, width, height);
                break;
            case 'roundrect':
                drawRoundRect(ctx, x1, y1, width, height, Math.min(Math.abs(width), Math.abs(height)) * 0.2);
                break;
            case 'polygon':
                drawPolygon(ctx, centerX, centerY, Math.min(Math.abs(width), Math.abs(height)) / 2, 5);
                break;
            case 'triangle':
                ctx.moveTo(centerX, y1);
                ctx.lineTo(x2, y2);
                ctx.lineTo(x1, y2);
                ctx.closePath();
                break;
            case 'rtriangle':
                ctx.moveTo(x1, y1);
                ctx.lineTo(x1, y2);
                ctx.lineTo(x2, y2);
                ctx.closePath();
                break;
            case 'diamond':
                ctx.moveTo(centerX, y1);
                ctx.lineTo(x2, centerY);
                ctx.lineTo(centerX, y2);
                ctx.lineTo(x1, centerY);
                ctx.closePath();
                break;
            case 'star5':
                drawStar(ctx, centerX, centerY, 5, Math.min(Math.abs(width), Math.abs(height)) / 2);
                break;
            case 'star6':
                drawStar(ctx, centerX, centerY, 6, Math.min(Math.abs(width), Math.abs(height)) / 2);
                break;
            case 'arrow-right':
            case 'arrow-left':
            case 'arrow-up':
            case 'arrow-down':
                drawArrow(ctx, x1, y1, x2, y2, state.currentShape.replace('arrow-', ''));
                break;
            case 'heart':
                drawHeart(ctx, centerX, y1, Math.abs(width), Math.abs(height));
                break;
            case 'lightning':
                drawLightning(ctx, x1, y1, x2, y2);
                break;
        }

        if (state.shapeFill !== 'none' && state.currentShape !== 'line' && state.currentShape !== 'curve') {
            ctx.fill();
        }
        if (state.shapeOutline !== 'none') {
            ctx.stroke();
        }

        ctx.restore();
    }

    function drawRoundRect(ctx, x, y, w, h, r) {
        if (w < 0) { x += w; w = -w; }
        if (h < 0) { y += h; h = -h; }
        r = Math.min(r, w/2, h/2);
        ctx.moveTo(x + r, y);
        ctx.arcTo(x + w, y, x + w, y + h, r);
        ctx.arcTo(x + w, y + h, x, y + h, r);
        ctx.arcTo(x, y + h, x, y, r);
        ctx.arcTo(x, y, x + w, y, r);
        ctx.closePath();
    }

    function drawPolygon(ctx, cx, cy, r, sides) {
        for (let i = 0; i <= sides; i++) {
            const angle = (i * 2 * Math.PI / sides) - Math.PI/2;
            if (i === 0) ctx.moveTo(cx + r * Math.cos(angle), cy + r * Math.sin(angle));
            else ctx.lineTo(cx + r * Math.cos(angle), cy + r * Math.sin(angle));
        }
    }

    function drawStar(ctx, cx, cy, points, r) {
        const innerR = r * 0.4;
        for (let i = 0; i < points * 2; i++) {
            const radius = i % 2 === 0 ? r : innerR;
            const angle = (i * Math.PI / points) - Math.PI/2;
            if (i === 0) ctx.moveTo(cx + radius * Math.cos(angle), cy + radius * Math.sin(angle));
            else ctx.lineTo(cx + radius * Math.cos(angle), cy + radius * Math.sin(angle));
        }
        ctx.closePath();
    }

    function drawArrow(ctx, x1, y1, x2, y2, dir) {
        const w = Math.abs(x2 - x1);
        const h = Math.abs(y2 - y1);
        const minX = Math.min(x1, x2);
        const minY = Math.min(y1, y2);

        const points = {
            right: [[0.6,0], [1,0.5], [0.6,1], [0.6,0.7], [0,0.7], [0,0.3], [0.6,0.3]],
            left: [[0.4,0], [0,0.5], [0.4,1], [0.4,0.7], [1,0.7], [1,0.3], [0.4,0.3]],
            up: [[0,0.4], [0.5,0], [1,0.4], [0.7,0.4], [0.7,1], [0.3,1], [0.3,0.4]],
            down: [[0,0.6], [0.5,1], [1,0.6], [0.7,0.6], [0.7,0], [0.3,0], [0.3,0.6]]
        };

        const pts = points[dir];
        ctx.moveTo(minX + pts[0][0] * w, minY + pts[0][1] * h);
        for (let i = 1; i < pts.length; i++) {
            ctx.lineTo(minX + pts[i][0] * w, minY + pts[i][1] * h);
        }
        ctx.closePath();
    }

    function drawHeart(ctx, cx, top, w, h) {
        const x = cx - w/2;
        const y = top;
        ctx.moveTo(cx, y + h * 0.3);
        ctx.bezierCurveTo(cx, y, x, y, x, y + h * 0.3);
        ctx.bezierCurveTo(x, y + h * 0.6, cx, y + h * 0.9, cx, y + h);
        ctx.bezierCurveTo(cx, y + h * 0.9, x + w, y + h * 0.6, x + w, y + h * 0.3);
        ctx.bezierCurveTo(x + w, y, cx, y, cx, y + h * 0.3);
    }

    function drawLightning(ctx, x1, y1, x2, y2) {
        const w = x2 - x1;
        const h = y2 - y1;
        ctx.moveTo(x1 + w * 0.6, y1);
        ctx.lineTo(x1 + w * 0.2, y1 + h * 0.45);
        ctx.lineTo(x1 + w * 0.45, y1 + h * 0.45);
        ctx.lineTo(x1 + w * 0.25, y2);
        ctx.lineTo(x1 + w * 0.8, y1 + h * 0.4);
        ctx.lineTo(x1 + w * 0.55, y1 + h * 0.4);
        ctx.closePath();
    }

    function clearPreview() {
        if (!state.floatingSelection) {
            previewCtx.clearRect(0, 0, previewCanvas.width, previewCanvas.height);
        }
    }

    // ==================== TOOLS ====================
    function selectTool(tool) {
        // Commit any existing text before switching tools
        if (state.currentTool === 'text' && tool !== 'text') {
            commitText();
        }

        // Stop selection animation when switching away from select tool
        if (state.currentTool === 'select' && tool !== 'select') {
            stopSelectionAnimation();
            clearSelection();
        }

        state.currentTool = tool;
        state.currentShape = null;
        if (tool === 'select') {
            state.selectionMode = 'rect';
        }
        updateToolButtons();
        updateCursor();
        updateTextOptionsVisibility();
        updateToolStatus();
    }

    function updateTextOptionsVisibility() {
        // Font tools are now always visible - no hiding needed
    }

    function updateToolButtons() {
        // Update tool buttons
        document.querySelectorAll('.tool-btn').forEach(btn => {
            const toolName = btn.id.replace('tool-', '');
            btn.classList.toggle('active', toolName === state.currentTool);
        });

        // Update shape buttons
        document.querySelectorAll('.shape-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.shape === state.currentShape);
        });

        // Update brushes button - show as active when brush tool is selected
        const brushesBtn = document.getElementById('btn-brushes');
        if (brushesBtn) {
            brushesBtn.classList.toggle('active', state.currentTool === 'brush');
        }

        // Update brush buttons in dropdown to show which brush is selected
        document.querySelectorAll('.brush-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.brush === state.currentBrush);
        });
    }

    function updateSizeButtons() {
        // Update size option buttons to show which size is selected
        document.querySelectorAll('.size-option').forEach(btn => {
            const size = parseInt(btn.dataset.size);
            btn.classList.toggle('active', size === state.lineWidth);
        });
    }

    function updateOutlineFillButtons() {
        // Update outline dropdown items to show which outline style is selected
        document.querySelectorAll('#outline-dropdown .menu-item').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.outline === state.shapeOutline);
        });

        // Update fill dropdown items to show which fill style is selected
        document.querySelectorAll('#fill-dropdown .menu-item').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.fill === state.shapeFill);
        });
    }

    function updateBrushesButtonIcon() {
        const brushesBtn = document.getElementById('btn-brushes');
        if (!brushesBtn) return;

        const iconContainer = brushesBtn.querySelector('.btn-icon');
        if (!iconContainer) return;

        // Define SVG icons for each brush type
        const brushIcons = {
            'brush': '<svg viewBox="0 0 32 32"><circle cx="16" cy="16" r="8" fill="#333"/></svg>',
            'calligraphy1': '<svg viewBox="0 0 32 32"><ellipse cx="16" cy="16" rx="3" ry="10" fill="#333" transform="rotate(-45 16 16)"/></svg>',
            'calligraphy2': '<svg viewBox="0 0 32 32"><ellipse cx="16" cy="16" rx="3" ry="10" fill="#333" transform="rotate(45 16 16)"/></svg>',
            'airbrush': '<svg viewBox="0 0 32 32"><circle cx="16" cy="16" r="10" fill="#333" opacity="0.3"/><circle cx="16" cy="16" r="6" fill="#333" opacity="0.5"/><circle cx="16" cy="16" r="3" fill="#333"/></svg>',
            'oil': '<svg viewBox="0 0 32 32"><rect x="6" y="12" width="20" height="8" fill="#333" rx="2"/></svg>',
            'crayon': '<svg viewBox="0 0 32 32"><path d="M8 8 L24 8 L20 24 L12 24 Z" fill="#333"/></svg>',
            'marker': '<svg viewBox="0 0 32 32"><rect x="10" y="8" width="12" height="16" fill="#333"/></svg>',
            'pencil': '<svg viewBox="0 0 32 32"><line x1="8" y1="24" x2="24" y2="8" stroke="#333" stroke-width="3"/></svg>',
            'watercolor': '<svg viewBox="0 0 32 32"><circle cx="16" cy="16" r="10" fill="#333" opacity="0.4"/></svg>'
        };

        const icon = brushIcons[state.currentBrush] || brushIcons['brush'];
        iconContainer.innerHTML = icon;
    }

    function updateCursor() {
        mainCanvas.className = '';
        mainCanvas.style.cursor = '';  // Reset inline cursor
        canvasWrapper.style.cursor = '';  // Reset wrapper cursor too

        let cursorStyle = 'crosshair';
        switch (state.currentTool) {
            case 'pencil':
                mainCanvas.classList.add('cursor-pencil');
                break;
            case 'brush':
                mainCanvas.classList.add('cursor-brush-' + state.currentBrush);
                break;
            case 'eraser':
                mainCanvas.classList.add('cursor-eraser');
                break;
            case 'fill':
                mainCanvas.classList.add('cursor-fill');
                break;
            case 'picker':
                mainCanvas.classList.add('cursor-picker');
                break;
            case 'text':
                mainCanvas.classList.add('cursor-text');
                cursorStyle = 'text';
                break;
            case 'magnifier':
                mainCanvas.classList.add('cursor-zoom-in');
                cursorStyle = 'zoom-in';
                break;
            case 'select':
                mainCanvas.classList.add('cursor-crosshair');
                break;
            default:
                mainCanvas.classList.add('cursor-crosshair');
        }

        // Also set on canvas wrapper and inline style
        mainCanvas.style.cursor = cursorStyle;
        canvasWrapper.style.cursor = cursorStyle;
    }

    // ==================== FLOOD FILL ====================
    function floodFill(startX, startY, fillColor) {
        const imageData = mainCtx.getImageData(0, 0, state.canvasWidth, state.canvasHeight);
        const data = imageData.data;
        const width = state.canvasWidth;
        const height = state.canvasHeight;

        // Bounds check
        if (startX < 0 || startX >= width || startY < 0 || startY >= height) return;

        const targetColor = getPixelColor(data, startX, startY, width);
        const fill = hexToRgb(fillColor);

        if (colorsMatch(targetColor, fill)) return;

        // Use a typed array for visited pixels to improve performance
        const visited = new Uint8Array(width * height);
        const pixelStack = [[startX, startY]];

        // Safety limit to prevent browser freeze on very large fills
        const maxIterations = width * height;
        let iterations = 0;

        while (pixelStack.length > 0 && iterations < maxIterations) {
            const [x, y] = pixelStack.pop();
            let currentY = y;

            // Move up to find the top of this column
            while (currentY >= 0 && colorsMatch(getPixelColor(data, x, currentY, width), targetColor)) {
                currentY--;
            }
            currentY++;

            let reachLeft = false, reachRight = false;

            while (currentY < height && colorsMatch(getPixelColor(data, x, currentY, width), targetColor)) {
                const idx = currentY * width + x;
                if (visited[idx]) {
                    currentY++;
                    continue;
                }
                visited[idx] = 1;
                setPixelColor(data, x, currentY, width, fill);
                iterations++;

                if (x > 0) {
                    if (colorsMatch(getPixelColor(data, x - 1, currentY, width), targetColor) && !visited[currentY * width + x - 1]) {
                        if (!reachLeft) { pixelStack.push([x - 1, currentY]); reachLeft = true; }
                    } else { reachLeft = false; }
                }

                if (x < width - 1) {
                    if (colorsMatch(getPixelColor(data, x + 1, currentY, width), targetColor) && !visited[currentY * width + x + 1]) {
                        if (!reachRight) { pixelStack.push([x + 1, currentY]); reachRight = true; }
                    } else { reachRight = false; }
                }

                currentY++;
            }
        }

        mainCtx.putImageData(imageData, 0, 0);
    }

    function getPixelColor(data, x, y, width) {
        const idx = (y * width + x) * 4;
        return { r: data[idx], g: data[idx + 1], b: data[idx + 2], a: data[idx + 3] };
    }

    function setPixelColor(data, x, y, width, color) {
        const idx = (y * width + x) * 4;
        data[idx] = color.r;
        data[idx + 1] = color.g;
        data[idx + 2] = color.b;
        data[idx + 3] = 255;
    }

    function colorsMatch(c1, c2, tolerance = 0) {
        return Math.abs(c1.r - c2.r) <= tolerance &&
               Math.abs(c1.g - c2.g) <= tolerance &&
               Math.abs(c1.b - c2.b) <= tolerance;
    }

    function hexToRgb(hex) {
        // Remove # if present
        hex = hex.replace(/^#/, '');

        // Handle 3-character hex (e.g., #FFF -> #FFFFFF)
        if (hex.length === 3) {
            hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
        }

        // Handle 4-character hex with alpha (e.g., #FFFA -> #FFFFFFAA)
        if (hex.length === 4) {
            hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
        }

        // Handle 8-character hex with alpha (just use first 6)
        if (hex.length === 8) {
            hex = hex.substring(0, 6);
        }

        const result = /^([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : { r: 0, g: 0, b: 0 };
    }

    function rgbToHex(r, g, b) {
        return '#' + [r, g, b].map(x => x.toString(16).padStart(2, '0')).join('');
    }

    // ==================== BRUSH DRAWING ====================
    function drawBrushStroke(x, y, color, isStart) {
        const size = state.lineWidth * 2;

        if (isStart) {
            lastBrushX = x;
            lastBrushY = y;
            drawBrushPoint(x, y, color, size);
            return;
        }

        // Interpolate between last point and current point for smooth strokes
        if (lastBrushX !== null && lastBrushY !== null) {
            const dist = Math.sqrt((x - lastBrushX) ** 2 + (y - lastBrushY) ** 2);
            const step = Math.max(1, size * 0.3); // Step size based on brush size

            if (dist > step) {
                const steps = Math.ceil(dist / step);
                for (let i = 1; i <= steps; i++) {
                    const t = i / steps;
                    const ix = lastBrushX + (x - lastBrushX) * t;
                    const iy = lastBrushY + (y - lastBrushY) * t;
                    drawBrushPoint(ix, iy, color, size);
                }
            } else {
                drawBrushPoint(x, y, color, size);
            }
        } else {
            drawBrushPoint(x, y, color, size);
        }

        lastBrushX = x;
        lastBrushY = y;
    }

    function drawBrushPoint(x, y, color, size) {
        // Get all points (original + mirrored)
        const points = getMirroredPoints(x, y);

        for (const pt of points) {
            drawSingleBrushPoint(pt.x, pt.y, color, size);
        }
    }

    function drawSingleBrushPoint(x, y, color, size) {
        switch (state.currentBrush) {
            case 'brush':
                // Standard round brush - draw filled circle
                mainCtx.fillStyle = color;
                mainCtx.beginPath();
                mainCtx.arc(x, y, size / 2, 0, Math.PI * 2);
                mainCtx.fill();
                break;

            case 'calligraphy1':
                // Angled calligraphy brush (45 degrees)
                drawCalligraphyStroke(x, y, color, size, -45);
                break;

            case 'calligraphy2':
                // Reverse angled calligraphy brush
                drawCalligraphyStroke(x, y, color, size, 45);
                break;

            case 'airbrush':
                // Spray paint effect
                drawAirbrushStroke(x, y, color, size * 2);
                break;

            case 'oil':
                // Flat oil brush - draw filled rectangle
                mainCtx.fillStyle = color;
                mainCtx.save();
                mainCtx.translate(x, y);
                mainCtx.fillRect(-size * 0.75, -size * 0.25, size * 1.5, size * 0.5);
                mainCtx.restore();
                break;

            case 'crayon':
                // Textured crayon effect
                drawCrayonStroke(x, y, color, size);
                break;

            case 'marker':
                // Semi-transparent marker with composite mode to prevent darkening
                mainCtx.save();
                mainCtx.globalCompositeOperation = 'source-over';
                const rgb = hexToRgb(color);
                mainCtx.fillStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.4)`;
                mainCtx.fillRect(x - size, y - size * 0.5, size * 2, size);
                mainCtx.restore();
                break;

            case 'pencil':
                // Natural pencil - small filled circle with slight transparency
                mainCtx.fillStyle = color;
                mainCtx.globalAlpha = 0.8;
                mainCtx.beginPath();
                mainCtx.arc(x, y, Math.max(1, size * 0.15), 0, Math.PI * 2);
                mainCtx.fill();
                mainCtx.globalAlpha = 1.0;
                break;

            case 'watercolor':
                // Soft watercolor effect
                drawWatercolorStroke(x, y, color, size * 2);
                break;

            default:
                // Fallback to standard brush - filled circle
                mainCtx.fillStyle = color;
                mainCtx.beginPath();
                mainCtx.arc(x, y, size / 2, 0, Math.PI * 2);
                mainCtx.fill();
        }
    }

    function drawCalligraphyStroke(x, y, color, size, angle) {
        mainCtx.save();
        mainCtx.translate(x, y);
        mainCtx.rotate(angle * Math.PI / 180);
        mainCtx.fillStyle = color;
        mainCtx.beginPath();
        mainCtx.ellipse(0, 0, size * 0.2, size * 0.8, 0, 0, Math.PI * 2);
        mainCtx.fill();
        mainCtx.restore();
    }

    function drawAirbrushStroke(x, y, color, size) {
        const rgb = hexToRgb(color);
        const particles = Math.floor(size * 3);

        for (let i = 0; i < particles; i++) {
            const angle = Math.random() * Math.PI * 2;
            const radius = Math.random() * size;
            const px = x + Math.cos(angle) * radius;
            const py = y + Math.sin(angle) * radius;
            const alpha = Math.max(0.1, 1 - (radius / size));

            mainCtx.fillStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${alpha * 0.3})`;
            mainCtx.beginPath();
            mainCtx.arc(px, py, 1, 0, Math.PI * 2);
            mainCtx.fill();
        }
    }

    function drawCrayonStroke(x, y, color, size) {
        const rgb = hexToRgb(color);

        for (let i = 0; i < 5; i++) {
            const offsetX = (Math.random() - 0.5) * size * 0.5;
            const offsetY = (Math.random() - 0.5) * size * 0.5;
            const alpha = 0.3 + Math.random() * 0.4;

            mainCtx.fillStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${alpha})`;
            mainCtx.beginPath();
            mainCtx.arc(x + offsetX, y + offsetY, size * 0.3 + Math.random() * size * 0.2, 0, Math.PI * 2);
            mainCtx.fill();
        }
    }

    function drawWatercolorStroke(x, y, color, size) {
        const rgb = hexToRgb(color);

        // Draw soft, overlapping circles
        for (let i = 0; i < 3; i++) {
            const offsetX = (Math.random() - 0.5) * size * 0.3;
            const offsetY = (Math.random() - 0.5) * size * 0.3;
            const radius = size * (0.5 + Math.random() * 0.5);

            mainCtx.fillStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.1)`;
            mainCtx.beginPath();
            mainCtx.arc(x + offsetX, y + offsetY, radius, 0, Math.PI * 2);
            mainCtx.fill();
        }
    }

    // ==================== COLOR PICKER (eyedropper) ====================
    function pickColor(x, y, isSecondary) {
        const pixel = mainCtx.getImageData(Math.floor(x), Math.floor(y), 1, 1).data;
        const color = rgbToHex(pixel[0], pixel[1], pixel[2]);
        if (isSecondary) state.color2 = color;
        else state.color1 = color;
        updateColorBoxes();
    }

    // ==================== TEXT TOOL ====================
    function showTextInput(x, y) {
        const input = document.getElementById('text-input');
        if (!input) return;

        // Commit any previous text first
        if (!input.classList.contains('hidden') && input.value.trim()) {
            commitText();
        }

        state.textX = x;
        state.textY = y;

        // Position directly on canvas
        const canvasRect = mainCanvas.getBoundingClientRect();
        input.style.left = (canvasRect.left + x * state.zoom) + 'px';
        input.style.top = (canvasRect.top + y * state.zoom) + 'px';

        // Apply current text styles
        input.style.fontFamily = state.textStyles.font;
        input.style.fontSize = (state.textStyles.size * state.zoom) + 'px';
        input.style.fontWeight = state.textStyles.bold ? 'bold' : 'normal';
        input.style.fontStyle = state.textStyles.italic ? 'italic' : 'normal';
        input.style.color = state.color1;

        // Set text decoration
        let textDecoration = 'none';
        if (state.textStyles.underline && state.textStyles.strikethrough) {
            textDecoration = 'underline line-through';
        } else if (state.textStyles.underline) {
            textDecoration = 'underline';
        } else if (state.textStyles.strikethrough) {
            textDecoration = 'line-through';
        }
        input.style.textDecoration = textDecoration;

        input.value = '';
        input.classList.remove('hidden');
        input.style.display = 'block';  // Force visible

        // Focus with a small delay to ensure element is visible
        setTimeout(() => {
            input.focus();
        }, 10);
    }

    function hideTextInput() {
        const input = document.getElementById('text-input');
        if (input) {
            input.classList.add('hidden');
        }
    }

    function commitText() {
        const input = document.getElementById('text-input');
        const text = input.value;

        if (text.trim()) {
            mainCtx.save();
            let fontStyle = '';
            if (state.textStyles.bold) fontStyle += 'bold ';
            if (state.textStyles.italic) fontStyle += 'italic ';

            mainCtx.font = `${fontStyle}${state.textStyles.size}px ${state.textStyles.font}`;
            mainCtx.fillStyle = state.color1;
            mainCtx.strokeStyle = state.color1;
            mainCtx.textBaseline = 'top';

            const lines = text.split('\n');
            const lineHeight = state.textStyles.size * 1.2;

            lines.forEach((line, i) => {
                const y = state.textY + i * lineHeight;
                mainCtx.fillText(line, state.textX, y);

                // Measure text for underline/strikethrough
                const metrics = mainCtx.measureText(line);
                const textWidth = metrics.width;

                // Draw underline
                if (state.textStyles.underline) {
                    const underlineY = y + state.textStyles.size + 2;
                    mainCtx.lineWidth = Math.max(1, state.textStyles.size / 12);
                    mainCtx.beginPath();
                    mainCtx.moveTo(state.textX, underlineY);
                    mainCtx.lineTo(state.textX + textWidth, underlineY);
                    mainCtx.stroke();
                }

                // Draw strikethrough
                if (state.textStyles.strikethrough) {
                    const strikeY = y + state.textStyles.size * 0.55;
                    mainCtx.lineWidth = Math.max(1, state.textStyles.size / 12);
                    mainCtx.beginPath();
                    mainCtx.moveTo(state.textX, strikeY);
                    mainCtx.lineTo(state.textX + textWidth, strikeY);
                    mainCtx.stroke();
                }
            });

            mainCtx.restore();
            saveHistory();
        }

        hideTextInput();
        input.value = '';
    }

    function toggleTextStyle(style) {
        state.textStyles[style] = !state.textStyles[style];
        document.getElementById('text-' + style).classList.toggle('active', state.textStyles[style]);
        updateTextInputStyle();
    }

    function updateTextInputStyle() {
        const input = document.getElementById('text-input');
        if (!input || input.classList.contains('hidden')) return;

        input.style.fontFamily = state.textStyles.font;
        input.style.fontSize = (state.textStyles.size * state.zoom) + 'px';
        input.style.fontWeight = state.textStyles.bold ? 'bold' : 'normal';
        input.style.fontStyle = state.textStyles.italic ? 'italic' : 'normal';
        input.style.color = state.color1;

        let textDecoration = 'none';
        if (state.textStyles.underline && state.textStyles.strikethrough) {
            textDecoration = 'underline line-through';
        } else if (state.textStyles.underline) {
            textDecoration = 'underline';
        } else if (state.textStyles.strikethrough) {
            textDecoration = 'line-through';
        }
        input.style.textDecoration = textDecoration;
    }

    // ==================== HISTORY ====================
    function saveHistory() {
        state.history = state.history.slice(0, state.historyIndex + 1);
        const imageData = mainCtx.getImageData(0, 0, state.canvasWidth, state.canvasHeight);
        state.history.push({
            imageData: imageData,
            width: state.canvasWidth,
            height: state.canvasHeight
        });
        state.historyIndex++;

        if (state.history.length > state.maxHistory) {
            state.history.shift();
            state.historyIndex--;
        }

        state.isModified = true;
        updateTitle();
        updateUndoRedoButtons();
    }

    function undo() {
        commitFloatingSelection();
        if (state.historyIndex <= 0) return;

        state.historyIndex--;
        restoreHistoryState();
        updateUndoRedoButtons();
    }

    function redo() {
        commitFloatingSelection();
        if (state.historyIndex >= state.history.length - 1) return;

        state.historyIndex++;
        restoreHistoryState();
        updateUndoRedoButtons();
    }

    function restoreHistoryState() {
        const historyItem = state.history[state.historyIndex];

        if (historyItem.width !== state.canvasWidth || historyItem.height !== state.canvasHeight) {
            resizeAllCanvases(historyItem.width, historyItem.height, false);
        }

        mainCtx.putImageData(historyItem.imageData, 0, 0);
    }

    function updateUndoRedoButtons() {
        document.getElementById('qat-undo').disabled = state.historyIndex <= 0;
        document.getElementById('qat-redo').disabled = state.historyIndex >= state.history.length - 1;
    }

    // ==================== FILE OPERATIONS ====================
    function newFile() {
        commitFloatingSelection();

        state.history = [];
        state.historyIndex = -1;
        state.fileName = 'Untitled';
        state.isModified = false;

        resizeAllCanvases(800, 600, false);
        mainCtx.fillStyle = '#FFFFFF';
        mainCtx.fillRect(0, 0, 800, 600);

        clearSelection();
        saveHistory();
        updateTitle();
    }

    function openFile() {
        document.getElementById('file-input').click();
    }

    function handleFileOpen(e) {
        const file = e.target.files[0];
        if (!file) return;

        // Validate file type
        if (!file.type.startsWith('image/')) {
            alert('Please select a valid image file.');
            e.target.value = '';
            return;
        }

        const img = new Image();
        img.onload = () => {
            try {
                // Validate image dimensions
                if (img.width < MIN_CANVAS_SIZE || img.height < MIN_CANVAS_SIZE) {
                    alert('Image is too small. Minimum size is ' + MIN_CANVAS_SIZE + 'x' + MIN_CANVAS_SIZE + ' pixels.');
                    URL.revokeObjectURL(img.src);
                    return;
                }
                if (img.width > MAX_CANVAS_SIZE || img.height > MAX_CANVAS_SIZE) {
                    alert('Image is too large. Maximum size is ' + MAX_CANVAS_SIZE + 'x' + MAX_CANVAS_SIZE + ' pixels.');
                    URL.revokeObjectURL(img.src);
                    return;
                }

                commitFloatingSelection();
                resizeAllCanvases(img.width, img.height, false);
                mainCtx.drawImage(img, 0, 0);

                state.fileName = file.name.replace(/\.[^/.]+$/, '');
                state.isModified = false;
                state.history = [];
                state.historyIndex = -1;
                saveHistory();
                updateTitle();
            } catch (error) {
                console.error('Error loading image:', error);
                alert('Failed to load image. The file may be corrupted.');
            } finally {
                URL.revokeObjectURL(img.src);
            }
        };

        img.onerror = () => {
            console.error('Failed to load image');
            alert('Failed to load image. The file may be corrupted or unsupported.');
            URL.revokeObjectURL(img.src);
        };

        img.src = URL.createObjectURL(file);
        e.target.value = '';
    }

    function saveFile() { quickSave(); }

    function saveFileAs() {
        commitFloatingSelection();
        // Show save as dialog
        document.getElementById('save-filename').value = state.fileName;
        showDialog('save-as-dialog');
    }

    function executeSaveAs() {
        const filename = document.getElementById('save-filename').value || 'Untitled';
        const format = document.querySelector('input[name="save-format"]:checked').value;

        const formatInfo = {
            'png': { mime: 'image/png', ext: '.png', quality: undefined },
            'jpeg': { mime: 'image/jpeg', ext: '.jpg', quality: 0.92 },
            'webp': { mime: 'image/webp', ext: '.webp', quality: 0.92 },
            'bmp': { mime: 'image/bmp', ext: '.bmp', quality: undefined }
        };

        const info = formatInfo[format] || formatInfo['png'];

        try {
            mainCanvas.toBlob(blob => {
                if (!blob) {
                    alert('Failed to save image. Try a different format.');
                    return;
                }
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = filename + info.ext;
                a.click();
                URL.revokeObjectURL(a.href);
                state.fileName = filename;
                state.isModified = false;
                updateTitle();
                closeAllDialogs();
            }, info.mime, info.quality);
        } catch (error) {
            console.error('Error saving file:', error);
            alert('Failed to save image. Please try again.');
        }
    }

    function quickSave() {
        // Quick save as PNG
        commitFloatingSelection();
        mainCanvas.toBlob(blob => {
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = state.fileName + '.png';
            a.click();
            URL.revokeObjectURL(a.href);
            state.isModified = false;
            updateTitle();
        }, 'image/png');
    }

    function printFile() {
        commitFloatingSelection();

        // Try to open print window
        const printWindow = window.open('', '_blank');

        if (!printWindow || printWindow.closed || typeof printWindow.closed === 'undefined') {
            // Popup was blocked - use alternative method
            alert('Please allow popups to print, or use Cmd+P after clicking OK.');
            return;
        }

        const imgData = mainCanvas.toDataURL('image/png');
        printWindow.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>Print - ${state.fileName}</title>
                <style>
                    body { margin: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
                    img { max-width: 100%; height: auto; }
                    @media print { body { margin: 0; } img { max-width: 100%; } }
                </style>
            </head>
            <body>
                <img src="${imgData}" onload="setTimeout(function(){ window.print(); window.close(); }, 100);">
            </body>
            </html>
        `);
        printWindow.document.close();
    }

    function sendEmail() {
        commitFloatingSelection();
        mainCanvas.toBlob(blob => {
            // Create a link to download the image first
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = state.fileName + '.png';
            link.click();
            URL.revokeObjectURL(url);
            // Then open mail client
            setTimeout(() => {
                window.location.href = 'mailto:?subject=' + encodeURIComponent('Image: ' + state.fileName) +
                    '&body=' + encodeURIComponent('Please find the attached image.');
            }, 100);
        }, 'image/png');
    }

    function setAsWallpaper() {
        commitFloatingSelection();
        mainCanvas.toBlob(blob => {
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = state.fileName + '-wallpaper.png';
            link.click();
            URL.revokeObjectURL(url);
            alert('Image downloaded. To set as wallpaper on Mac:\n1. Open System Settings > Wallpaper\n2. Click "Add Folder" or drag the downloaded image');
        }, 'image/png');
    }

    function exitApp() {
        if (state.isModified && !confirm('Discard changes?')) return;
        window.close();
    }

    // ==================== CAMERA ====================
    let cameraStream = null;

    function openCamera() {
        showDialog('camera-dialog');
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(stream => {
                cameraStream = stream;
                document.getElementById('camera-video').srcObject = stream;
            })
            .catch(err => {
                alert('Could not access camera: ' + err.message);
                closeAllDialogs();
            });
    }

    function captureCamera() {
        const video = document.getElementById('camera-video');
        const canvas = document.getElementById('camera-canvas');

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);

        const img = new Image();
        img.onload = () => {
            pasteImage(img);
        };
        img.src = canvas.toDataURL();

        stopCamera();
        closeAllDialogs();
    }

    function stopCamera() {
        if (cameraStream) {
            cameraStream.getTracks().forEach(track => track.stop());
            cameraStream = null;
        }
    }

    // ==================== RESIZE DIALOG ====================
    let resizeAspectRatio = 1;

    function showResizeDialog() {
        const unit = document.querySelector('input[name="resize-unit"]:checked').value;

        if (unit === 'percent') {
            document.getElementById('resize-h').value = 100;
            document.getElementById('resize-v').value = 100;
        } else {
            document.getElementById('resize-h').value = state.canvasWidth;
            document.getElementById('resize-v').value = state.canvasHeight;
        }

        document.getElementById('skew-h').value = 0;
        document.getElementById('skew-v').value = 0;

        // Calculate aspect ratio
        resizeAspectRatio = state.canvasWidth / state.canvasHeight;

        // Update unit labels
        updateResizeUnitLabels();

        showDialog('resize-dialog');
    }

    function updateResizeUnitLabels() {
        const unit = document.querySelector('input[name="resize-unit"]:checked').value;
        const labels = document.querySelectorAll('.resize-unit');
        labels.forEach(label => {
            label.textContent = unit === 'percent' ? '%' : 'px';
        });

        // Update values when switching units
        const hInput = document.getElementById('resize-h');
        const vInput = document.getElementById('resize-v');

        if (unit === 'percent') {
            hInput.value = 100;
            vInput.value = 100;
        } else {
            hInput.value = state.canvasWidth;
            vInput.value = state.canvasHeight;
        }
    }

    function handleResizeAspectRatio(changedInput) {
        const maintainAspect = document.getElementById('resize-aspect').checked;
        if (!maintainAspect) return;

        const unit = document.querySelector('input[name="resize-unit"]:checked').value;
        const hInput = document.getElementById('resize-h');
        const vInput = document.getElementById('resize-v');

        if (changedInput === 'h') {
            if (unit === 'percent') {
                vInput.value = hInput.value;
            } else {
                vInput.value = Math.round(parseFloat(hInput.value) / resizeAspectRatio);
            }
        } else {
            if (unit === 'percent') {
                hInput.value = vInput.value;
            } else {
                hInput.value = Math.round(parseFloat(vInput.value) * resizeAspectRatio);
            }
        }
    }

    function applyResize() {
        commitFloatingSelection();

        const unit = document.querySelector('input[name="resize-unit"]:checked').value;
        let h = parseFloat(document.getElementById('resize-h').value) || 100;
        let v = parseFloat(document.getElementById('resize-v').value) || 100;
        const skewH = parseFloat(document.getElementById('skew-h').value) || 0;
        const skewV = parseFloat(document.getElementById('skew-v').value) || 0;

        let newWidth, newHeight;
        if (unit === 'percent') {
            newWidth = Math.round(state.canvasWidth * h / 100);
            newHeight = Math.round(state.canvasHeight * v / 100);
        } else {
            newWidth = Math.round(h);
            newHeight = Math.round(v);
        }

        // Ensure minimum size
        newWidth = Math.max(1, newWidth);
        newHeight = Math.max(1, newHeight);

        // Create temp canvas for transformations
        const tempCanvas = document.createElement('canvas');
        const tempCtx = tempCanvas.getContext('2d');

        // Calculate skew adjustments
        const skewHRad = skewH * Math.PI / 180;
        const skewVRad = skewV * Math.PI / 180;

        // Adjust canvas size for skew
        const skewExtraWidth = Math.abs(Math.tan(skewHRad) * newHeight);
        const skewExtraHeight = Math.abs(Math.tan(skewVRad) * newWidth);

        const finalWidth = Math.round(newWidth + skewExtraWidth);
        const finalHeight = Math.round(newHeight + skewExtraHeight);

        tempCanvas.width = finalWidth;
        tempCanvas.height = finalHeight;

        // Apply transformations
        tempCtx.fillStyle = state.color2;
        tempCtx.fillRect(0, 0, finalWidth, finalHeight);

        // Translate to compensate for skew offset
        if (skewH < 0) tempCtx.translate(skewExtraWidth, 0);
        if (skewV < 0) tempCtx.translate(0, skewExtraHeight);

        // Apply skew transform
        tempCtx.transform(1, Math.tan(skewVRad), Math.tan(skewHRad), 1, 0, 0);

        // Draw scaled image
        tempCtx.drawImage(mainCanvas, 0, 0, newWidth, newHeight);

        resizeAllCanvases(finalWidth, finalHeight, false);
        mainCtx.drawImage(tempCanvas, 0, 0);

        saveHistory();
        closeAllDialogs();
    }

    // Canvas resize handles
    let isResizingCanvas = false;
    let resizeHandle = null;
    let resizeStartX, resizeStartY, originalWidth, originalHeight;

    function startCanvasResize(e) {
        isResizingCanvas = true;
        resizeHandle = e.target.dataset.handle;
        resizeStartX = e.clientX;
        resizeStartY = e.clientY;
        originalWidth = state.canvasWidth;
        originalHeight = state.canvasHeight;

        document.addEventListener('mousemove', doCanvasResize);
        document.addEventListener('mouseup', stopCanvasResize);
        e.preventDefault();
    }

    // Minimum canvas size constants
    const MIN_CANVAS_SIZE = 10;
    const MAX_CANVAS_SIZE = 10000;

    function doCanvasResize(e) {
        if (!isResizingCanvas) return;

        const dx = (e.clientX - resizeStartX) / state.zoom;
        const dy = (e.clientY - resizeStartY) / state.zoom;

        let newWidth = originalWidth;
        let newHeight = originalHeight;

        if (resizeHandle.includes('e')) {
            newWidth = Math.max(MIN_CANVAS_SIZE, Math.min(MAX_CANVAS_SIZE, Math.round(originalWidth + dx)));
        }
        if (resizeHandle.includes('s')) {
            newHeight = Math.max(MIN_CANVAS_SIZE, Math.min(MAX_CANVAS_SIZE, Math.round(originalHeight + dy)));
        }

        canvasWrapper.style.width = (newWidth * state.zoom) + 'px';
        canvasWrapper.style.height = (newHeight * state.zoom) + 'px';
    }

    function stopCanvasResize(e) {
        if (!isResizingCanvas) return;

        const dx = (e.clientX - resizeStartX) / state.zoom;
        const dy = (e.clientY - resizeStartY) / state.zoom;

        let newWidth = originalWidth;
        let newHeight = originalHeight;

        if (resizeHandle.includes('e')) {
            newWidth = Math.max(MIN_CANVAS_SIZE, Math.min(MAX_CANVAS_SIZE, Math.round(originalWidth + dx)));
        }
        if (resizeHandle.includes('s')) {
            newHeight = Math.max(MIN_CANVAS_SIZE, Math.min(MAX_CANVAS_SIZE, Math.round(originalHeight + dy)));
        }

        resizeAllCanvases(newWidth, newHeight, true);
        saveHistory();

        isResizingCanvas = false;
        document.removeEventListener('mousemove', doCanvasResize);
        document.removeEventListener('mouseup', stopCanvasResize);
    }

    // ==================== ZOOM ====================
    function setZoom(zoom) {
        state.zoom = Math.max(0.125, Math.min(8, zoom));
        updateCanvasSize();
        document.getElementById('status-zoom-slider').value = state.zoom * 100;
        document.getElementById('status-zoom-level').textContent = Math.round(state.zoom * 100) + '%';

        // Redraw rulers and gridlines at new zoom level
        if (state.showRulers) drawRulers();
        if (state.showGridlines) drawGridlines();
    }

    function toggleFullscreen() {
        if (document.fullscreenElement) document.exitFullscreen();
        else document.documentElement.requestFullscreen();
    }

    // ==================== GRIDLINES ====================
    function drawGridlines() {
        // We'll use a dedicated overlay for gridlines
        let gridOverlay = document.getElementById('grid-overlay');
        if (!gridOverlay) {
            gridOverlay = document.createElement('canvas');
            gridOverlay.id = 'grid-overlay';
            gridOverlay.style.cssText = 'position:absolute;top:0;left:0;pointer-events:none;';
            canvasWrapper.appendChild(gridOverlay);
        }

        gridOverlay.width = state.canvasWidth;
        gridOverlay.height = state.canvasHeight;
        gridOverlay.style.width = (state.canvasWidth * state.zoom) + 'px';
        gridOverlay.style.height = (state.canvasHeight * state.zoom) + 'px';

        const ctx = gridOverlay.getContext('2d');
        ctx.clearRect(0, 0, state.canvasWidth, state.canvasHeight);

        if (!state.showGridlines) return;

        const gridSize = 10; // 10px grid
        ctx.strokeStyle = 'rgba(0, 0, 0, 0.15)';
        ctx.lineWidth = 0.5;

        // Draw vertical lines
        for (let x = gridSize; x < state.canvasWidth; x += gridSize) {
            ctx.beginPath();
            ctx.moveTo(x + 0.5, 0);
            ctx.lineTo(x + 0.5, state.canvasHeight);
            ctx.stroke();
        }

        // Draw horizontal lines
        for (let y = gridSize; y < state.canvasHeight; y += gridSize) {
            ctx.beginPath();
            ctx.moveTo(0, y + 0.5);
            ctx.lineTo(state.canvasWidth, y + 0.5);
            ctx.stroke();
        }
    }

    // ==================== MIRROR DRAWING ====================
    function drawMirrorGuide() {
        // Create or get mirror guide overlay
        let mirrorOverlay = document.getElementById('mirror-overlay');
        if (!mirrorOverlay) {
            mirrorOverlay = document.createElement('canvas');
            mirrorOverlay.id = 'mirror-overlay';
            mirrorOverlay.style.cssText = 'position:absolute;top:0;left:0;pointer-events:none;z-index:5;';
            canvasWrapper.appendChild(mirrorOverlay);
        }

        mirrorOverlay.width = state.canvasWidth;
        mirrorOverlay.height = state.canvasHeight;
        mirrorOverlay.style.width = (state.canvasWidth * state.zoom) + 'px';
        mirrorOverlay.style.height = (state.canvasHeight * state.zoom) + 'px';

        const ctx = mirrorOverlay.getContext('2d');
        ctx.clearRect(0, 0, state.canvasWidth, state.canvasHeight);

        // Draw mirror guide lines
        ctx.setLineDash([5, 5]);
        ctx.lineWidth = 1;

        // Horizontal mirror line (vertical center line)
        if (state.mirrorHorizontal) {
            const centerX = state.canvasWidth / 2;
            ctx.strokeStyle = 'rgba(0, 120, 212, 0.6)';
            ctx.beginPath();
            ctx.moveTo(centerX, 0);
            ctx.lineTo(centerX, state.canvasHeight);
            ctx.stroke();
        }

        // Vertical mirror line (horizontal center line)
        if (state.mirrorVertical) {
            const centerY = state.canvasHeight / 2;
            ctx.strokeStyle = 'rgba(212, 0, 120, 0.6)';
            ctx.beginPath();
            ctx.moveTo(0, centerY);
            ctx.lineTo(state.canvasWidth, centerY);
            ctx.stroke();
        }

        ctx.setLineDash([]);
    }

    // Get mirrored coordinates
    function getMirroredPoints(x, y) {
        const points = [{ x, y }];
        const centerX = state.canvasWidth / 2;
        const centerY = state.canvasHeight / 2;

        if (state.mirrorHorizontal && state.mirrorVertical) {
            // 4-way symmetry
            points.push({ x: state.canvasWidth - x, y: y }); // Horizontal flip
            points.push({ x: x, y: state.canvasHeight - y }); // Vertical flip
            points.push({ x: state.canvasWidth - x, y: state.canvasHeight - y }); // Both
        } else if (state.mirrorHorizontal) {
            // Left-right mirror
            points.push({ x: state.canvasWidth - x, y: y });
        } else if (state.mirrorVertical) {
            // Top-bottom mirror
            points.push({ x: x, y: state.canvasHeight - y });
        }

        return points;
    }

    // Draw a stroke at all mirrored positions
    function drawMirroredStroke(fromX, fromY, toX, toY, color, lineWidth, lineCap, lineJoin) {
        const fromPoints = getMirroredPoints(fromX, fromY);
        const toPoints = getMirroredPoints(toX, toY);

        for (let i = 0; i < fromPoints.length; i++) {
            mainCtx.beginPath();
            mainCtx.strokeStyle = color;
            mainCtx.lineWidth = lineWidth;
            mainCtx.lineCap = lineCap || 'round';
            mainCtx.lineJoin = lineJoin || 'round';
            mainCtx.moveTo(fromPoints[i].x, fromPoints[i].y);
            mainCtx.lineTo(toPoints[i].x, toPoints[i].y);
            mainCtx.stroke();
        }
    }

    // Draw a point at all mirrored positions (for initial click)
    function drawMirroredPoint(x, y, color, lineWidth, lineCap) {
        const points = getMirroredPoints(x, y);

        for (const pt of points) {
            mainCtx.beginPath();
            mainCtx.strokeStyle = color;
            mainCtx.lineWidth = lineWidth;
            mainCtx.lineCap = lineCap || 'round';
            mainCtx.moveTo(pt.x, pt.y);
            mainCtx.lineTo(pt.x + 0.1, pt.y + 0.1);
            mainCtx.stroke();
        }
    }

    // ==================== RULERS ====================
    function drawRulers() {
        if (!state.showRulers) return;

        drawHorizontalRuler();
        drawVerticalRuler();
    }

    function drawHorizontalRuler() {
        const rulerCanvas = document.getElementById('ruler-h-canvas');
        if (!rulerCanvas) return;

        const container = document.getElementById('ruler-horizontal');
        const containerWidth = container.offsetWidth;

        rulerCanvas.width = containerWidth;
        rulerCanvas.height = 24;

        const ctx = rulerCanvas.getContext('2d');
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0, 0, containerWidth, 24);

        ctx.fillStyle = '#333';
        ctx.strokeStyle = '#333';
        ctx.font = '9px sans-serif';
        ctx.textAlign = 'center';

        // Calculate pixel interval based on zoom
        const pixelsPerUnit = state.zoom;
        let majorInterval = 100;
        let minorInterval = 10;

        // Adjust intervals based on zoom level
        if (state.zoom < 0.25) {
            majorInterval = 500;
            minorInterval = 100;
        } else if (state.zoom < 0.5) {
            majorInterval = 200;
            minorInterval = 50;
        } else if (state.zoom > 2) {
            majorInterval = 50;
            minorInterval = 10;
        } else if (state.zoom > 4) {
            majorInterval = 20;
            minorInterval = 5;
        }

        // Draw ruler markings
        for (let px = 0; px <= state.canvasWidth; px += minorInterval) {
            const screenX = px * state.zoom;
            if (screenX > containerWidth) break;

            const isMajor = px % majorInterval === 0;

            ctx.beginPath();
            ctx.moveTo(screenX, 24);
            ctx.lineTo(screenX, isMajor ? 8 : 16);
            ctx.stroke();

            if (isMajor) {
                ctx.fillText(px.toString(), screenX, 7);
            }
        }
    }

    function drawVerticalRuler() {
        const rulerCanvas = document.getElementById('ruler-v-canvas');
        if (!rulerCanvas) return;

        const container = document.getElementById('ruler-vertical');
        const containerHeight = container.offsetHeight;

        rulerCanvas.width = 24;
        rulerCanvas.height = containerHeight;

        const ctx = rulerCanvas.getContext('2d');
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0, 0, 24, containerHeight);

        ctx.fillStyle = '#333';
        ctx.strokeStyle = '#333';
        ctx.font = '9px sans-serif';

        // Calculate pixel interval based on zoom
        let majorInterval = 100;
        let minorInterval = 10;

        if (state.zoom < 0.25) {
            majorInterval = 500;
            minorInterval = 100;
        } else if (state.zoom < 0.5) {
            majorInterval = 200;
            minorInterval = 50;
        } else if (state.zoom > 2) {
            majorInterval = 50;
            minorInterval = 10;
        } else if (state.zoom > 4) {
            majorInterval = 20;
            minorInterval = 5;
        }

        // Draw ruler markings
        for (let py = 0; py <= state.canvasHeight; py += minorInterval) {
            const screenY = py * state.zoom;
            if (screenY > containerHeight) break;

            const isMajor = py % majorInterval === 0;

            ctx.beginPath();
            ctx.moveTo(24, screenY);
            ctx.lineTo(isMajor ? 8 : 16, screenY);
            ctx.stroke();

            if (isMajor && py > 0) {
                ctx.save();
                ctx.translate(7, screenY);
                ctx.rotate(-Math.PI / 2);
                ctx.textAlign = 'center';
                ctx.fillText(py.toString(), 0, 0);
                ctx.restore();
            }
        }
    }

    // ==================== UI HELPERS ====================
    function updateStatus(x, y) {
        if (x !== undefined && y !== undefined) {
            document.getElementById('status-pos').textContent = `${Math.floor(x)}, ${Math.floor(y)}px`;
        }
        document.getElementById('status-dimensions').textContent = `${state.canvasWidth} x ${state.canvasHeight}px`;
    }

    function updateTitle() {
        const modified = state.isModified ? '*' : '';
        document.getElementById('document-title').textContent = `${modified}${state.fileName} - MattPaint`;
        document.title = `${modified}${state.fileName} - MattPaint`;
    }

    function switchTab(tab) {
        document.querySelectorAll('.ribbon-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
        document.querySelectorAll('.ribbon-content').forEach(c => c.classList.toggle('active', c.id === 'ribbon-' + tab));
    }

    function toggleFileMenu() {
        const menu = document.getElementById('file-menu');
        menu.classList.toggle('hidden');
        if (!menu.classList.contains('hidden')) {
            const btn = document.getElementById('file-menu-btn');
            const rect = btn.getBoundingClientRect();
            menu.style.top = rect.bottom + 'px';
            menu.style.left = rect.left + 'px';
        }
    }

    function hideFileMenu() {
        document.getElementById('file-menu').classList.add('hidden');
    }

    function toggleDropdown(e, id) {
        hideAllDropdowns();
        const dropdown = document.getElementById(id);
        const rect = e.currentTarget.getBoundingClientRect();

        // Position dropdown below the button
        dropdown.style.top = rect.bottom + 2 + 'px';
        dropdown.style.left = rect.left + 'px';
        dropdown.classList.remove('hidden');

        // Make sure dropdown doesn't go off the right edge of the screen
        const dropdownRect = dropdown.getBoundingClientRect();
        if (dropdownRect.right > window.innerWidth) {
            dropdown.style.left = (window.innerWidth - dropdownRect.width - 10) + 'px';
        }

        // Make sure dropdown doesn't go off the bottom of the screen
        if (dropdownRect.bottom > window.innerHeight) {
            dropdown.style.top = (rect.top - dropdownRect.height - 2) + 'px';
        }

        e.stopPropagation();
    }

    function hideAllDropdowns() {
        document.querySelectorAll('.dropdown-menu').forEach(d => {
            if (d.id !== 'file-menu') d.classList.add('hidden');
        });
    }

    function showDialog(id) {
        document.getElementById('dialog-overlay').classList.remove('hidden');
        document.getElementById(id).classList.remove('hidden');
    }

    function closeAllDialogs() {
        document.getElementById('dialog-overlay').classList.add('hidden');
        document.querySelectorAll('.dialog').forEach(d => d.classList.add('hidden'));
        stopCamera();
    }

    function showProperties() {
        document.getElementById('prop-width').textContent = state.canvasWidth;
        document.getElementById('prop-height').textContent = state.canvasHeight;
        showDialog('properties-dialog');
    }

    function showAbout() {
        showDialog('about-dialog');
    }

    // ==================== COLOR PICKER DIALOG ====================
    let colorPickerTarget = 1;
    let colorPickerHue = 0;
    let colorPickerSat = 1;
    let colorPickerVal = 1;

    function initColorPicker() {
        const basicGrid = document.getElementById('basic-colors-grid');
        basicColors.forEach(color => {
            const swatch = document.createElement('button');
            swatch.className = 'color-swatch';
            swatch.style.background = color;
            swatch.addEventListener('click', () => setPickerColor(color));
            basicGrid.appendChild(swatch);
        });

        const customGrid = document.getElementById('custom-colors-grid');
        for (let i = 0; i < 16; i++) {
            const swatch = document.createElement('button');
            swatch.className = 'color-swatch empty';
            swatch.dataset.index = i;
            swatch.addEventListener('click', () => {
                if (customColors[i] !== '#FFFFFF') setPickerColor(customColors[i]);
            });
            customGrid.appendChild(swatch);
        }

        const gradient = document.getElementById('color-gradient');
        gradient.addEventListener('mousedown', (e) => { doGradientPick(e); });
        gradient.addEventListener('mousemove', (e) => { if (e.buttons === 1) doGradientPick(e); });

        const hue = document.getElementById('color-hue');
        const hueCtx = hue.getContext('2d');
        for (let y = 0; y < 256; y++) {
            hueCtx.fillStyle = `hsl(${(y / 256) * 360}, 100%, 50%)`;
            hueCtx.fillRect(0, y, 20, 1);
        }
        hue.addEventListener('mousedown', (e) => { doHuePick(e); });
        hue.addEventListener('mousemove', (e) => { if (e.buttons === 1) doHuePick(e); });

        ['r', 'g', 'b'].forEach(ch => {
            document.getElementById('color-' + ch).addEventListener('input', updateFromRGB);
        });

        document.getElementById('add-custom-color').addEventListener('click', addCustomColor);
    }

    function openColorPicker(target) {
        colorPickerTarget = target;
        const currentColor = target === 1 ? state.color1 : state.color2;
        document.getElementById('color-current').style.background = currentColor;
        setPickerColor(currentColor);
        showDialog('color-dialog');
    }

    function setPickerColor(hex) {
        const rgb = hexToRgb(hex);
        document.getElementById('color-r').value = rgb.r;
        document.getElementById('color-g').value = rgb.g;
        document.getElementById('color-b').value = rgb.b;
        document.getElementById('color-new').style.background = hex;

        const hsv = rgbToHsv(rgb.r, rgb.g, rgb.b);
        colorPickerHue = hsv.h;
        colorPickerSat = hsv.s;
        colorPickerVal = hsv.v;

        updateGradient();
        updateCursors();
    }

    function updateGradient() {
        const gradient = document.getElementById('color-gradient');
        const ctx = gradient.getContext('2d');
        const baseColor = hsvToRgb(colorPickerHue, 1, 1);

        const gradH = ctx.createLinearGradient(0, 0, 256, 0);
        gradH.addColorStop(0, '#FFFFFF');
        gradH.addColorStop(1, rgbToHex(baseColor.r, baseColor.g, baseColor.b));
        ctx.fillStyle = gradH;
        ctx.fillRect(0, 0, 256, 256);

        const gradV = ctx.createLinearGradient(0, 0, 0, 256);
        gradV.addColorStop(0, 'rgba(0,0,0,0)');
        gradV.addColorStop(1, 'rgba(0,0,0,1)');
        ctx.fillStyle = gradV;
        ctx.fillRect(0, 0, 256, 256);
    }

    function updateCursors() {
        document.getElementById('gradient-cursor').style.left = (colorPickerSat * 256) + 'px';
        document.getElementById('gradient-cursor').style.top = ((1 - colorPickerVal) * 256) + 'px';
        document.getElementById('hue-cursor').style.top = (colorPickerHue / 360 * 256) + 'px';
    }

    function doGradientPick(e) {
        const rect = e.target.getBoundingClientRect();
        colorPickerSat = Math.max(0, Math.min(1, (e.clientX - rect.left) / 255));
        colorPickerVal = Math.max(0, Math.min(1, 1 - (e.clientY - rect.top) / 255));
        updateColorFromHSV();
        updateCursors();
    }

    function doHuePick(e) {
        const rect = e.target.getBoundingClientRect();
        colorPickerHue = Math.max(0, Math.min(360, ((e.clientY - rect.top) / 255) * 360));
        updateGradient();
        updateColorFromHSV();
        updateCursors();
    }

    function updateColorFromHSV() {
        const rgb = hsvToRgb(colorPickerHue, colorPickerSat, colorPickerVal);
        document.getElementById('color-r').value = rgb.r;
        document.getElementById('color-g').value = rgb.g;
        document.getElementById('color-b').value = rgb.b;
        document.getElementById('color-new').style.background = rgbToHex(rgb.r, rgb.g, rgb.b);
    }

    function updateFromRGB() {
        const r = Math.max(0, Math.min(255, parseInt(document.getElementById('color-r').value) || 0));
        const g = Math.max(0, Math.min(255, parseInt(document.getElementById('color-g').value) || 0));
        const b = Math.max(0, Math.min(255, parseInt(document.getElementById('color-b').value) || 0));

        document.getElementById('color-new').style.background = rgbToHex(r, g, b);

        const hsv = rgbToHsv(r, g, b);
        colorPickerHue = hsv.h;
        colorPickerSat = hsv.s;
        colorPickerVal = hsv.v;

        updateGradient();
        updateCursors();
    }

    function applyColor() {
        const r = Math.max(0, Math.min(255, parseInt(document.getElementById('color-r').value) || 0));
        const g = Math.max(0, Math.min(255, parseInt(document.getElementById('color-g').value) || 0));
        const b = Math.max(0, Math.min(255, parseInt(document.getElementById('color-b').value) || 0));

        const hex = rgbToHex(r, g, b);
        if (colorPickerTarget === 1) state.color1 = hex;
        else state.color2 = hex;

        updateColorBoxes();
        closeAllDialogs();
    }

    function addCustomColor() {
        const r = Math.max(0, Math.min(255, parseInt(document.getElementById('color-r').value) || 0));
        const g = Math.max(0, Math.min(255, parseInt(document.getElementById('color-g').value) || 0));
        const b = Math.max(0, Math.min(255, parseInt(document.getElementById('color-b').value) || 0));

        const hex = rgbToHex(r, g, b);
        let index = customColors.findIndex(c => c === '#FFFFFF');
        if (index === -1) index = 0;

        customColors[index] = hex;
        const swatch = document.querySelector(`#custom-colors-grid .color-swatch[data-index="${index}"]`);
        swatch.style.background = hex;
        swatch.classList.remove('empty');
    }

    function rgbToHsv(r, g, b) {
        r /= 255; g /= 255; b /= 255;
        const max = Math.max(r, g, b), min = Math.min(r, g, b);
        const d = max - min;
        let h = 0;
        const s = max === 0 ? 0 : d / max;
        const v = max;

        if (d !== 0) {
            switch (max) {
                case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
                case g: h = ((b - r) / d + 2) / 6; break;
                case b: h = ((r - g) / d + 4) / 6; break;
            }
        }
        return { h: h * 360, s, v };
    }

    function hsvToRgb(h, s, v) {
        h = h / 360;
        const i = Math.floor(h * 6);
        const f = h * 6 - i;
        const p = v * (1 - s);
        const q = v * (1 - f * s);
        const t = v * (1 - (1 - f) * s);

        let r, g, b;
        switch (i % 6) {
            case 0: r = v; g = t; b = p; break;
            case 1: r = q; g = v; b = p; break;
            case 2: r = p; g = v; b = t; break;
            case 3: r = p; g = q; b = v; break;
            case 4: r = t; g = p; b = v; break;
            case 5: r = v; g = p; b = q; break;
        }
        return { r: Math.round(r * 255), g: Math.round(g * 255), b: Math.round(b * 255) };
    }

    // ==================== DRAG AND DROP ====================
    function handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        e.dataTransfer.dropEffect = 'copy';
        canvasContainer.classList.add('drag-over');
    }

    function handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        canvasContainer.classList.remove('drag-over');
    }

    function handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        canvasContainer.classList.remove('drag-over');

        const files = e.dataTransfer.files;
        if (files.length > 0 && files[0].type.startsWith('image/')) {
            const img = new Image();
            img.onload = () => {
                commitFloatingSelection();
                resizeAllCanvases(img.width, img.height, false);
                mainCtx.drawImage(img, 0, 0);

                state.fileName = files[0].name.replace(/\.[^/.]+$/, '');
                state.isModified = false;
                state.history = [];
                state.historyIndex = -1;
                saveHistory();
                updateTitle();
                URL.revokeObjectURL(img.src);
            };
            img.src = URL.createObjectURL(files[0]);
        }
    }

    // ==================== KEYBOARD SHORTCUTS ====================
    function handleKeyboard(e) {
        // Don't handle shortcuts when typing in text fields
        const tag = e.target.tagName.toUpperCase();
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
        if (e.target.isContentEditable) return;
        if (e.target.id === 'text-input') return;

        const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
        const ctrl = isMac ? e.metaKey : e.ctrlKey;

        if (ctrl) {
            switch (e.key.toLowerCase()) {
                case 'n': e.preventDefault(); newFile(); break;
                case 'o': e.preventDefault(); openFile(); break;
                case 's': e.preventDefault(); saveFile(); break;
                case 'p': e.preventDefault(); printFile(); break;
                case 'z':
                    e.preventDefault();
                    if (e.shiftKey) redo();
                    else undo();
                    break;
                case 'y': e.preventDefault(); redo(); break;
                case 'c': e.preventDefault(); copy(); break;
                case 'x': e.preventDefault(); cut(); break;
                case 'v': e.preventDefault(); paste(); break;
                case 'a': e.preventDefault(); selectAll(); break;
            }
        } else {
            switch (e.key) {
                case 'Delete':
                case 'Backspace':
                    if (state.selection || state.floatingSelection) {
                        e.preventDefault();
                        deleteSelection();
                    }
                    break;
                case 'Escape':
                    if (state.floatingSelection) {
                        commitFloatingSelection();
                    } else {
                        clearSelection();
                    }
                    commitText();  // Commit and hide text input
                    hideAllDropdowns();
                    hideFileMenu();
                    closeAllDialogs();
                    break;
                case '+':
                case '=':
                    setZoom(state.zoom * 1.25);
                    break;
                case '-':
                    setZoom(state.zoom / 1.25);
                    break;

                // Tool shortcuts
                case 'p':
                case 'P':
                    e.preventDefault();
                    selectTool('pencil');
                    break;
                case 'b':
                case 'B':
                    e.preventDefault();
                    selectTool('brush');
                    break;
                case 'e':
                case 'E':
                    e.preventDefault();
                    selectTool('eraser');
                    break;
                case 'g':
                case 'G':
                    e.preventDefault();
                    selectTool('fill');
                    break;
                case 't':
                case 'T':
                    e.preventDefault();
                    selectTool('text');
                    break;
                case 'i':
                case 'I':
                    e.preventDefault();
                    selectTool('picker');
                    break;
                case 's':
                case 'S':
                    e.preventDefault();
                    selectTool('select');
                    break;
                case 'z':
                case 'Z':
                    e.preventDefault();
                    selectTool('magnifier');
                    break;
                case 'l':
                case 'L':
                    e.preventDefault();
                    selectShape('line');
                    break;
                case 'r':
                case 'R':
                    e.preventDefault();
                    selectShape('rect');
                    break;
                case 'o':
                case 'O':
                    e.preventDefault();
                    selectShape('oval');
                    break;
            }
        }
    }

    // ==================== INITIALIZE ====================
    document.addEventListener('DOMContentLoaded', init);

})();
