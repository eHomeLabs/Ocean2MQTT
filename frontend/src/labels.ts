// Textes de l'interface (français pour l'alpha ; traductions EN / DE en bêta)
export const LABELS: Record<string, string> = {
  temperature: "Température",
  humidity: "Humidité",
  power: "Puissance",
  energy: "Énergie",
  illuminance: "Luminosité",
  voltage: "Tension",
  battery: "Batterie",
  co2: "CO2",
  voc: "COV",
  valve_position: "Ouverture vanne",
  setpoint: "Consigne",
  rssi: "Signal",
  mode: "Mode fil pilote",
  position: "Position",
  open: "Ouverture",
  motion: "Mouvement",
  card: "Carte",
  water_leak: "Fuite d'eau",
  window_open: "Fenêtre",
  battery_low: "Pile",
  handle: "Poignée",
  action: "Dernière action",
  state: "Marche / arrêt",
};

export const OPTION_LABELS: Record<string, string> = {
  off: "Arrêt",
  comfort: "Confort",
  eco: "Éco",
  frost_protection: "Hors-gel",
  comfort_1: "Confort -1",
  comfort_2: "Confort -2",
  closed: "Fermée",
  open: "Ouverte",
  tilt: "Oscillo-battant",
  left_up: "Gauche haut",
  left_down: "Gauche bas",
  right_up: "Droite haut",
  right_down: "Droite bas",
  release: "Relâché",
  press: "Appui",
  single: "Appui simple",
  double: "Double appui",
  long: "Appui long",
  long_release: "Fin d'appui long",
};

export const BINARY_TEXT: Record<string, [string, string]> = {
  open: ["Ouvert", "Fermé"],
  motion: ["Mouvement", "Calme"],
  card: ["Carte insérée", "Pas de carte"],
  water_leak: ["Eau détectée", "Sec"],
  window_open: ["Ouverte", "Fermée"],
  battery_low: ["Faible", "OK"],
};

export const TYPES: Record<string, string> = {
  actionneur: "Actionneurs",
  chauffage: "Chauffage",
  prise: "Prises",
  interrupteur: "Interrupteurs",
  capteur: "Capteurs",
};

export const TEACH_IN: Record<string, string> = {
  ute_bidir: "UTE bidirectionnel",
  ute_uni: "UTE",
  "1bs": "1BS",
  "4bs": "4BS",
  "4bs_bidir": "4BS bidirectionnel",
  rps: "Premier appui",
};

export function label(key: string): string {
  if (key.startsWith("state_l")) return `Canal ${key.slice(7)}`;
  return LABELS[key] ?? key;
}

export function option(value: string): string {
  return OPTION_LABELS[value] ?? value.replaceAll("_", " ");
}

export function formatValue(value: unknown, unit?: string): string {
  if (value === undefined || value === null) return "—";
  if (typeof value === "number") {
    const text = value.toLocaleString("fr-FR", { maximumFractionDigits: 2 });
    return unit ? `${text} ${unit}` : text;
  }
  return String(value);
}

export function since(iso: string | null | undefined, now: number): string {
  if (!iso) return "jamais vu";
  const s = Math.max(0, Math.round((now - Date.parse(iso)) / 1000));
  if (s < 60) return `vu il y a ${s} s`;
  if (s < 3600) return `vu il y a ${Math.round(s / 60)} min`;
  if (s < 86400) return `vu il y a ${Math.round(s / 3600)} h`;
  return `vu il y a ${Math.round(s / 86400)} j`;
}

export function signal(rssi: unknown): string {
  if (typeof rssi !== "number") return "";
  const dbm = rssi > 0 ? -rssi : rssi;
  if (dbm >= -70) return "signal bon";
  if (dbm >= -85) return "signal moyen";
  return "signal faible";
}
