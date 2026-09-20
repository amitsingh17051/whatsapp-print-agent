# Printing Specification & Mock Printer

## Overview

The printing system handles print job creation, queue management, hardware status tracking, and dispatching jobs to printer implementations.

---

## Supported Print Options

| Option | Values | Default | Description |
| :--- | :--- | :--- | :--- |
| **Paper** | `A4` | `A4` | Standard A4 sheet (210 x 297 mm) |
| **Color** | `bw`, `color` | `bw` | Monochrome grayscale vs Full Color |
| **Copies** | Integer $\ge 1$ | `1` | Number of printed sets |
| **Duplex** | `single`, `double` | `single` | Single-sided vs Both sides |

---

## Print Job Lifecycle

```text
[Created] ──▶ [Queued] ──▶ [Printing] ──▶ [Completed]
                                │
                                └──▶ [Failed]
```

1. **Created**: Print job entity instantiated in SQLite after verified payment.
2. **Queued**: Job added to the execution queue.
3. **Printing**: Hardware/Mock printer actively processing pages.
4. **Completed**: All pages processed; customer notified for collection.
5. **Failed**: Error occurred (out of paper, corrupted file, timeout).

---

## MockPrinter Design

For MVP testing, a physical hardware printer is NOT required. The system relies on `MockPrinter`.

### MockPrinter Responsibilities:
- Receives:
  - `job_id`: Unique identifier (e.g. `JOB-1024`).
  - `file_path`: Absolute path to verified PDF.
  - `page_count`: Total document pages.
  - `copies`: Number of copies.
  - `color_mode`: `bw` or `color`.
  - `duplex`: `single` or `double`.
- Simulates realistic hardware processing with an asynchronous worker:
  - Progress logging (e.g. "Processing page 1 of 3").
  - Simulated delay (1-2 seconds per job).
  - Generates confirmation payload and updates job state to `completed`.
  - Stores a mock output representation in `output/` for inspection.

---

## Hardware Extension Point

To connect a physical printer in production:
1. Replace `MockPrinter` with `CUPSPrinter` implementing the same interface.
2. Dispatch command via native Linux CUPS:
   ```bash
   lp -d <printer_name> -n <copies> -o ColorModel=<Gray|CMYK> <file_path>
   ```
