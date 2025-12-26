/**
 * MattPaint In-App Test Suite
 * Run this in the browser console while index.html is open
 * Or add ?test to the URL to auto-run
 */

(function() {
    'use strict';

    let passed = 0, failed = 0;
    const results = [];

    function test(name, condition) {
        const pass = !!condition;
        if (pass) passed++; else failed++;
        results.push({ name, pass });
        return pass;
    }

    function runTests() {
        console.clear();
        console.log('%c MattPaint Test Suite ', 'background: #2196F3; color: white; font-size: 16px; padding: 5px;');
        console.log('');

        // ============ DOM ELEMENT TESTS ============
        console.log('%c--- DOM Elements ---', 'color: #9C27B0; font-weight: bold;');

        test('Main canvas exists', document.getElementById('main-canvas'));
        test('Preview canvas exists', document.getElementById('preview-canvas'));
        test('Selection canvas exists', document.getElementById('selection-canvas'));
        test('Canvas wrapper exists', document.getElementById('canvas-wrapper'));
        test('Color palette exists', document.getElementById('color-palette'));

        // Tool buttons
        const tools = ['pencil', 'brush', 'eraser', 'fill', 'text', 'picker', 'magnifier', 'select'];
        tools.forEach(tool => {
            test(`Tool button: ${tool}`, document.getElementById('tool-' + tool));
        });

        // Shape buttons
        const shapes = ['line', 'curve', 'oval', 'rect', 'roundrect', 'polygon', 'triangle'];
        shapes.forEach(shape => {
            test(`Shape: ${shape}`, document.querySelector(`[data-shape="${shape}"]`));
        });

        // Dialogs
        test('Resize dialog exists', document.getElementById('resize-dialog'));
        test('Color picker dialog exists', document.getElementById('color-dialog'));
        test('About dialog exists', document.getElementById('about-dialog'));

        // Resize dialog inputs
        test('Resize H input', document.getElementById('resize-h'));
        test('Resize V input', document.getElementById('resize-v'));
        test('Skew H input', document.getElementById('skew-h'));
        test('Skew V input', document.getElementById('skew-v'));
        test('Aspect ratio checkbox', document.getElementById('resize-aspect'));

        // Rulers
        test('Horizontal ruler', document.getElementById('ruler-horizontal'));
        test('Vertical ruler', document.getElementById('ruler-vertical'));
        test('H ruler canvas', document.getElementById('ruler-h-canvas'));
        test('V ruler canvas', document.getElementById('ruler-v-canvas'));

        // Text tool
        test('Text input', document.getElementById('text-input'));
        test('Text options group', document.getElementById('text-options-group'));
        test('Text font select', document.getElementById('text-font'));
        test('Text size select', document.getElementById('text-size'));
        test('Text bold button', document.getElementById('text-bold'));
        test('Text italic button', document.getElementById('text-italic'));
        test('Text underline button', document.getElementById('text-underline'));
        test('Text strikethrough button', document.getElementById('text-strikethrough'));

        // View controls
        test('Rulers checkbox', document.getElementById('chk-rulers'));
        test('Gridlines checkbox', document.getElementById('chk-gridlines'));
        test('Zoom slider', document.getElementById('status-zoom-slider'));

        // File inputs
        test('File input', document.getElementById('file-input'));
        test('Paste file input', document.getElementById('paste-file-input'));

        // Quick access toolbar
        test('Save button', document.getElementById('qat-save'));
        test('Undo button', document.getElementById('qat-undo'));
        test('Redo button', document.getElementById('qat-redo'));

        // ============ COLOR PALETTE TESTS ============
        console.log('%c--- Color Palette ---', 'color: #9C27B0; font-weight: bold;');

        const palette = document.getElementById('color-palette');
        const swatches = palette ? palette.querySelectorAll('.color-swatch') : [];
        test('Has 30 color swatches', swatches.length === 30);

        // Check for unique colors
        const colors = Array.from(swatches).map(s => s.style.backgroundColor);
        const uniqueColors = new Set(colors);
        test('All colors unique (no duplicates)', uniqueColors.size === 30);

        // ============ BRUSH TESTS ============
        console.log('%c--- Brushes ---', 'color: #9C27B0; font-weight: bold;');

        const brushes = ['brush', 'calligraphy1', 'calligraphy2', 'airbrush', 'oil', 'crayon', 'marker', 'pencil', 'watercolor'];
        brushes.forEach(brush => {
            test(`Brush: ${brush}`, document.querySelector(`[data-brush="${brush}"]`));
        });

        // ============ COPYRIGHT TEST ============
        console.log('%c--- Misc ---', 'color: #9C27B0; font-weight: bold;');

        const copyright = document.querySelector('.copyright');
        test('Copyright is 2025', copyright && copyright.textContent.includes('2025'));

        // ============ CANVAS FUNCTIONALITY ============
        console.log('%c--- Canvas Functionality ---', 'color: #9C27B0; font-weight: bold;');

        const mainCanvas = document.getElementById('main-canvas');
        test('Canvas has 2D context', mainCanvas && mainCanvas.getContext('2d'));
        test('Canvas has dimensions', mainCanvas && mainCanvas.width > 0 && mainCanvas.height > 0);

        // ============ PRINT RESULTS ============
        console.log('');
        console.log('%c--- Results ---', 'color: #FF9800; font-weight: bold;');

        results.forEach(r => {
            if (r.pass) {
                console.log('%c✓ ' + r.name, 'color: #4CAF50;');
            } else {
                console.log('%c✗ ' + r.name, 'color: #f44336;');
            }
        });

        console.log('');
        const total = passed + failed;
        const percent = Math.round((passed / total) * 100);

        if (failed === 0) {
            console.log('%c ✓ ALL ' + total + ' TESTS PASSED! ', 'background: #4CAF50; color: white; font-size: 14px; padding: 5px;');
        } else {
            console.log('%c Passed: ' + passed + '/' + total + ' (' + percent + '%) ', 'background: #FF9800; color: white; font-size: 14px; padding: 5px;');
            console.log('%c Failed: ' + failed, 'color: #f44336; font-weight: bold;');
        }

        // Show visual indicator
        showVisualResults(passed, failed);

        return { passed, failed, total, percent };
    }

    function showVisualResults(passed, failed) {
        // Create visual overlay
        const overlay = document.createElement('div');
        overlay.id = 'test-results-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${failed === 0 ? '#4CAF50' : '#f44336'};
            color: white;
            padding: 20px 30px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 16px;
            z-index: 99999;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            cursor: pointer;
        `;

        const total = passed + failed;
        if (failed === 0) {
            overlay.innerHTML = `✓ ALL ${total} TESTS PASSED!<br><small>Click to dismiss</small>`;
        } else {
            overlay.innerHTML = `Passed: ${passed}/${total}<br>Failed: ${failed}<br><small>Click to dismiss</small>`;
        }

        overlay.onclick = () => overlay.remove();
        document.body.appendChild(overlay);

        // Auto-dismiss after 10 seconds
        setTimeout(() => {
            if (overlay.parentNode) overlay.remove();
        }, 10000);
    }

    // Auto-run if ?test is in URL
    if (window.location.search.includes('test')) {
        window.addEventListener('load', () => {
            setTimeout(runTests, 500);
        });
    }

    // Expose globally for manual testing
    window.runMattPaintTests = runTests;

    console.log('%c MattPaint Tests Loaded! ', 'background: #333; color: #4CAF50; padding: 3px;');
    console.log('Run tests with: runMattPaintTests()');
    console.log('Or open: index.html?test');

})();
