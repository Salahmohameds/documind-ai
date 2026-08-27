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

/**
 * Hands a generated JSON file to the browser.
 *
 * Same shape as `downloadCsv` — the payload is serialised from data the client
 * already holds, so nothing round-trips through a service. Pretty-printed
 * because these files are read by people as often as they are parsed.
 */
export function downloadJson(file: { filename: string; data: unknown }): void {
  const blob = new Blob([`${JSON.stringify(file.data, null, 2)}\n`], {
    type: "application/json;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);

  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = file.filename;
  // Safari ignores a click on an anchor that is not in the document.
  anchor.style.display = "none";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();

  requestAnimationFrame(() => URL.revokeObjectURL(url));
}
