# Local English screenshot OCR

**Super+Shift+X** keeps the existing QuickShell ii region selector, then copies recognized English text to the clipboard. A short-lived helper replaces the shared Tesseract action. The non-QuickShell fallback uses the same helper with `--select` (slurp + grim). Other screenshot actions and the region-selection components are unchanged.

The runtime uses RapidOCR3.10.0 and CPU ONNX Runtime1.31.1, isolated under `~/.local/share/rdp-screen-ocr/venv` with Python3.12. It does not install packages into system Python. The tiny launcher uses system Python's standard library only, then execs the isolated interpreter; it does not remain resident.

## Models and runtime

Selected models in `~/.local/share/rdp-screen-ocr/models/`:

- `ch_PP-OCRv5_det_mobile.onnx`:4819576bytes, lightweight text-region detector. The v5 detector route is shared across languages; this does not select multilingual recognition.
- `en_PP-OCRv5_rec_mobile.onnx`:7872351bytes, explicitly selected **English** mobile recognition. Its character dictionary is embedded in the ONNX model.

`models.json` pins official RapidAI download URLs and SHA256 values. Setup downloads and verifies both files. Runtime supplies explicit local paths, verifies their hashes, disables dependency download calls and does not use a remote API. Genuine network-disabled execution was tested. Orientation classification, document correction, word/character-box generation, GPU providers and telemetry are disabled/not used. Detector and recognizer use CPU only, at most four intra-op threads each, one inter-op thread; stages execute sequentially. OpenCV and BLAS pools are bounded separately.

A fresh process loads the models only when triggered and exits afterward. No OCR daemon/service is installed. The ordinary `wl-copy` clipboard owner may remain, as in the previous workflow; it is not an OCR worker. Selected model files total about12.1MiB; the complete isolated environment occupies about350MiB on this machine (native Python/OpenCV/NumPy/ONNX dependencies included).

## Text layout and preprocessing

Text coordinates group regions into reading lines and sort fragments left to right. Vertical gaps estimate blank lines; horizontal offsets estimate indentation and fragment spacing relative to the leftmost recognized text. Local ink edges refine detector padding for layout only. Recognition pixels are not thresholded by that refinement. The helper emits plain text: it does not generate Markdown, repair punctuation, infer program syntax or rewrite recognized words.

Clear light screenshots retain their pixels. Genuinely dark screenshots are conditionally complemented while retaining antialiasing and colour differences. There is no blanket threshold or enlargement. The detector performs its required model resize, capped at1600px on the longer side; extremely small glyphs and large captures can still lose detail. No document unwarping or orientation model runs for normal upright screenshots.

Geometry cannot guarantee exact whitespace in proportional fonts, arbitrary columns/tables, text already merged by detection, or regions that omit the leftmost indentation baseline. Inspect OCR output before executing extracted code. See [BENCHMARK.md](BENCHMARK.md) for measured improvements and remaining recognition/layout errors.

## Failure behaviour

Empty recognition, damaged/missing models, invalid crops, dependency failures and busy captures notify the user without invoking `wl-copy`. Recognized output reaches `wl-copy` in one write only after non-empty recognition succeeds. Screenshot paths and crop coordinates are passed as separate arguments, without shell interpolation. Paths with quotes/spaces are covered by tests.

A per-user nonblocking lock prevents overlapping OCR inference. Disposable inputs are removed on success/failure when the caller supplies `--delete-input`; identity checks avoid removing a newer capture that reused the filename. Fallback captures live in a private temporary directory and are cleaned after success/cancellation/failure. The helper rejects symlink/unowned inputs and images larger than25megapixels. No screenshot, recognized text, clipboard backup or credential is stored in Git. The checked-in samples and output are authored synthetic fixtures and dedicated generic Qt test windows.

## Reproduce

Prerequisites: `uv`, Python3.12 (uv can obtain it), `wl-copy`, `notify-send`; fallback also requires slurp/grim. The system's Tesseract/ImageMagick remain installed for rollback and the comparison benchmark.

From this directory:

```bash
python3 setup.py
python3 test_ocr.py
python3 customizations.py check --config-root "$HOME/.config"
python3 customizations.py install --config-root "$HOME/.config"
hyprctl reload config-only
hyprctl configerrors
```

Setup pins the environment using `requirements.lock` and downloads models only during setup. Do not run setup as root. The installer preflights both modified integration files and all assets, snapshots previous files privately, installs dependencies before consumers, refuses unknown versions/concurrent edits and rolls back partial writes. The live shell hot-reloads the shared action; normal captures thereafter work offline. No real `.env` files are created or changed.

Source package: `Linux/End-4/ocr/`. Identical fork copy: `dots-hyprland/dots/.config/hypr/custom/ocr/`; its launcher is also mirrored in `dots/.config/hypr/custom/scripts/screen-ocr`. The fork's base upstream QML/Lua files remain clean in Git. The checked installer patches the installed runtime after upstream setup. It recognizes the inspected live and latest-fork keybind variants without discarding unrelated bindings. Unknown future upstream changes stop before writes and need deliberate review; do not whitelist an unknown version simply to bypass the guard.

Reapply this OCR layer after the other documented desktop integrations when deliberately reinstalling/updating end-4. Fetching/merging upstream alone does not overwrite the running desktop. Never rerun an older layer's installer over a later unrecognized layer.

## Rollback

The installer prints a backup under `~/.local/state/hypr-ocr-backups/`. Restore it with:

```bash
python3 customizations.py restore --config-root "$HOME/.config" --backup /path/printed/by/install
hyprctl reload config-only
hyprctl configerrors
```

For this machine, the consolidated pre-feature rollback snapshot is:
`/home/rdp/.local/state/hypr-ocr-backups/rollback-tns6vu6j`.
It restores the original Tesseract shared action/fallback and removes the new runtime assets in one checked transaction. Restore refuses intervening personal edits. The local model/venv directory can remain unused after rollback; remove it separately only if you want its disk space back. No app data or clipboard history is removed by rollback.

## Checks and references

`test_ocr.py`:11 targeted tests for ordering/indentation/blank lines, unchanged text, empty/error clipboard preservation, safe paths, success/cleanup, concurrent capture identity and transactional install/rollback. Additional integration checks exercised the actual QML command arguments, actual evaluated Lua fallback with a home path containing spaces, mocked select/capture/copy/cancel, CPU provider settings and installed helper under a network namespace with networking disabled. No OCR worker remained after completion. Hyprland configerrors and all earlier desktop integration checks were clean after installation.

Official references checked2026-11-09:

- [RapidOCR model routes and English v5 support](https://rapidai.github.io/RapidOCRDocs/main/en/model_list/)
- [RapidOCR API implementation](https://github.com/RapidAI/RapidOCR/blob/main/python/rapidocr/main.py)
- [RapidAI model catalogue/checksums](https://github.com/RapidAI/RapidOCR/blob/main/python/rapidocr/default_models.yaml)
- [ONNX Runtime thread management](https://onnxruntime.ai/docs/performance/tune-performance/threading.html)
