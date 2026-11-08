# OCR comparison, 2026-11-09

Measured on this Intel i7-1360P/16GB machine with the installed Tesseract languages (`eng+osd`) and the pinned CPU RapidOCR environment.

14 controlled English fixtures:12Pillow-rendered light/dark,10–18px sans/serif/monospace, paragraphs, low contrast and indented code; plus two dedicated native Qt/QuickShell text windows using desktop fonts. Each backend ran three fresh processes per fixture (84process runs total). Models were reloaded each run; OS disk caches were not forcibly cleared, so these are process-cold, not cold-disk boot measurements.

The legacy path included ImageMagick crop, Tesseract startup/inference and cleanup. RapidOCR included launcher/Python/model startup, crop, preprocessing, layout reconstruction and cleanup. Clipboard and notification commands were mocked to avoid disturbing user data; actual clipboard ownership/desktop notification display time and the human region-selection delay are excluded. The same mock clipboard sink was used for both. Timing wraps the complete backend command, not only inference. Peak RSS is measured through Linux wait4.

| Fixture | Tesseract seconds | RapidOCR seconds | Tesseract char errors | RapidOCR char errors |
| --- | ---: | ---: | ---: | ---: |
| light-sans-18 | 0.266 | 0.774 | 0 | 0 |
| dark-sans-16 | 0.508 | 0.842 | 0 | 0 |
| small-light-10 | 0.322 | 0.695 | 4 | 0 |
| small-dark-11 | 0.366 | 0.682 | 3 | 0 |
| serif-paragraph-17 | 0.358 | 0.794 | 0 | 0 |
| sans-paragraph-14 | 0.360 | 0.768 | 0 | 0 |
| mono-code-15 | 0.259 | 0.745 | 5 | 0 |
| dark-code-14 | 0.334 | 0.749 | 3 | 0 |
| small-code-11 | 0.314 | 0.709 | 8 | 0 |
| low-contrast-14 | 0.357 | 0.762 | 0 | 1 |
| single-line-13 | 0.222 | 0.636 | 0 | 0 |
| mono-paragraph-13 | 0.314 | 0.879 | 2 | 0 |
| native-light-14 | 0.447 | 1.055 | 0 | 0 |
| native-dark-code-14 | 0.456 | 1.081 | 0 | 1 |

Character-error distance excludes whitespace, because whitespace layout is evaluated separately. Case/punctuation remain significant. This is a small reproducible task-specific sample, not a general accuracy guarantee.

- Tesseract: 25/1467 character errors (1.70%); median of per-fixture medians 0.346s; peak measured worker RSS 116.0MiB.
- RapidOCR: 2/1467 character errors (0.14%); median of per-fixture medians 0.765s; peak measured worker RSS 355.9MiB.

RapidOCR recovered small text and code punctuation missed by this Tesseract path. It preserved the4/8space indentation in all four code fixtures, including the small11px and native Qt cases; Tesseract flattened those indentation levels. The three paragraph fixtures retained their blank line.

Remaining errors: the low-contrast fixture changed a final full stop to a colon; native dark code dropped one quote and its blank paragraph gap. The11px code output also retained an extra recognized space before a colon. The helper deliberately does not rewrite those results. Complex columns/tables, selection margins and unusual font bearings can still make spacing approximate.

The tradeoff is about2.2× higher median latency and higher transient memory on these samples. No alternative model was substituted: the requested English PP-OCRv5 mobile recognizer is used, paired with the official mobile detector.

Reproduce: `~/.local/share/rdp-screen-ocr/venv/bin/python benchmark.py`. Fixtures and full outputs/timings are in `samples/` and `benchmark-results.json`. Original user screenshots/clipboard contents are not part of the dataset.

The native fixtures can be regenerated with `RDP_OCR_SAMPLE_DIR="$PWD/samples" qs -p "$PWD/native-samples.qml"` on the desktop. This briefly opens a dedicated generic-text window and captures its own contents, not the rest of the desktop.
