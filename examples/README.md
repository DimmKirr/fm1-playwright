# Examples

E2E test examples for the FM-1 emulator using Playwright.

Run any example with:

```bash
FM1_WEB_DIR=$HOME/.fm1-emulator/web \
FIRMWARE_NAME=felucca \
RESULTS_DIR=results \
python3 -m unittest examples.e2e_firmware_ui_test -v
```

See [`e2e_firmware_ui_test.py`](e2e_firmware_ui_test.py) for the complete test suite.
