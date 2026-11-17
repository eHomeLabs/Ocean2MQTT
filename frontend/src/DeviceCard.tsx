// Carte d'un produit appairé : contrôles et mesures construits à partir des « exposes »
import { useState } from "react";
import { request, sendCommand, useNow } from "./api";
import { BINARY_TEXT, formatValue, label, option, signal, since } from "./labels";
import type { Device, DeviceState, Expose } from "./types";

type Props = {
  device: Device;
  state: DeviceState;
  available: boolean;
  action?: { event: string; at: number };
  onError: (message: string) => void;
};

export function DeviceCard({ device, state, available, action, onError }: Props) {
  const now = useNow(10000);
  const [editing, setEditing] = useState(false);
  const exposes = device.product.exposes;
  const controls = exposes.filter((e) => e.access === "rw");
  const measures = exposes.filter(
    (e) => e.access === "r" && !e.category && ["sensor", "binary_sensor", "enum"].includes(e.kind),
  );
  const event = exposes.find((e) => e.kind === "event");
  const run = (payload: Record<string, unknown>) => sendCommand(device, payload).catch((e: Error) => onError(e.message));
  const lastSeen = (state.last_seen as string | undefined) ?? device.last_seen;
  const image = device.product.image;

  return (
    <article className="card device">
      <header className="device-head">
        {image ? <img src={image} alt="" className="thumb" /> : <div className="thumb placeholder" aria-hidden="true" />}
        <div className="device-title">
          <h2>{device.name}</h2>
          <span className="muted small">
            {[device.room, `${device.product.brand} ${device.product.model}`, device.product.eep].filter(Boolean).join(" · ")}
          </span>
        </div>
        <span className={`status ${available ? "ok" : "warn"}`}>
          <span className="dot" />
          {available ? "Disponible" : "Sans nouvelles"}
        </span>
      </header>

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
          <span className="muted small">Dernière action</span>
          <strong>{action ? option(action.event) : "—"}</strong>
          {action && <span className="muted small">{new Date(action.at).toLocaleTimeString("fr-FR")}</span>}
        </div>
      )}

      {!available && !device.actuator && event && (
        <p className="hint">Un produit sans pile n'émet que quand on l'utilise : « sans nouvelles » est normal.</p>
      )}

      <footer className="device-foot">
        <span>
          {since(lastSeen, now)}
          {signal(state.rssi) && ` · ${signal(state.rssi)}`}
        </span>
        <span className="links">
          <button type="button" className="link" onClick={() => setEditing(true)}>
            Renommer
          </button>
        </span>
      </footer>

      {editing && <RenameDialog device={device} onClose={() => setEditing(false)} onError={onError} />}
    </article>
  );
}

function Control({ expose, state, run }: { expose: Expose; state: DeviceState; run: (p: Record<string, unknown>) => void }) {
  const value = state[expose.key];
  if (expose.kind === "switch" || expose.kind === "light") {
    const on = value === "ON";
    return (
      <div className="row">
        <span className="strong">{expose.kind === "light" ? label(expose.key) : "Marche / arrêt"}</span>
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
    return (
      <div className="field">
        <label className="small muted strong">
          Position : {pos === null ? "inconnue" : pos === 0 ? "fermé" : pos === 100 ? "ouvert" : `ouvert à ${pos} %`}
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
            Ouvrir
          </button>
          <button type="button" className="secondary" onClick={() => run({ state: "STOP" })}>
            Stop
          </button>
          <button type="button" className="secondary" onClick={() => run({ state: "CLOSE" })}>
            Fermer
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
          <button type="button" className="secondary" aria-label="Baisser" onClick={() => setTo(current - step)}>
            −
          </button>
          <strong>{formatValue(current, expose.unit)}</strong>
          <button type="button" className="secondary" aria-label="Monter" onClick={() => setTo(current + step)}>
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
    const [yes, no] = BINARY_TEXT[expose.key] ?? ["Oui", "Non"];
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

function RenameDialog({ device, onClose, onError }: { device: Device; onClose: () => void; onError: (m: string) => void }) {
  const [name, setName] = useState(device.name);
  const [room, setRoom] = useState(device.room ?? "");
  const save = async () => {
    try {
      await request("device/rename", { id: device.id, name, room });
      onClose();
    } catch (e) {
      onError((e as Error).message);
    }
  };
  const remove = async () => {
    if (!window.confirm(`Retirer « ${device.name} » d'Ocean2MQTT ?`)) return;
    try {
      await request("device/remove", { id: device.id });
      onClose();
    } catch (e) {
      onError((e as Error).message);
    }
  };
  return (
    <div className="dialog-backdrop" role="presentation" onClick={onClose}>
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby={`rn-${device.id}`} onClick={(e) => e.stopPropagation()}>
        <h3 id={`rn-${device.id}`}>Renommer le produit</h3>
        <label className="field">
          Nom
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label className="field">
          Pièce (facultatif)
          <input value={room} onChange={(e) => setRoom(e.target.value)} />
        </label>
        <p className="small muted">Identifiant EnOcean {device.id} · topic ocean2mqtt/{device.topic}</p>
        <div className="dialog-actions">
          <button type="button" className="danger" onClick={remove}>
            Retirer
          </button>
          <span className="spacer" />
          <button type="button" className="secondary" onClick={onClose}>
            Annuler
          </button>
          <button type="button" className="primary" onClick={save}>
            Enregistrer
          </button>
        </div>
      </div>
    </div>
  );
}
