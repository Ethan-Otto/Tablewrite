# GitHub Actions Setup Guide

This guide explains how to configure GitHub Actions to automatically run tests on pull requests.

## Required Setup

### 1. Add Gemini API Key as GitHub Secret

Integration tests require a Gemini API key to function. Follow these steps:

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Create a secret with:
   - **Name**: `GEMINI_API_KEY`
   - **Value**: Your Gemini API key (the same value as `GeminiImageAPI` in your local `.env` file)
5. Click **Add secret**

### 2. PDF Files

All PDF files (including test PDFs) are included in the repository and will be available to GitHub Actions automatically:
- `Lost_Mine_of_Phandelver.pdf` (53MB) - Full PDF for TOC tests
- `Lost_Mine_of_Phandelver_small.pdf` (47MB) - Small version
- `Lost_Mine_of_Phandelver_test.pdf` (6.2MB) - Test PDF for most tests

## Workflow Behavior

The GitHub Actions workflow (`.github/workflows/test.yml`) will:

- ✅ Run on all pull requests to `main` or `master`
- ✅ Use Python 3.11
- ✅ Install dependencies using `uv`
- ✅ Install Tesseract OCR for text extraction
- ✅ Run **all tests** including integration tests
- ✅ Upload test artifacts if tests fail

### Tests That Will Run

1. **Unit tests** (fast, no API calls):
   - PDF splitting and validation
   - XML sanitization and parsing
   - Word counting
   - HTML generation
   - Error handling

2. **Integration tests** (make real Gemini API calls):
   - End-to-end pipeline (PDF → XML → HTML)
   - Gemini API XML generation
   - Note: These will fail if `GEMINI_API_KEY` secret is not configured

3. **All tests enabled**:
   - TOC tests will use the full PDF (53MB, included in repo)
   - No tests will be skipped due to missing files

## Current API Issue

**Note**: As of October 2025, there's a known issue with the Google Generative AI library (`ragStoreName` parameter error) that causes file upload to fail. Integration tests are set to `continue-on-error: true` in the workflow, so they won't block PRs.

This will be fixed when Google resolves the API issue.

## Viewing Test Results

1. Go to your pull request
2. Click the **Checks** tab
3. Click **Run Tests** to see detailed output
4. If tests fail, download test artifacts under **Summary** → **Artifacts**

## Local Testing

To test the same workflow locally:

```bash
# Run all tests (same as CI)
uv run pytest tests/ -v

# Run only unit tests (fast)
uv run pytest tests/ -v -m "not integration and not slow"

# Run only integration tests
uv run pytest tests/ -v -m "integration"
```

## Troubleshooting

### Tests fail with "Gemini API key not found"
- Ensure you've added the `GEMINI_API_KEY` secret to your repository settings
- Check that the secret name is exactly `GEMINI_API_KEY` (case-sensitive)

### Tests fail with "Test PDF not found"
- Ensure `data/pdfs/Lost_Mine_of_Phandelver_test.pdf` is committed to the repository
- Check that `.gitignore` is not excluding it

### Integration tests fail with "ragStoreName" error
- This is a known issue with the current Google Generative AI library
- Tests are set to continue on error, so they won't block your PR
- The issue will be resolved when updating to a fixed version of the library
