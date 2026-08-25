/**
 * Static fixtures used only by the `/states` design gallery, which documents
 * the visual language rather than driving a live screen. Everything the real
 * screens render now comes from `lib/api.ts`.
 */

/** name, score, level, tone */
export const RISK_CATEGORIES: [string, number, string, "--bad" | "--warn" | "--ok"][] = [
  ["Financial", 84, "High", "--bad"],
  ["Legal", 58, "Medium", "--warn"],
  ["Operational", 71, "High", "--bad"],
];
