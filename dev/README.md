# Development Scripts

This directory contains development and debugging scripts used during the development of the image asset extraction feature. These are **not production code** and **not part of the test suite** (see `tests/` for proper pytest tests).

## Script Categories

### Debugging Scripts
- **`debug_segmentation.py`** - Debug Gemini Imagen segmentation with red perimeter technique
  - Compares segmentation output against reference images
  - Outputs: Visualizations and debug logs

- **`debug_red_detection.py`** - Debug red pixel detection thresholds
  - Tests different RGB thresholds for detecting red perimeter
  - Outputs: Detection statistics

- **`check_corners.py`** - Test corner detection algorithms
  - Experiments with corner detection for bounding box refinement

### Benchmarking & Performance
- **`benchmark_segmentation.py`** - Reliability testing with multiple iterations
  - Runs segmentation 10 times on same page to measure consistency
  - Compares outputs against reference images
  - Usage: `python benchmark_segmentation.py [test_case] [temperature]`
  - Outputs: `../dev_output/segmentation_benchmarks/runs/{test_case}_{timestamp}/`

- **`sweep_temperature_params.py`** - Temperature parameter sweep (0.0 to 1.0)
  - Tests segmentation across temperature range to find optimal setting
  - Runs 10 attempts per temperature per test case
  - Usage: `python sweep_temperature_params.py`
  - Outputs: `../dev_output/segmentation_benchmarks/runs/`

### Comparison & Verification
- **`compare_segmentation_methods.py`** - Compare PyMuPDF vs Imagen segmentation
  - Side-by-side comparison of extraction methods
  - Outputs: Visual comparisons and metrics

- **`verify_ai_classification.py`** - Test AI classification accuracy
  - Validates Gemini Vision's ability to distinguish maps from textures
  - Outputs: `tests_assets/pdf_processing/image_asset_processing/test_extract_maps/extracted_images/`

### Experiments
- **`experiment_region_growing.py`** - Region growing algorithm experiments
  - Tested alternative segmentation approach (not used in production)
  - Outputs: `../dev_output/region_growing_experiments/`

### Utilities
- **`create_test_cases.py`** - Create reference test cases from PDFs
  - Extracts pages and creates test case structure
  - Outputs: `tests_assets/pdf_processing/image_asset_processing/test_extract_maps/`

- **`extract_test_page.py`** - Extract single PDF page for testing
  - Quick utility to export a page as PNG
  - Outputs: `tests_assets/pdf_processing/image_asset_processing/test_extract_maps/`

- **`scan_pdf_pages.py`** - Scan PDF for image content
  - Lists all embedded images in PDF pages

## Reference Data

### `tests_assets/`
Contains reference images and documentation for development testing:

- `test_extract_maps/` - PyMuPDF extraction reference cases
  - `input_images/` - Full PDF pages
  - `output_images/` - Expected extraction results
  - `README.md` - Detailed test case documentation

- `test_segment_maps/` - Imagen segmentation reference cases
  - `input_images/` - Full PDF pages
  - `output_images/` - Expected segmentation results
  - `README.md` - Detailed test case documentation

**Note:** These are NOT used by pytest (tests use actual PDFs from `data/pdfs/`). These are reference materials for manual comparison and algorithm development.

## Output Directory

All dev script outputs go to `../dev_output/`:

```
dev_output/
├── segmentation_benchmarks/
│   ├── test_cases/              # Input test cases
│   │   ├── cragmaw_hideout/
│   │   │   ├── page.png         # Full page
│   │   │   └── reference.png    # Known good extraction
│   │   └── example_keep_small/
│   └── runs/                    # Timestamped benchmark runs
│       └── {test_case}_{timestamp}/
│           ├── attempt_01_pass.png
│           ├── attempt_02_pass.png
│           └── temp/            # Debug files
├── region_growing_experiments/
├── debug_segmentation/
├── maps/
├── segmentation_experiments/
├── region_growing_50kernel.log
├── segmentation_experiments.log
└── temperature_sweep.log
```

## Usage

Run scripts from the project root, not from this directory:

```bash
# From project root
cd /path/to/dnd_module_gen

# Benchmark segmentation
python dev/benchmark_segmentation.py cragmaw_hideout 0.5

# Temperature sweep
python dev/sweep_temperature_params.py

# Debug segmentation
python dev/debug_segmentation.py
```

## Relationship to Production Code

- **Production code:** `src/pdf_processing/image_asset_processing/`
- **Production tests:** `tests/pdf_processing/image_asset_processing/`
- **Development scripts:** `dev/` (this directory)
- **Development outputs:** `dev_output/`

These scripts were used to develop and tune the algorithms now in production. They're kept for future debugging and experimentation.
