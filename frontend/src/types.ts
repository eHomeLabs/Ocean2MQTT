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
  support: "valide" | "communaute";
  teach_in: string;
  steps: string[];
  after: string;
  manual?: string | null;
  image?: string | null;
  variants: string[];
  recom: boolean;
  exposes: Expose[];
};

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
};

export type Info = {
  version: string;
  gateway: { connected: boolean; port: string; base_id?: string | null; chip_id?: string | null; app_version?: string | null };
  language: string;
  pairing: { product: string; timeout: number; until: number } | null;
  config: Record<string, Record<string, unknown>>;
  devices: number;
};

export type PairingEvent = {
  status: "started" | "success" | "timeout" | "stopped";
  product?: string;
  timeout?: number;
  until?: number;
} & Partial<Device>;
