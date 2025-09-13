# OCR Provider Configuration Simplification

## Problem

The OCR provider configuration was overcomplicated and unreliable:

- **Environment variable propagation issues**: Changes to `OCR_PROVIDER` in `.env` weren't being picked up by Docker Compose worker containers
- **Poor default**: System defaulted to `OCR_PROVIDER=stub` which disables OCR entirely
- **Configuration complexity**: Required Docker rebuilds and restarts to apply changes
- **Testing friction**: Made it hard to test real OCR functionality

## Solution

**Simplified to use sensible code defaults:**

1. **Removed environment variable requirement**: Commented out `OCR_PROVIDER` in `.env` and `.env.example`
2. **Better default**: Code now defaults to `tesseract` (useful OCR) instead of `stub` (disabled OCR)
3. **Optional override**: Environment variable still works if explicitly set
4. **No Docker complexity**: Works immediately without container restarts

## Code Changes

### Before
```bash
# .env
OCR_PROVIDER=stub  # Poor default, required for configuration
```

### After
```bash
# .env
# OCR_PROVIDER=tesseract  # Uses code default (tesseract) if not set
```

### Worker Logic (unchanged but now more effective)
```python
# apps/block0_worker/worker.py:193
provider = (os.getenv("OCR_PROVIDER", "tesseract") or "tesseract").strip().lower()
```

## Benefits

✅ **Just works**: OCR enabled by default without configuration
✅ **No Docker issues**: No environment variable propagation problems
✅ **Better testing**: Real OCR works out of the box
✅ **Still flexible**: Can override with `OCR_PROVIDER=ocrmypdf` or `OCR_PROVIDER=stub` if needed
✅ **Cleaner setup**: New developers don't need to configure OCR

## Usage

### Default (recommended)
```bash
# No configuration needed - uses tesseract
docker compose -f infra/docker-compose.yml up -d
```

### Override if needed
```bash
# For PDF-focused OCR
export OCR_PROVIDER=ocrmypdf
docker compose -f infra/docker-compose.yml up -d

# For testing without OCR
export OCR_PROVIDER=stub
docker compose -f infra/docker-compose.yml up -d
```

## Testing

Run `python3 test_ocr_default.py` to verify the logic works correctly.

## Impact

This change makes Block 0a **more usable by default** while maintaining **full flexibility** for advanced use cases. It eliminates a major source of configuration friction without breaking existing functionality.