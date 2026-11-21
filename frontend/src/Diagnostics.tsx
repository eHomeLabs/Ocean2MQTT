import { decodedValue } from "./decodedValue";
import { useNow, useStore } from "./api";
import { label, signal, since, t } from "./i18n";
import { TelegramTable } from "./Telegrams";
import type { Device, DeviceState } from "./types";

export function Diagnostics({ device }: { device: Device }) {
  const now = useNow(10000);
  const { telegrams, availability, states } = useStore();
  const received = telegrams.filter((x) => x.dir === "rx" && x.sender === device.id);
  const unique = received.filter((x) => !x.duplicate);
  const samples = unique.flatMap((x) => x.dbm == null ? [] : [-Math.abs(x.dbm)]);
  const last = unique.at(-1);
  const state: DeviceState = states[device.topic] ?? device.state;
  const available = availability[device.topic] ?? device.available;
  return <section className="stack">
    <p className="small muted">{t("diag.scope")}</p>
    <dl className="facts">
      <div><dt>{t("diag.availability")}</dt><dd>{t(available ? "diag.online" : "diag.offline")}</dd></div>
      <div><dt>{t("detail.eep")}</dt><dd><code>{device.product.eep}</code></dd></div>
      <div><dt>{t("diag.last")}</dt><dd>{since(typeof state.last_seen === "string" ? state.last_seen : device.last_seen, now)}</dd></div>
      <div><dt>{t("diag.signal")}</dt><dd>{last?.dbm != null || state.rssi != null ? `${-Math.abs(Number(last?.dbm ?? state.rssi))} dBm · ${signal(last?.dbm ?? state.rssi)}` : "—"}</dd></div>
      <div><dt>{t("diag.received")}</dt><dd>{unique.length}</dd></div>
      <div><dt>{t("diag.duplicates")}</dt><dd>{received.length - unique.length}</dd></div>
      <div><dt>{t("diag.mean")}</dt><dd>{samples.length ? `${Math.round(samples.reduce((a,b) => a+b,0) / samples.length)} dBm` : "—"}</dd></div>
      <div><dt>{t("diag.interval")}</dt><dd>{unique.length > 1 ? `${Math.round((unique.at(-1)!.time - unique[0].time) / (unique.length - 1))} s` : "—"}</dd></div>
    </dl>
    <h3>{t("diag.values")}</h3>
    <dl className="facts">{device.product.exposes.filter((e) => e.key in state).map((e) =>
      <div key={e.key}><dt>{label(e.key)}</dt><dd>{decodedValue(e.key, state[e.key], e.unit)}</dd></div>)}</dl>
    <h3>{t("diag.telegrams")}</h3>
    <TelegramTable telegrams={received.slice(-10)} />
  </section>;
}
