"use client";

/**
 * Hands a generated CSV to the browser.
 *
 * Exports are built from data the client already holds (see `exportDocuments`
 * in `lib/api.ts`), so the file never round-trips through a service. The object
 * URL is revoked on the next frame — long enough for the click to be handled,
 * short enough not to pin the blob in memory.
 */
export function downloadCsv(file: { filename: string; csv: string }): void {
  // A BOM so Excel opens UTF-8 correctly instead of mangling non-ASCII names.
  const blob = new Blob([`\ufeff${file.csv}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);

  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = file.filename;
  anchor.click();

  requestAnimationFrame(() => URL.revokeObjectURL(url));
}
