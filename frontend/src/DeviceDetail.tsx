// Fiche d'un produit appairé : Contrôle, Réglages, Remote Commissioning, Télégrammes, Informations
import { useEffect, useState } from "react";
import { request, useStore } from "./api";
import { DeviceControls } from "./DeviceCard";
import { RecomPanel } from "./Recom";
import { label, option, supportName, t } from "./i18n";
import { TelegramTable } from "./Telegrams";
import type { Device, Setting } from "./types";

type Tab = "control" | "settings" | "recom" | "telegrams" | "info";

export function DeviceDetail({ device, initialTab = "control", onClose, onError }: { device: Device; initialTab?: Tab; onClose: () => void; onError: (m: string) => void }) {
  const [tab, setTab] = useState<Tab>(initialTab);
  const { states, actions, telegrams } = useStore();
  const state = states[device.topic] ?? device.state;
  const tabs: [Tab, string][] = [
    ["control", t("detail.control")],
    ...(device.settings.length ? [["settings", t("detail.settings")] as [Tab, string]] : []),
    ...(device.recom ? [["recom", t("detail.recom")] as [Tab, string]] : []),
    ["telegrams", t("detail.telegrams")],
    ["info", t("detail.info")],
  ];
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="dialog-backdrop" role="presentation" onClick={onClose}>
      <div className="dialog wide" role="dialog" aria-modal="true" aria-labelledby={`dd-${device.id}`} onClick={(e) => e.stopPropagation()}>
        <header className="detail-head">
          {device.product.image ? <img src={device.product.image} alt="" className="thumb" /> : <div className="thumb placeholder" aria-hidden="true" />}
          <div className="device-title">
            <h2 id={`dd-${device.id}`}>{device.name}</h2>
            <span className="muted small">
              {[device.room, `${device.product.brand} ${device.product.model}`, device.id].filter(Boolean).join(" · ")}
            </span>
          </div>
          <button type="button" className="secondary" onClick={onClose}>
            {t("close")}
          </button>
        </header>
        <div className="tabs" role="tablist">
          {tabs.map(([key, text]) => (
            <button key={key} type="button" role="tab" aria-selected={tab === key} className={tab === key ? "active" : ""} onClick={() => setTab(key)}>
              {text}
            </button>
          ))}
        </div>
        <div className="tab-body" role="tabpanel">
          {tab === "control" && <div className="device stack"><DeviceControls device={device} state={state} action={actions[device.topic]} onError={onError} /></div>}
          {tab === "settings" && <SettingsForm device={device} onError={onError} />}
          {tab === "recom" && <RecomPanel device={device} onError={onError} />}
          {tab === "telegrams" && <TelegramTable telegrams={telegrams.filter((x) => x.sender === device.id || x.destination === device.id)} />}
          {tab === "info" && <Info device={device} onClose={onClose} onError={onError} />}
        </div>
      </div>
    </div>
  );
}

function SettingsForm({ device, onError }: { device: Device; onError: (m: string) => void }) {
  const [done, setDone] = useState<string | null>(null);
  const apply = async (key: string, value: unknown) => {
    try {
      await request("device/settings/set", { id: device.id, key, value });
      setDone(key);
      setTimeout(() => setDone((k) => (k === key ? null : k)), 2500);
    } catch (e) {
      onError((e as Error).message);
    }
  };
  const groups: ["product" | "local" | "recom", string][] = [
    ["product", t("settings.product")],
    ["recom", t("settings.recom")],
    ["local", t("settings.local")],
  ];
  return (
    <div className="stack">
      {groups.map(([group, title]) => {
        const items = device.settings.filter((s) => (s.group ?? "product") === group);
        if (!items.length) return null;
        return (
          <section key={group} className="stack">
            <h3>{title}</h3>
            {group === "product" && <p className="small muted">{t("settings.notRead")}</p>}
            {items.map((s) => (
              <SettingRow key={s.key} setting={s} done={done === s.key} apply={apply} />
            ))}
          </section>
        );
      })}
    </div>
  );
}

function SettingRow({ setting, done, apply }: { setting: Setting; done: boolean; apply: (key: string, value: unknown) => void }) {
  const [text, setText] = useState(setting.value === undefined || setting.value === null ? "" : String(setting.value));
  const [choice, setChoice] = useState(setting.options?.[0] ?? "");
  useEffect(() => setText(setting.value === undefined || setting.value === null ? "" : String(setting.value)), [setting.value]);
  const name = label(setting.key);
  let input: React.ReactNode = null;
  if (setting.kind === "binary") {
    const on = setting.value === true;
    input = (
      <button type="button" role="switch" aria-checked={on} aria-label={name} className={`switch ${on ? "on" : ""}`} onClick={() => apply(setting.key, !on)}>
        <span />
      </button>
    );
  } else if (setting.kind === "enum") {
    input = (
      <select aria-label={name} value={setting.value === undefined || setting.value === null ? "" : String(setting.value)} onChange={(e) => apply(setting.key, e.target.value)}>
        {(setting.value === undefined || setting.value === null) && <option value="">{t("settings.unset")}</option>}
        {setting.options?.map((o) => (
          <option key={o} value={o}>
            {option(o)}
          </option>
        ))}
      </select>
    );
  } else if (setting.kind === "numeric") {
    input = (
      <form
        className="number-form"
        onSubmit={(e) => {
          e.preventDefault();
          if (text !== "") apply(setting.key, Number(text));
        }}
      >
        <input type="number" aria-label={name} min={setting.min} max={setting.max} step={setting.step} value={text} onChange={(e) => setText(e.target.value)} />
        {setting.unit && <span className="muted small">{setting.unit}</span>}
        <button type="submit" className="secondary">
          {t("save")}
        </button>
      </form>
    );
  } else {
    input = (
      <div className="number-form">
        {(setting.options?.length ?? 0) > 1 && (
          <select aria-label={name} value={choice} onChange={(e) => setChoice(e.target.value)}>
            {setting.options?.map((o) => (
              <option key={o} value={o}>
                {option(o)}
              </option>
            ))}
          </select>
        )}
        <button type="button" className="secondary" onClick={() => apply(setting.key, choice)}>
          {t("settings.run")}
        </button>
      </div>
    );
  }
  return (
    <div className="row setting">
      <span className="strong">
        {name}
        {done && <span className="applied"> ✓ {t("settings.applied")}</span>}
      </span>
      {input}
    </div>
  );
}

function Info({ device, onClose, onError }: { device: Device; onClose: () => void; onError: (m: string) => void }) {
  const [name, setName] = useState(device.name);
  const [room, setRoom] = useState(device.room ?? "");
  const save = () => request("device/rename", { id: device.id, name, room }).catch((e: Error) => onError(e.message));
  const remove = async () => {
    if (!window.confirm(t("detail.removeConfirm", { name: device.name }))) return;
    try {
      await request("device/remove", { id: device.id });
      onClose();
    } catch (e) {
      onError((e as Error).message);
    }
  };
  const p = device.product;
  return (
    <div className="stack">
      <dl className="facts">
        <div>
          <dt>{t("detail.id")}</dt>
          <dd><code>{device.id}</code></dd>
        </div>
        <div>
          <dt>{t("detail.topic")}</dt>
          <dd><code>ocean2mqtt/{device.topic}</code></dd>
        </div>
        <div>
          <dt>{t("detail.product")}</dt>
          <dd>{p.brand} {p.model}</dd>
        </div>
        <div>
          <dt>{t("detail.eep")}</dt>
          <dd><code>{[p.eep, ...p.extra_eeps].join(" + ")}</code></dd>
        </div>
        <div>
          <dt>{t("detail.support")}</dt>
          <dd><span className={`badge ${p.support}`}>{supportName(p.support)}</span></dd>
        </div>
        {p.manual && (
          <div>
            <dt>{t("detail.manual")}</dt>
            <dd><a href={p.manual} target="_blank" rel="noreferrer">{p.manual.replace(/^https:\/\//, "").slice(0, 32)}…</a></dd>
          </div>
        )}
      </dl>
      <h3>{t("detail.rename")}</h3>
      <label className="field">
        {t("detail.name")}
        <input value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      <label className="field">
        {t("detail.roomOpt")}
        <input value={room} onChange={(e) => setRoom(e.target.value)} />
      </label>
      <div className="dialog-actions">
        <button type="button" className="danger" onClick={remove}>
          {t("remove")}
        </button>
        <span className="spacer" />
        <button type="button" className="primary" onClick={save}>
          {t("save")}
        </button>
      </div>
    </div>
  );
}
