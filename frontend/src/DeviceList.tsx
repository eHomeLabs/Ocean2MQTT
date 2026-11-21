import { ProductImage } from "./ProductImage";
// Vue « Liste » de Mes produits, façon Zigbee2MQTT : colonnes au choix, tri, recherche
import { useMemo, useState } from "react";
import { request, useNow } from "./api";
import { formatValue, label, since, supportName, t, typeName, type Key } from "./i18n";
import type { Device, DeviceState } from "./types";

export type ColumnKey =
  | "name" | "id" | "topic" | "model" | "type" | "eep" | "values"
  | "signal" | "seen" | "availability" | "battery" | "support" | "actions";

const COLUMNS: ColumnKey[] = [
  "name", "id", "topic", "model", "type", "eep", "values",
  "signal", "seen", "availability", "battery", "support", "actions",
];
const DEFAULT_COLUMNS: ColumnKey[] = [
  "name", "id", "model", "eep", "values", "signal", "seen", "availability", "battery", "actions",
];
const STORAGE = "o2m-list-columns";

function loadColumns(): ColumnKey[] {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE) ?? "null");
    if (Array.isArray(saved)) return COLUMNS.filter((c) => saved.includes(c));
  } catch {
    /* stockage indisponible : colonnes par défaut */
  }
  return DEFAULT_COLUMNS;
}

function saveColumns(cols: ColumnKey[]) {
  try {
    localStorage.setItem(STORAGE, JSON.stringify(cols));
  } catch {
    /* pas grave */
  }
}

type Props = {
  devices: Device[];
  states: Record<string, DeviceState>;
  availability: Record<string, boolean>;
  onOpen: (d: Device, tab?: "control" | "recom") => void;
  onError: (m: string) => void;
};

type Row = {
  device: Device;
  state: DeviceState;
  available: boolean;
  seen: string | null | undefined;
  rssi: number | null;
};

const BATTERY_KEYS = ["battery", "voltage"];
const HIDDEN_VALUES = new Set(["rssi", "action", ...BATTERY_KEYS]);

/** Principales valeurs du produit (mesures et états), comme sur la carte. */
function values(row: Row): string {
  const parts: string[] = [];
  for (const e of row.device.product.exposes) {
    if (HIDDEN_VALUES.has(e.key) || e.category === "diagnostic" || e.kind === "event") continue;
    const v = row.state[e.key];
    if (v === undefined || v === null) continue;
    if (typeof v === "boolean") parts.push(`${label(e.key)} ${v ? "✓" : "—"}`);
    else parts.push(formatValue(v, e.unit));
    if (parts.length >= 3) break;
  }
  return parts.join(" · ") || "—";
}

function battery(row: Row): string {
  const b = row.state.battery;
  if (typeof b === "number") return `${Math.round(b)} %`;
  const v = row.state.voltage;
  if (typeof v === "number") return formatValue(v, "V");
  return row.device.actuator ? t("list.mains") : "—";
}

function Bars({ rssi }: { rssi: number | null }) {
  if (rssi === null) return <span className="muted">—</span>;
  const dbm = rssi > 0 ? -rssi : rssi;
  const level = dbm >= -60 ? 4 : dbm >= -70 ? 3 : dbm >= -80 ? 2 : 1;
  return (
    <span className="signal-bars" title={`${dbm} dBm`}>
      {[1, 2, 3, 4].map((i) => (
        <i key={i} className={i <= level ? "on" : ""} style={{ height: 3 + i * 3 }} />
      ))}
      <span>{dbm} dBm</span>
    </span>
  );
}

export function DeviceList({ devices, states, availability, onOpen, onError }: Props) {
  const now = useNow(10000);
  const [columns, setColumns] = useState<ColumnKey[]>(loadColumns);
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<{ key: ColumnKey; desc: boolean }>({ key: "name", desc: false });

  const rows: Row[] = useMemo(
    () =>
      devices.map((device) => {
        const state = states[device.topic] ?? device.state;
        const rssi = typeof state.rssi === "number" ? state.rssi : null;
        return {
          device,
          state,
          available: availability[device.topic] ?? device.available,
          seen: (state.last_seen as string | undefined) ?? device.last_seen,
          rssi,
        };
      }),
    [devices, states, availability],
  );

  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  const filtered = rows.filter((r) => {
    const p = r.device.product;
    const text = [r.device.name, r.device.room, r.device.id, r.device.topic, p.brand, p.model, p.eep, ...p.variants]
      .join(" ")
      .toLowerCase();
    return words.every((w) => text.includes(w));
  });

  const sortValue = (r: Row): string | number => {
    switch (sort.key) {
      case "id": return r.device.id;
      case "topic": return r.device.topic;
      case "model": return `${r.device.product.brand} ${r.device.product.model}`.toLowerCase();
      case "type": return typeName(r.device.product.type);
      case "eep": return r.device.product.eep;
      case "signal": return r.rssi === null ? -999 : -Math.abs(r.rssi);
      case "seen": return r.seen ? Date.parse(r.seen) : 0;
      case "availability": return r.available ? 1 : 0;
      case "battery": return typeof r.state.battery === "number" ? r.state.battery : typeof r.state.voltage === "number" ? r.state.voltage : -1;
      case "support": return r.device.product.support;
      default: return `${r.device.room ?? ""} ${r.device.name}`.toLowerCase();
    }
  };
  const sorted = [...filtered].sort((a, b) => {
    const va = sortValue(a);
    const vb = sortValue(b);
    const cmp = typeof va === "number" && typeof vb === "number" ? va - vb : String(va).localeCompare(String(vb));
    return sort.desc ? -cmp : cmp;
  });

  const toggleColumn = (c: ColumnKey) => {
    const next = columns.includes(c) ? columns.filter((x) => x !== c) : COLUMNS.filter((x) => x === c || columns.includes(x));
    setColumns(next);
    saveColumns(next);
  };
  const sortBy = (key: ColumnKey) =>
    setSort((s) => (s.key === key ? { key, desc: !s.desc } : { key, desc: key === "seen" || key === "signal" }));

  const remove = async (d: Device) => {
    if (!window.confirm(t("detail.removeConfirm", { name: d.name }))) return;
    try {
      await request("device/remove", { id: d.id });
    } catch (e) {
      onError((e as Error).message);
    }
  };

  const show = (c: ColumnKey) => columns.includes(c);
  const head = (c: ColumnKey) =>
    show(c) && (
      <th key={c} aria-sort={sort.key === c ? (sort.desc ? "descending" : "ascending") : undefined}>
        {c === "actions" ? (
          t("list.col.actions")
        ) : (
          <button type="button" className="th-sort" onClick={() => sortBy(c)}>
            {t(`list.col.${c}` as Key)}
            {sort.key === c && <span aria-hidden="true">{sort.desc ? " ↓" : " ↑"}</span>}
          </button>
        )}
      </th>
    );

  return (
    <div className="stack">
      <div className="list-tools">
        <input
          type="search"
          className="list-search"
          placeholder={t("list.search")}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label={t("list.search")}
        />
        <span className="muted small">{t("list.count", { n: sorted.length, total: rows.length })}</span>
      </div>
      <div className="list-columns small">
        <span className="muted">{t("list.columns")}</span>
        {COLUMNS.filter((c) => c !== "name").map((c) => (
          <label key={c} className="check">
            <input type="checkbox" checked={show(c)} onChange={() => toggleColumn(c)} />
            {t(`list.col.${c}` as Key)}
          </label>
        ))}
      </div>
      <div className="card table-card">
        <table className="table device-list">
          <thead>
            <tr>
              <th aria-sort={sort.key === "name" ? (sort.desc ? "descending" : "ascending") : undefined}>
                <button type="button" className="th-sort" onClick={() => sortBy("name")}>
                  {t("list.col.name")}
                  {sort.key === "name" && <span aria-hidden="true">{sort.desc ? " ↓" : " ↑"}</span>}
                </button>
              </th>
              {COLUMNS.filter((c) => c !== "name").map(head)}
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => {
              const d = r.device;
              const p = d.product;
              return (
                <tr key={d.id} className={r.available ? "" : "off"}>
                  <td>
                    <div className="list-name">
                      <ProductImage product={{ ...p, image: d.identity?.photo || p.image }} className="list-thumb" />
                      <div>
                        <button type="button" className="title-link" onClick={() => onOpen(d)}>
                          {d.name}
                        </button>
                        {d.room && <div className="muted small">{d.room}</div>}
                      </div>
                    </div>
                  </td>
                  {show("id") && <td><code>{d.id}</code></td>}
                  {show("topic") && <td><code className="small">{d.topic}</code></td>}
                  {show("model") && (
                    <td>
                      <div>{p.model}</div>
                      <span className="brand-chip">{p.brand}</span>
                    </td>
                  )}
                  {show("type") && <td>{typeName(p.type)}</td>}
                  {show("eep") && <td><code>{p.eep}</code></td>}
                  {show("values") && <td className="small">{values(r)}</td>}
                  {show("signal") && <td><Bars rssi={r.rssi} /></td>}
                  {show("seen") && <td className="nowrap small">{since(r.seen, now).replace(/^(vu|seen) /, "")}</td>}
                  {show("availability") && (
                    <td>
                      {d.needs_pairing ? (
                        <span className="badge communaute">{t("repair.badge")}</span>
                      ) : (
                        <span className={`status ${r.available ? "ok" : "warn"}`}>
                          <span className="dot" />
                          {r.available ? t("card.available") : t("card.silent")}
                        </span>
                      )}
                    </td>
                  )}
                  {show("battery") && <td className="nowrap">{battery(r)}</td>}
                  {show("support") && <td><span className={`badge ${p.support}`}>{supportName(p.support)}</span></td>}
                  {show("actions") && (
                    <td>
                      <div className="list-actions">
                        <button type="button" className="icon-btn" title={t("card.details")} aria-label={`${t("card.details")} : ${d.name}`} onClick={() => onOpen(d)}>
                          ✎
                        </button>
                        {d.recom && (
                          <button type="button" className="icon-btn" title="Remote Commissioning" aria-label={`Remote Commissioning : ${d.name}`} onClick={() => onOpen(d, "recom")}>
                            ⚙
                          </button>
                        )}
                        <button type="button" className="icon-btn remove" title={t("remove")} aria-label={`${t("remove")} : ${d.name}`} onClick={() => remove(d)}>
                          🗑
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              );
            })}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={columns.length + 1} className="muted">{t("list.none")}</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
