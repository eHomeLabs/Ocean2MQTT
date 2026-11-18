// Connexion WebSocket au service (même API que MQTT : topics + bridge/request/…)
import { useEffect, useState, useSyncExternalStore } from "react";
import { defaultLang } from "./i18n";
import type { Device, DeviceState, Info, PairingEvent, RecomLog, Telegram, Unknown } from "./types";

const TELEGRAMS_MAX = 500;

type Message = { topic: string; payload: unknown };
type Pending = { resolve: (v: unknown) => void; reject: (e: Error) => void };

type Snapshot = {
  connected: boolean;
  info: Info | null;
  devices: Device[];
  states: Record<string, DeviceState>;
  availability: Record<string, boolean>;
  actions: Record<string, { event: string; at: number }>;
  pairing: PairingEvent | null;
  error: string | null;
  telegrams: Telegram[];
  unknown: Unknown[];
  suggestion: Unknown | null;
  recomLog: RecomLog[];
};

let snapshot: Snapshot = {
  connected: false,
  info: null,
  devices: [],
  states: {},
  availability: {},
  actions: {},
  pairing: null,
  error: null,
  telegrams: [],
  unknown: [],
  suggestion: null,
  recomLog: [],
};
let paused = false;
const listeners = new Set<() => void>();
const pending = new Map<number, Pending>();
let socket: WebSocket | null = null;
let transaction = 0;

function set(patch: Partial<Snapshot>) {
  snapshot = { ...snapshot, ...patch };
  listeners.forEach((l) => l());
}

function onMessage({ topic, payload }: Message) {
  if (topic === "bridge/info") {
    defaultLang((payload as Info).language);
    return set({ info: payload as Info });
  }
  if (topic === "bridge/telegrams") {
    if (paused) return;
    const list = snapshot.telegrams.length >= TELEGRAMS_MAX ? snapshot.telegrams.slice(1) : snapshot.telegrams;
    return set({ telegrams: [...list, payload as Telegram] });
  }
  if (topic === "bridge/unknown") return set({ unknown: payload as Unknown[] });
  if (topic === "bridge/devices") return set({ devices: payload as Device[] });
  if (topic === "bridge/state") return;
  if (topic.startsWith("bridge/response/")) {
    const p = payload as { status: string; data?: unknown; error?: string; transaction?: number };
    const waiter = p.transaction !== undefined ? pending.get(p.transaction) : undefined;
    if (waiter) {
      pending.delete(p.transaction!);
      if (p.status === "ok") waiter.resolve(p.data);
      else waiter.reject(new Error(p.error || "Erreur"));
    }
    return;
  }
  if (topic === "bridge/event") {
    const ev = payload as { type: string; data: PairingEvent & { message?: string } };
    if (ev.type === "pairing") set({ pairing: ev.data });
    if (ev.type === "suggestion") set({ suggestion: ev.data as unknown as Unknown });
    if (ev.type === "recom") set({ recomLog: [...snapshot.recomLog.slice(-199), ev.data as unknown as RecomLog] });
    if (ev.type === "error") set({ error: ev.data.message ?? "Erreur" });
    return;
  }
  if (topic.startsWith("bridge/")) return;
  if (topic.endsWith("/availability")) {
    const name = topic.slice(0, -"/availability".length);
    return set({ availability: { ...snapshot.availability, [name]: payload === "online" } });
  }
  if (topic.endsWith("/action")) {
    const name = topic.slice(0, -"/action".length);
    return set({ actions: { ...snapshot.actions, [name]: { event: String(payload), at: Date.now() } } });
  }
  if (payload === "" || payload === null) return;
  set({ states: { ...snapshot.states, [topic]: payload as DeviceState } });
}

export function connect() {
  const url = new URL("api", window.location.href);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  socket = new WebSocket(url);
  socket.onopen = () => {
    set({ connected: true });
    // Historique : journal radio, émetteurs inconnus, journal ReCom
    request<Telegram[]>("telegrams").then((list) => set({ telegrams: list.slice(-TELEGRAMS_MAX) })).catch(() => {});
    request<Unknown[]>("unknown").then((list) => set({ unknown: list })).catch(() => {});
    request<RecomLog[]>("recom/log").then((list) => set({ recomLog: list })).catch(() => {});
  };
  socket.onmessage = (e) => {
    try {
      onMessage(JSON.parse(e.data));
    } catch {
      /* message ignoré */
    }
  };
  socket.onclose = () => {
    set({ connected: false });
    pending.forEach((p) => p.reject(new Error("Connexion perdue")));
    pending.clear();
    setTimeout(connect, 3000);
  };
}

export function request<T = unknown>(command: string, data: Record<string, unknown> = {}): Promise<T> {
  return new Promise((resolve, reject) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) return reject(new Error("Non connecté au service"));
    const id = ++transaction;
    pending.set(id, { resolve: resolve as (v: unknown) => void, reject });
    socket.send(JSON.stringify({ topic: `bridge/request/${command}`, payload: { ...data, transaction: id } }));
    setTimeout(() => {
      if (pending.delete(id)) reject(new Error("Pas de réponse du service"));
    }, 15000);
  });
}

export function sendCommand(device: Device, payload: Record<string, unknown>) {
  return request("device/set", { id: device.id, payload });
}

export function clearError() {
  set({ error: null });
}

export function clearPairing() {
  set({ pairing: null });
}

export function clearSuggestion() {
  set({ suggestion: null });
}

export function clearTelegrams() {
  set({ telegrams: [] });
}

export function pauseTelegrams(value: boolean) {
  paused = value;
}

/** Nouveau rendu après un changement de langue. */
export function refresh() {
  set({});
}

export function useStore(): Snapshot {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => listeners.delete(l);
    },
    () => snapshot,
  );
}

/** Horloge pour les comptes à rebours et « vu il y a… ». */
export function useNow(intervalMs = 1000) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(t);
  }, [intervalMs]);
  return now;
}
