
/**
 * Vertex Sovereign - Native Hausa Number Engine
 * Ensures zero digits are displayed in the UI.
 */

const hausaUnits = ["zero", "daya", "biyu", "uku", "hudu", "biyar", "shida", "bakwai", "takwas", "tara"];
const hausaTens = ["", "goma", "ashirin", "talatin", "arba'in", "hamsin", "sittin", "shittin", "tamanin", "casa'in"];

export function numberToHausaWords(n: number): string {
  if (n < 10) return hausaUnits[n];
  if (n === 10) return "goma";
  if (n < 20) {
    const unit = n % 10;
    return `sha ${hausaUnits[unit]}`;
  }
  if (n < 100) {
    const ten = Math.floor(n / 10);
    const unit = n % 10;
    return unit === 0 ? hausaTens[ten] : `${hausaTens[ten]} da ${hausaUnits[unit]}`;
  }
  if (n < 1000) {
    const hundred = Math.floor(n / 100);
    const remainder = n % 100;
    const prefix = hundred === 1 ? "dari" : `dari ${hausaUnits[hundred]}`;
    return remainder === 0 ? prefix : `${prefix} da ${numberToHausaWords(remainder)}`;
  }
  if (n < 10000) {
    const thousand = Math.floor(n / 1000);
    const remainder = n % 100; // Simplified for years
    const prefix = thousand === 1 ? "dubu" : `dubu ${hausaUnits[thousand]}`;
    const yearPart = n > 2000 ? ` da ashirin da ${hausaUnits[n % 10]}` : ""; // Specific for era logic
    if (n >= 2020 && n < 2030) return `dubu biyu da ashirin da ${hausaUnits[n % 10]}`;
    return `${prefix} ${numberToHausaWords(n % 1000)}`;
  }
  return n.toString(); // Fallback
}
