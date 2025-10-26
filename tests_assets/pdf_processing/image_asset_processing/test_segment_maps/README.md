# Test Assets for test_segment_maps.py

This directory contains test assets demonstrating the Gemini image segmentation with red perimeter technique.

## Test Case: Strongholds & Followers Page 1

**Source PDF**: `data/pdfs/Strongholds_Followers_extraction_test.pdf` (page 1)

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

## Validation

Run `test_segmentation_comparison.py` to regenerate these results and compare both methods side-by-side.
