# Printing Options Specification

## Supported Formats & Configurations

This document specifies the exact printing parameters supported by the printing service.

---

## 1. Supported Document Types

- **Format**: PDF (`.pdf`) only.
- **Maximum File Size**: 25 MB per upload.
- **Page Limits**: 1 to 500 pages per job.
- **Validation**: PyMuPDF (`fitz`) validates file integrity and determines page count. Corrupted or password-protected PDFs are rejected with a clear message.

---

## 2. Supported Print Options

### Paper Size
- **A4** (210 $\times$ 297 mm) — Standard 75 GSM paper.
- Other paper sizes (A3, Letter, Legal) are not supported in MVP.

### Color Modes
- **Black & White (`bw`)**: High-contrast grayscale output.
- **Color (`color`)**: Standard full-color CMYK output.

### Copies
- **Minimum**: 1
- **Maximum**: 50 copies per job.
- **Default**: 1 copy if unspecified.

### Duplex (Orientation & Sides)
- **Single-Sided (`single`)**: Default. Prints on one side of each sheet.
- **Double-Sided (`double`)**: Prints on both sides of each sheet (duplex long-edge).

---

## 3. Option Selection Flow

1. Customer uploads PDF document.
2. System confirms receipt and page count.
3. Customer provides preferences (or agent prompts for color and copy count).
4. Agent extracts options and validates against allowed values:
   - `copies` $\in [1, 50]$
   - `color` $\in \{\text{"bw"}, \text{"color"}\}$
   - `duplex` $\in \{\text{"single"}, \text{"double"}\}$
5. Options are confirmed before price calculation.
