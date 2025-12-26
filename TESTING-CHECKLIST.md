# MattPaint Interactive Testing Checklist

Use this checklist to manually verify all features work correctly.

---

## 1. Basic Drawing Tools

### Pencil (P)
- [ ] Press `P` key - Pencil tool should activate
- [ ] Draw on canvas - Should create 1px line
- [ ] Left-click draws with Color 1
- [ ] Right-click draws with Color 2

### Brush (B)
- [ ] Press `B` key - Brush tool should activate
- [ ] Click brushes dropdown
- [ ] Test each brush type:
  - [ ] Standard brush - solid circle
  - [ ] Calligraphy 1 - angled stroke
  - [ ] Calligraphy 2 - opposite angle
  - [ ] Airbrush - spray effect
  - [ ] Oil brush - flat rectangle
  - [ ] Crayon - textured
  - [ ] Marker - semi-transparent (no over-darkening!)
  - [ ] Pencil - thin line
  - [ ] Watercolor - soft transparent

### Eraser (E)
- [ ] Press `E` key - Eraser should activate
- [ ] Erases to background color (Color 2)

### Fill Tool (G)
- [ ] Press `G` key - Fill tool should activate
- [ ] Draw a closed shape, then fill it
- [ ] Test on large area (should not freeze browser)

### Color Picker (I)
- [ ] Press `I` key - Eyedropper should activate
- [ ] Click on colored area - should pick up color

---

## 2. Text Tool

### Basic Text (T)
- [ ] Press `T` key - Text tool should activate
- [ ] Click on canvas - text input appears
- [ ] Type text and click away - text renders

### Text Styles
- [ ] Toggle Bold (B button)
- [ ] Toggle Italic (I button)
- [ ] Toggle Underline (U button) - **Should now render!**
- [ ] Toggle Strikethrough (S button) - **Should now render!**
- [ ] Change font from dropdown
- [ ] Change font size

---

## 3. Shape Tools

### Draw Shapes
- [ ] Line (L key)
- [ ] Curve - drag up = curve up, drag down = curve down **NEW!**
- [ ] Rectangle (R key)
- [ ] Oval (O key)
- [ ] Rounded rectangle
- [ ] Polygon
- [ ] Triangle
- [ ] Right triangle
- [ ] Diamond
- [ ] 5-point star
- [ ] 6-point star
- [ ] Arrows (all 4 directions)
- [ ] Heart
- [ ] Lightning bolt

### Shape Styles
- [ ] Click Outline dropdown - change outline style
- [ ] Click Fill dropdown - change fill style
- [ ] Change Size - affects line thickness

---

## 4. Selection Tools

### Rectangular Selection (S)
- [ ] Press `S` key - Selection tool activates
- [ ] Draw rectangle to select area
- [ ] Marching ants animation appears

### Free-form Selection
- [ ] Click Select dropdown > Free-form selection
- [ ] Draw custom shape
- [ ] Selection should respect drawn shape (not just bounding box!) **FIXED!**

### Selection Operations
- [ ] Cmd+C - Copy selection
- [ ] Cmd+X - Cut selection
- [ ] Cmd+V - Paste selection
- [ ] Delete/Backspace - Delete selection
- [ ] Drag selection to move it
- [ ] Image > Crop - Crops to selection

---

## 5. Image Operations

### Rotate/Flip
- [ ] Rotate right 90°
- [ ] Rotate left 90°
- [ ] Rotate 180°
- [ ] Flip horizontal
- [ ] Flip vertical

### Resize/Skew Dialog
- [ ] Image > Resize
- [ ] Change percentage - both inputs update with aspect ratio **FIXED!**
- [ ] Switch to Pixels - labels update to "px" **FIXED!**
- [ ] Uncheck "Maintain aspect ratio" - inputs independent
- [ ] Enter skew values - image skews **NOW WORKS!**

---

## 6. View Controls

### Zoom
- [ ] Press `+` key - Zoom in
- [ ] Press `-` key - Zoom out
- [ ] Drag zoom slider - zoom changes
- [ ] Press `Z` key - Magnifier tool

### Display Options
- [ ] View tab > Rulers checkbox - **Rulers now show markings!**
- [ ] View tab > Gridlines checkbox - Grid overlay appears
- [ ] View tab > Status bar checkbox - Toggle status bar
- [ ] Resize canvas - gridlines/rulers update **FIXED!**

---

## 7. Color System

### Color Palette
- [ ] All 30 colors are unique (no duplicates) **FIXED!**
- [ ] Click color with left mouse - sets Color 1
- [ ] Click color with right mouse - sets Color 2

### Color Picker Dialog
- [ ] Click "Edit colors" or double-click color box
- [ ] HSV gradient picker works
- [ ] Hue slider works
- [ ] RGB input fields work
- [ ] Short hex codes work (e.g., #FFF) **FIXED!**
- [ ] Add to Custom Colors button

---

## 8. File Operations

### New/Open/Save
- [ ] Cmd+N - New file (prompts if unsaved)
- [ ] Cmd+O - Open image file
- [ ] Cmd+S - Save as PNG
- [ ] File > Save As - Choose format

### Other Operations
- [ ] File > Print - Opens print dialog **Handles popup blockers!**
- [ ] File > Properties - Shows dimensions
- [ ] File > About - Shows about dialog (Copyright 2025) **FIXED!**
- [ ] Drag & drop image onto canvas

---

## 9. Keyboard Shortcuts

### Tool Shortcuts
- [ ] P = Pencil
- [ ] B = Brush
- [ ] E = Eraser
- [ ] G = Fill (paint bucket)
- [ ] T = Text
- [ ] I = Color picker (eyedropper)
- [ ] S = Selection
- [ ] Z = Magnifier

### Shape Shortcuts
- [ ] L = Line
- [ ] R = Rectangle
- [ ] O = Oval

### Edit Shortcuts
- [ ] Cmd+Z = Undo
- [ ] Cmd+Shift+Z = Redo
- [ ] Cmd+Y = Redo
- [ ] Cmd+A = Select All
- [ ] Escape = Deselect / Close dialogs

---

## 10. Touch Support (on iPad/tablet)

- [ ] Touch to draw
- [ ] Touch and drag for brush strokes
- [ ] Touch selection handles to resize
- [ ] Pinch to zoom (if implemented)

---

## 11. Canvas Operations

### Resize Handles
- [ ] Drag right edge - expands width
- [ ] Drag bottom edge - expands height
- [ ] Drag corner - expands both

### Canvas Coordinates
- [ ] Mouse position shows in status bar
- [ ] Coordinates clamp to canvas bounds (no negative values) **FIXED!**

---

## Quick Verification Commands

Open browser console (Cmd+Option+J) and run:

```javascript
// Check palette has unique colors
const colors = [...document.querySelectorAll('#color-palette .color-swatch')].map(s => s.style.backgroundColor);
console.log('Unique colors:', new Set(colors).size, '/ 30');

// Check canvas exists
console.log('Canvas:', document.getElementById('main-canvas') ? 'OK' : 'MISSING');

// Check state exists (inside IIFE, can't access directly)
console.log('App loaded:', typeof init !== 'undefined' ? 'YES' : 'Encapsulated (OK)');
```

---

## Test Complete!

If all checkboxes are checked, MattPaint is fully functional!

Report any issues to the developer.
