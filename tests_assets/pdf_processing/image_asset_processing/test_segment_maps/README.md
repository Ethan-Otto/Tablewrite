# Test Assets for test_segment_maps.py

This directory contains test assets demonstrating the Gemini image segmentation with red perimeter technique.

## Test Case 1: Strongholds & Followers Page 1

**Source PDF**: `data/pdfs/Strongholds_Followers_extraction_test.pdf` (page 1)

## Test Case 2: Example Keep (Full Page)

**Input**: `input_images/example_keep.png` (3523x4644 - full D&D module page)
**Expected Output**: `output_images/example_keep.png` (2397x1648 - extracted map)

### Output Images

#### 1. `page1_pymupdf_wrong_extraction.png` ❌
- **Method**: PyMuPDF extraction (>25% page area filter)
- **Result**: WRONG - extracted background texture instead of map
- **Dimensions**: 3107x4132 pixels
- **File size**: 6.6MB
- **Issue**: The background texture was larger than the actual map, so PyMuPDF's "largest image" heuristic failed

#### 2. `page1_imagen_segmented_correct.png` ✅
- **Method**: Gemini `gemini-2.5-flash-image` segmentation with red perimeter
- **Result**: CORRECT - extracted the actual map with compass rose
- **Dimensions**: 619x427 pixels
- **File size**: 422KB
- **Process**:
  1. Sent full page to Gemini with prompt: "Add a precise 5-pixel red border (RGB 255,0,0) around the navigation map"
  2. Detected 8,753 red pixels (lenient matching: R>200, G<50, B<50)
  3. Calculated bounding box (274,873 px² area)
  4. Cropped original image with 5px inset to remove red border

#### 3. `page1_with_red_perimeter_debug.png` 🔍
- **Method**: Debug output showing Gemini's generated image with red perimeter
- **Dimensions**: Full page with red border around map
- **File size**: 1.8MB
- **Purpose**: Visualize the red perimeter detection before cropping

## Key Findings

1. **PyMuPDF fails on baked-in maps**: When the background texture is larger than the actual map content, PyMuPDF's heuristic of "largest image >25% page area" extracts the wrong image.

2. **Gemini segmentation succeeds**: The AI correctly identifies the semantic content (the map) rather than just the largest embedded image.

3. **Red perimeter technique works**: With lenient red pixel detection (to account for compression artifacts), the technique reliably segments maps from full pages.

## Critical Bug Fixed: Resolution Scaling

**Problem**: Gemini downscales input images (3523x4644 → 896x1152, 3.93x smaller). Red pixel detection worked on the downscaled image, but we cropped the original full-resolution image using downscaled coordinates, resulting in a tiny 625x427 extraction instead of the full 2763x1726 map.

**Solution**: Scale bounding box coordinates back up to match original resolution:
```python
scale_x = original_img.width / generated_img.width  # 3.93x
scale_y = original_img.height / generated_img.height  # 4.03x

x_min = int(x_min_downscaled * scale_x)
y_min = int(y_min_downscaled * scale_y)
# ... etc
```

**Before fix**: Extracted 625x427 (wrong region - decorative header)
**After fix**: Extracted 2763x1726 (correct - full map)

## Validation

Run `test_segmentation_comparison.py` to regenerate these results and compare both methods side-by-side.

Run `debug_segmentation.py` to test segmentation on the Example Keep input and compare against expected output.
