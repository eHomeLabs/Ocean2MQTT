export type Expose = {
  key: string;
  kind: "switch" | "light" | "cover" | "select" | "number" | "sensor" | "binary_sensor" | "enum" | "event";
  access: "r" | "rw";
  unit?: string;
  device_class?: string;
  state_class?: string;
  category?: string;
  options?: string[];
  min?: number;
  max?: number;
  step?: number;
};

export type Product = {
  id: string;
  brand: string;
  model: string;
  name: string;
  type: string;
  eep: string;
  extra_eeps: string[];
  support: "valide" | "communaute" | "generique";
  teach_in: string;
  steps: string[];
  after: string;
  manual?: string | null;
  image?: string | null;
  variants: string[];
  recom: boolean;
  generic?: boolean;
  i18n?: Record<string, { name: string; steps: string[]; after: string }>;
  exposes: Expose[];
};

export type Setting = {
  key: string;
  kind: "binary" | "enum" | "numeric" | "action";
  group?: "product" | "local" | "recom";
  options?: string[];
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  channel?: number;
  readable?: boolean;
  value?: unknown;
};

export type Link = { index: number; id: string; eep: string; channel?: number };

export type Recom = {
  secured: boolean;
  pending: boolean;
  has_code: boolean;
  mode?: "auto" | "custom" | "random" | "none" | null;
  links?: Link[] | null;
  links_max?: number | null;
  link_types: string[];
  session_until?: number;
  config: Record<string, unknown>;
};

export type Telegram = {
  time: number;
  dir: "rx" | "tx";
  sender: string;
  destination: string;
  rorg: string;
  data: string;
  status: string;
  dbm?: number | null;
  duplicate?: boolean;
  name?: string | null;
};

export type Unknown = {
  id: string;
  rorg: string;
  count: number;
  first_seen: string;
  last_seen: string;
  rssi?: number;
  eep?: string | null;
  manufacturer?: number | null;
  teach_in?: string | null;
  suggestions: string[];
};

export type RecomLog = { time: string; id: string; name: string; action: string; ok: boolean; detail?: string | null };

export type DeviceState = Record<string, unknown>;

export type Device = {
  id: string;
  name: string;
  room?: string | null;
  topic: string;
  product: Product;
  state: DeviceState;
  available: boolean;
  last_seen?: string | null;
  actuator: boolean;
  settings: Setting[];
  needs_pairing?: boolean;
  recom?: Recom | null;
};

export type Info = {
  version: string;
  gateway: { connected: boolean; port: string; base_id?: string | null; chip_id?: string | null; app_version?: string | null; base_id_writes_left?: number | null };
  mqtt?: { connected: boolean; editable: boolean };
  language: string;
  pairing: { product: string; timeout: number; until: number } | null;
  config: Record<string, Record<string, unknown>>;
  devices: number;
  recom_enabled?: boolean;
  migration?: { nodocean: MigrationSource[]; dismissed: boolean; previous_base_id?: string | null };
};

export type MigrationSource = { kind: "nodocean" | "backup"; base_id?: string | null; active?: boolean | null; port?: string | null; title?: string | null; devices: number };

export type MigrationItem = {
  id: string;
  name: string;
  room?: string | null;
  product: string;
  model: string;
  brand?: string | null;
  actuator: boolean;
  recom: boolean;
  status: "ok" | "repair" | "exists" | "unknown" | "code";
  alternatives?: string[];
  labels?: Record<string, string>;
};

export type MigrationPlan = { source: MigrationSource; mode: "same" | "new"; current_base_id?: string | null; key_mismatch: boolean; items: MigrationItem[] };

export type PairingEvent = {
  status: "started" | "success" | "timeout" | "stopped";
  product?: string;
  timeout?: number;
  until?: number;
} & Partial<Device>;
