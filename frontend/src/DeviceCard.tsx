import { ProductImage } from "./ProductImage";
// Carte d'un produit appairé : contrôles et mesures construits à partir des « exposes »
import { sendCommand, useNow } from "./api";
import { binaryText, formatValue, label, locale, option, signal, since, t } from "./i18n";
import type { Device, DeviceState, Expose } from "./types";

type Props = {
  device: Device;
  state: DeviceState;
  available: boolean;
  action?: { event: string; at: number };
  onError: (message: string) => void;
  onOpen: () => void;
  onRepair?: () => void;
};

export function DeviceCard({ device, state, available, action, onError, onOpen, onRepair }: Props) {
  const now = useNow(10000);
  const lastSeen = (state.last_seen as string | undefined) ?? device.last_seen;
  const event = device.product.exposes.find((e) => e.kind === "event");

  return (
    <article className="card device">
      <header className="device-head">
        <ProductImage product={device.product} />
        <div className="device-title">
          <h2>
            <button type="button" className="title-link" onClick={onOpen}>
              {device.name}
            </button>
          </h2>
          <span className="muted small">
            {[device.room, `${device.product.brand} ${device.product.model}`, device.product.eep].filter(Boolean).join(" · ")}
          </span>
        </div>
        {device.needs_pairing ? (
          <span className="badge communaute">{t("repair.badge")}</span>
        ) : (
          <span className={`status ${available ? "ok" : "warn"}`}>
            <span className="dot" />
            {available ? t("card.available") : t("card.silent")}
          </span>
        )}
      </header>

      {device.needs_pairing && (
        <div className="callout warn row-title">
          <span className="small">{t("repair.cardHint")}</span>
          <button type="button" className="primary" onClick={onRepair}>
            {t("repair.button")}
          </button>
        </div>
      )}

      <DeviceControls device={device} state={state} action={action} onError={onError} />

      {!available && !device.actuator && event && <p className="hint">{t("card.silentHint")}</p>}

      <footer className="device-foot">
        <span>
          {since(lastSeen, now)}
          {signal(state.rssi) && ` · ${signal(state.rssi)}`}
        </span>
        <button type="button" className="link" onClick={onOpen}>
          {t("card.details")}
        </button>
      </footer>
    </article>
  );
}

/** Contrôles, mesures et dernière action (carte et onglet Contrôle de la fiche). */
export function DeviceControls({ device, state, action, onError }: { device: Device; state: DeviceState; action?: { event: string; at: number }; onError: (m: string) => void }) {
  const exposes = device.product.exposes;
  const controls = exposes.filter((e) => e.access === "rw");
  const measures = exposes.filter((e) => e.access === "r" && !e.category && ["sensor", "binary_sensor", "enum"].includes(e.kind));
  const event = exposes.find((e) => e.kind === "event");
  const run = (payload: Record<string, unknown>) => sendCommand(device, payload).catch((e: Error) => onError(e.message));
  return (
    <>
      {controls.map((e) => (
        <Control key={e.key} expose={e} state={state} run={run} />
      ))}
      {measures.length > 0 && (
        <div className="measures">
          {measures.map((e) => (
            <Measure key={e.key} expose={e} value={state[e.key]} />
          ))}
        </div>
      )}
      {event && (
        <div className="last-action">
          <span className="muted small">{t("card.lastAction")}</span>
          <strong>{action ? option(action.event) : "—"}</strong>
          {action && <span className="muted small">{new Date(action.at).toLocaleTimeString(locale())}</span>}
        </div>
      )}
    </>
  );
}

function Control({ expose, state, run }: { expose: Expose; state: DeviceState; run: (p: Record<string, unknown>) => void }) {
  const value = state[expose.key];
  if (expose.kind === "switch" || expose.kind === "light") {
    const on = value === "ON";
    return (
      <div className="row">
        <span className="strong">{expose.kind === "light" ? label(expose.key) : t("card.onOff")}</span>
        <button
          type="button"
          role="switch"
          aria-checked={on}
          aria-label={label(expose.key)}
          className={`switch ${on ? "on" : ""}`}
          onClick={() => run({ [expose.key]: on ? "OFF" : "ON" })}
        >
          <span />
        </button>
      </div>
    );
  }
  if (expose.kind === "select") {
    return (
      <div className="field">
        <span className="small muted strong">{label(expose.key)}</span>
        <div className="segmented" role="group" aria-label={label(expose.key)}>
          {expose.options?.map((o) => (
            <button key={o} type="button" aria-pressed={value === o} className={value === o ? "active" : ""} onClick={() => run({ [expose.key]: o })}>
              {option(o)}
            </button>
          ))}
        </div>
      </div>
    );
  }
  if (expose.kind === "cover") {
    const pos = typeof state.position === "number" ? state.position : null;
    const text = pos === null ? t("card.posUnknown") : pos === 0 ? t("card.posClosed") : pos === 100 ? t("card.posOpen") : t("card.posPct", { n: pos });
    return (
      <div className="field">
        <label className="small muted strong">
          {t("card.position", { p: text })}
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            defaultValue={pos ?? 0}
            key={pos ?? -1}
            onChange={(e) => run({ position: Number((e.target as HTMLInputElement).value) })}
          />
        </label>
        <div className="buttons3">
          <button type="button" className="secondary" onClick={() => run({ state: "OPEN" })}>
            {t("card.open")}
          </button>
          <button type="button" className="secondary" onClick={() => run({ state: "STOP" })}>
            {t("card.stop")}
          </button>
          <button type="button" className="secondary" onClick={() => run({ state: "CLOSE" })}>
            {t("card.close")}
          </button>
        </div>
      </div>
    );
  }
  if (expose.kind === "number") {
    const current = typeof value === "number" ? value : expose.min ?? 0;
    const step = expose.step ?? 1;
    const setTo = (v: number) => run({ [expose.key]: Math.max(expose.min ?? v, Math.min(expose.max ?? v, v)) });
    return (
      <div className="row">
        <span className="strong">{label(expose.key)}</span>
        <div className="stepper">
          <button type="button" className="secondary" aria-label={t("card.down")} onClick={() => setTo(current - step)}>
            −
          </button>
          <strong>{formatValue(current, expose.unit)}</strong>
          <button type="button" className="secondary" aria-label={t("card.up")} onClick={() => setTo(current + step)}>
            +
          </button>
        </div>
      </div>
    );
  }
  return null;
}

function Measure({ expose, value }: { expose: Expose; value: unknown }) {
  let text: string;
  if (expose.kind === "binary_sensor") {
    const [yes, no] = binaryText(expose.key);
    text = value === undefined ? "—" : value ? yes : no;
  } else if (expose.kind === "enum") {
    text = value === undefined ? "—" : option(String(value));
  } else {
    text = formatValue(value, expose.unit);
  }
  return (
    <div className="measure">
      <span className="small muted">{label(expose.key)}</span>
      <span className="value">{text}</span>
    </div>
  );
}
