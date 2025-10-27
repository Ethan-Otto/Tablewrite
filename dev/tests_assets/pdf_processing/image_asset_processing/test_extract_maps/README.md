# Test Assets for test_extract_maps.py

This directory contains test assets demonstrating the PyMuPDF extraction with AI classification technique.

## Overview

The PyMuPDF extraction system uses a two-stage filtering approach:

1. **Size Filtering**:
   - Images must be ≥200x200px (MIN_IMAGE_SIZE)
   - Images must occupy ≥10% of page area (PAGE_AREA_THRESHOLD)

2. **AI Classification**:
   - All candidates are sent to Gemini Vision in parallel
   - Uses `is_map_image_async()` to classify as map/non-map
   - Returns first image classified as a map

## Test Cases

### Test Case 1: Page 1 - Navigation Map with Background Texture

**Input**: `input_images/test_case_1_page1.png` (full page)
**Output**: `output_images/test_case_1_page1_extracted.png` (2400x1650)

**Challenge**: Page contains both the actual map AND a larger background texture
- Image 1: 2400x1650 (actual map) ✓ Classified as MAP
- Image 2: 3107x4132 (background texture) ✗ Classified as NOT A MAP
- Image 19: 750x750 (decorative element) ✗ Classified as NOT A MAP
- Image 20: 750x750 (decorative element) ✗ Classified as NOT A MAP

**Why AI Classification Matters**: Without AI, PyMuPDF's "largest image" heuristic would extract the 3107x4132 background texture instead of the actual 2400x1650 map. AI classification correctly identifies the semantic content.

### Test Case 2: Page 2 - Vertical Navigation Map

**Input**: `input_images/test_case_2_page2.png` (full page)
**Output**: `output_images/test_case_2_page2_extracted.png` (2400x3300)

**Candidates**:
- Image 1: 2400x3300 (vertical map) ✓ Classified as MAP
- Image 2: 3107x4132 (background texture) ✗ Classified as NOT A MAP
- Image 3: 750x750 (decorative element) ✗ Classified as NOT A MAP
- Image 4: 750x750 (decorative element) ✗ Classified as NOT A MAP

**Success**: AI correctly identified the vertical format navigation map despite the larger background texture.

### Test Case 3: Page 6 - Horizontal Battle Map

**Input**: `input_images/test_case_3_page6.png` (full page)
**Output**: `output_images/test_case_3_page6_extracted.png` (2386x1640)

**Candidates**:
- Image 1: 3107x4132 (background texture) ✗ Classified as NOT A MAP
- Image 2: 750x750 (decorative element) ✗ Classified as NOT A MAP
- Image 3: 750x750 (decorative element) ✗ Classified as NOT A MAP
- Image 4: 2386x1640 (horizontal map) ✓ Classified as MAP

**Success**: AI correctly identified the battle map even when it wasn't the largest candidate.

## Key Findings

1. **Background Texture Problem**: All pages have a 3107x4132 background texture larger than the actual maps. Without AI classification, PyMuPDF's largest-image heuristic fails 100% of the time on these pages.

2. **AI Classification Success Rate**: 3/3 pages correctly identified (100% accuracy)

3. **Parallel Processing**: All candidates classified in parallel using `asyncio.gather()`, making the process fast despite multiple API calls per page.

4. **Size Filtering Effectiveness**:
   - Filters out small decorative images (61x320, 298x57, etc.)
   - Reduces candidates from ~27 images to ~4 images per page
   - Makes AI classification efficient

## Performance

- **Test Case 1**: 4 candidates → ~2-3 seconds for parallel classification
- **Test Case 2**: 4 candidates → ~2-3 seconds for parallel classification
- **Test Case 3**: 4 candidates → ~2-3 seconds for parallel classification

## Validation

Run `test_ai_classification.py` to reproduce the classification results for Page 1.

Run `create_test_cases.py` to regenerate all three test cases and verify extraction works correctly.

## Directory Structure

```
test_extract_maps/
├── README.md (this file)
├── input_images/
│   ├── test_case_1_page1.png (full page 1)
│   ├── test_case_2_page2.png (full page 2)
│   └── test_case_3_page6.png (full page 6)
├── output_images/
│   ├── test_case_1_page1_extracted.png (2400x1650 map)
│   ├── test_case_2_page2_extracted.png (2400x3300 map)
│   └── test_case_3_page6_extracted.png (2386x1640 map)
└── extracted_images/
    ├── candidate_*.jpeg (individual candidates from page 1)
    └── WINNER_image1_2400x1650.jpeg (winning map from page 1)
```

## Related Files

- `src/pdf_processing/image_asset_processing/extract_maps.py` - Main extraction implementation
- `src/pdf_processing/image_asset_processing/detect_maps.py` - AI classification implementation
- `tests/pdf_processing/image_asset_processing/test_extract_maps.py` - Unit and integration tests
