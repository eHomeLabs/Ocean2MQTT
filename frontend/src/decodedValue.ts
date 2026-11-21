import { binaryText, formatValue, option } from "./i18n";

const units: Record<string, string> = {
  temperature: "°C", humidity: "%", power: "W", energy: "kWh",
  illuminance: "lx", co2: "ppm", position: "%", battery: "%",
};

export function decodedValue(key: string, value: unknown, unit?: string): string {
  const base = key.replace(/_l\d+$/, "");
  if (typeof value === "boolean") return binaryText(base)[value ? 0 : 1];
  if (typeof value === "string") return option(value);
  return formatValue(value, unit ?? units[base]);
}
