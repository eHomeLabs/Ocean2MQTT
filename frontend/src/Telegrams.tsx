import { decodedValue } from "./decodedValue";
// Journal radio en direct : filtres (recherche, produit, sens, RORG, signal…), pause, export CSV
import { useState } from "react";
import { clearTelegrams, pauseTelegrams, useStore } from "./api";
import { label, locale, t } from "./i18n";
import type { Telegram } from "./types";

const RORGS: Record<string, string> = { F6: "RPS", D5: "1BS", A5: "4BS", D2: "VLD", D4: "UTE", D1: "MSC", C5: "SYS_EX" };

type Filters = { q: string; sender: string; rorg: string; dir: "" | "rx" | "tx"; kind: "" | "known" | "unknown"; dbm: string; dups: boolean };
const EMPTY: Filters = { q: "", sender: "", rorg: "", dir: "", kind: "", dbm: "", dups: true };

function loadFilters(): Filters {
  try {
    return { ...EMPTY, ...JSON.parse(sessionStorage.getItem("o2m-tg-filters") || "{}") };
  } catch {
    return EMPTY;
  }
}

export function TelegramsPage() {
  const { telegrams, devices } = useStore();
  const [f, setF] = useState<Filters>(loadFilters);
  const [paused, setPaused] = useState(false);
  const set = (patch: Partial<Filters>) => {
    const next = { ...f, ...patch };
    setF(next);
    try {
      sessionStorage.setItem("o2m-tg-filters", JSON.stringify(next));
    } catch {
      /* stockage indisponible */
    }
  };
  const names = new Map(devices.map((d) => [d.id, d.name]));
  const peer = (x: Telegram) => (x.dir === "tx" ? x.destination : x.sender);
  const senders = Array.from(new Set(telegrams.map(peer))).sort((a, b) => (names.get(a) ?? "~" + a).localeCompare(names.get(b) ?? "~" + b));
  const rorgs = Array.from(new Set(telegrams.map((x) => x.rorg))).sort();
  const q = f.q.trim().toLowerCase();
  const minDbm = f.dbm ? Number(f.dbm) : null;
  const shown = telegrams.filter((x) => {
    const id = peer(x);
    if (f.sender && x.sender !== f.sender && x.destination !== f.sender) return false;
    if (f.rorg && x.rorg !== f.rorg) return false;
    if (f.dir && x.dir !== f.dir) return false;
    if (f.kind === "known" && !names.has(id)) return false;
    if (f.kind === "unknown" && names.has(id)) return false;
    if (minDbm != null && (x.dbm == null || -Math.abs(x.dbm) < minDbm)) return false;
    if (!f.dups && x.duplicate) return false;
    if (q && ![x.sender, x.destination, names.get(id) ?? "", x.name ?? "", x.data, x.eep ?? "", x.rorg, RORGS[x.rorg] ?? ""].join(" ").toLowerCase().includes(q)) return false;
    return true;
  });
  const active = JSON.stringify(f) !== JSON.stringify(EMPTY);
  const exportCsv = () => {
    const head = "time;dir;sender;name;destination;rorg;eep;data;status;dbm;duplicate;decoded";
    const rows = shown.map((x) =>
      [new Date(x.time * 1000).toISOString(), x.dir, x.sender, names.get(peer(x)) ?? x.name ?? "", x.destination, x.rorg, x.eep ?? "", x.data, x.status, x.dbm ?? "", x.duplicate ? 1 : 0, x.decoded ? JSON.stringify(x.decoded) : ""].map((v) => `"${String(v).replaceAll('"', '""')}"`).join(";"),
    );
    const blob = new Blob([[head, ...rows].join("\n")], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `ocean2mqtt-telegrammes-${new Date().toISOString().slice(0, 19).replaceAll(":", "-")}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };
  return (
    <div className="stack">
      <div className="toolbar">
        <p className="muted">{t("tg.intro")}</p>
        <div className="button-row">
          <button
            type="button"
            className="secondary"
            onClick={() => {
              pauseTelegrams(!paused);
              setPaused(!paused);
            }}
          >
            {paused ? t("tg.resume") : t("tg.pause")}
          </button>
          <button type="button" className="secondary" onClick={clearTelegrams}>
            {t("tg.clear")}
          </button>
          <button type="button" className="secondary" onClick={exportCsv} disabled={!shown.length}>
            {t("tg.export")}
          </button>
        </div>
      </div>
      <div className="card tg-filters">
        <label className="field tg-search">
          {t("tg.search")}
          <input type="search" value={f.q} onChange={(e) => set({ q: e.target.value })} placeholder={t("tg.searchHint")} />
        </label>
        <label className="field">
          {t("tg.product")}
          <select value={f.sender} onChange={(e) => set({ sender: e.target.value })}>
            <option value="">{t("tg.allSenders")}</option>
            {f.sender && !senders.includes(f.sender) && <option value={f.sender}>{f.sender}</option>}
            {senders.map((s) => (
              <option key={s} value={s}>
                {names.get(s) ? `${names.get(s)} · ${s}` : s}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          {t("tg.kind")}
          <select value={f.kind} onChange={(e) => set({ kind: e.target.value as Filters["kind"] })}>
            <option value="">{t("tg.all")}</option>
            <option value="known">{t("tg.known")}</option>
            <option value="unknown">{t("tg.unknown")}</option>
          </select>
        </label>
        <label className="field">
          {t("tg.dir")}
          <select value={f.dir} onChange={(e) => set({ dir: e.target.value as Filters["dir"] })}>
            <option value="">{t("tg.all")}</option>
            <option value="rx">← {t("tg.rxMany")}</option>
            <option value="tx">→ {t("tg.txMany")}</option>
          </select>
        </label>
        <label className="field">
          {t("tg.rorg")}
          <select value={f.rorg} onChange={(e) => set({ rorg: e.target.value })}>
            <option value="">{t("tg.all")}</option>
            {f.rorg && !rorgs.includes(f.rorg) && <option value={f.rorg}>{f.rorg}</option>}
            {rorgs.map((r) => (
              <option key={r} value={r}>
                {r} {RORGS[r] ? `(${RORGS[r]})` : ""}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          {t("tg.signal")}
          <select value={f.dbm} onChange={(e) => set({ dbm: e.target.value })}>
            <option value="">{t("tg.all")}</option>
            {["-60", "-70", "-80", "-90"].map((v) => (
              <option key={v} value={v}>
                ≥ {v} dBm
              </option>
            ))}
          </select>
        </label>
        <label className="check tg-dups">
          <input type="checkbox" checked={f.dups} onChange={(e) => set({ dups: e.target.checked })} /> {t("tg.showDups")}
        </label>
        <div className="tg-count">
          <span className="small muted">{t("tg.count", { n: shown.length, total: telegrams.length })}</span>
          {active && (
            <button type="button" className="link small" onClick={() => set(EMPTY)}>
              {t("tg.reset")}
            </button>
          )}
        </div>
      </div>
      <TelegramTable telegrams={shown} names={names} />
    </div>
  );
}

export function TelegramTable({ telegrams, names }: { telegrams: Telegram[]; names?: Map<string, string> }) {
  if (!telegrams.length) return <p className="muted">{t("tg.empty")}</p>;
  return (
    <div className="card table-card">
      <table className="table mono">
        <thead>
          <tr>
            <th>{t("tg.time")}</th>
            <th>{t("tg.dir")}</th>
            <th>{t("tg.sender")}</th>
            <th>{t("tg.rorg")}</th>
            <th>EEP</th>
            <th>{t("tg.data")}</th>
            <th>{t("tg.decoded")}</th>
            <th>{t("tg.dbm")}</th>
          </tr>
        </thead>
        <tbody>
          {[...telegrams].reverse().slice(0, 300).map((x, i) => (
            <tr key={`${x.time}-${i}`} className={x.duplicate ? "dim" : ""}>
              <td>{new Date(x.time * 1000).toLocaleTimeString(locale())}</td>
              <td>{x.dir === "tx" ? `→ ${t("tg.tx")}` : `← ${t("tg.rx")}`}</td>
              <td>
                {x.dir === "tx" ? x.destination : x.sender}
                <span className="sans muted"> {(names?.get(x.dir === "tx" ? x.destination : x.sender) ?? x.name) || ""}</span>
              </td>
              <td>
                {x.rorg} <span className="muted">{RORGS[x.rorg] ?? ""}</span>
              </td>
              <td>{x.eep || "—"}</td>
              <td>
                {x.data}
                {x.duplicate && <span className="sans muted"> ({t("tg.dup")})</span>}
              </td>
              <td className="sans small">{x.decoded ? Object.entries(x.decoded).map(([key, value]) =>
                <div key={key}>{label(key)} : {decodedValue(key, value)}</div>) : "—"}</td>
              <td>{x.dbm != null ? -Math.abs(x.dbm) : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
