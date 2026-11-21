import { ProductImage } from "./ProductImage";
// Fiche d'un produit appairé : Contrôle, Réglages, Remote Commissioning, Télégrammes, Informations
import { useEffect, useState } from "react";
import { request, useStore } from "./api";
import { useConfirm } from "./Confirm";
import { DeviceControls } from "./DeviceCard";
import { RecomPanel } from "./Recom";
import { label, option, productText, supportName, t } from "./i18n";
import { TelegramTable } from "./Telegrams";
import type { Device, Product, Setting } from "./types";

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
          <ProductImage product={device.product} />
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
  const [dialog, confirm] = useConfirm();
  const apply = async (key: string, value: unknown) => {
    const setting = device.settings.find((s) => s.key === key);
    if (setting?.group === "recom" && (device.recom?.session_until ?? 0) * 1000 <= Date.now()) {
      const ok = await confirm({ title: t("recom.confirmTitle"), text: t("recom.confirmText", { name: device.name }), ok: t("recom.confirmOk") });
      if (!ok) return;
    }
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
      {dialog}
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
  const [compatible, setCompatible] = useState<Product[] | null>(null);
  const [sheet, setSheet] = useState(device.product.id);
  const [sheetDone, setSheetDone] = useState(false);
  useEffect(() => {
    request<Product[]>("device/compatible", { id: device.id }).then(setCompatible).catch(() => setCompatible([]));
    setSheet(device.product.id);
  }, [device.id, device.product.id]);
  const changeSheet = async () => {
    try {
      await request("device/change_product", { id: device.id, product: sheet });
      setSheetDone(true);
      setTimeout(() => setSheetDone(false), 2500);
    } catch (e) {
      onError((e as Error).message);
    }
  };
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
      <h3>
        {t("detail.sheet")}
        {sheetDone && <span className="applied"> ✓ {t("detail.sheetDone")}</span>}
      </h3>
      {compatible && compatible.length === 0 ? (
        <p className="small muted">{t("detail.sheetNone")}</p>
      ) : (
        <>
          <p className="small muted">{t("detail.sheetHint", { eep: p.eep })}</p>
          <div className="number-form">
            <select className="grow" aria-label={t("detail.sheet")} value={sheet} onChange={(e) => setSheet(e.target.value)}>
              <option value={p.id}>
                {p.brand} {p.model} — {productText(p).name}
              </option>
              {(compatible ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.brand} {c.model} — {productText(c).name}
                </option>
              ))}
            </select>
            <button type="button" className="secondary" disabled={sheet === p.id} onClick={changeSheet}>
              {t("detail.sheetChange")}
            </button>
          </div>
        </>
      )}
      {(p.support === "communaute" || p.generic) && <ConfirmWorks device={device} />}
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

const REPO = "https://github.com/eHomeLabs/Ocean2MQTT";

/** Produit « Communauté » : retour de test prérempli sur GitHub (validé ensuite par le mainteneur). */
function ConfirmWorks({ device }: { device: Device }) {
  const { info, states, telegrams } = useStore();
  const p = device.product;
  const state = states[device.topic] ?? device.state;
  const recent = telegrams
    .filter((tg) => tg.sender === device.id && !tg.duplicate)
    .slice(-10)
    .map((tg) => `${new Date(tg.time * 1000).toISOString().slice(11, 19)} ${tg.dir} ${tg.rorg} ${tg.data} ${tg.status}${tg.dbm != null ? ` ${tg.dbm} dBm` : ""}`)
    .join("\n");
  const params = new URLSearchParams({
    template: "retour-test.yml",
    title: `[Retour de test] ${p.brand} ${p.model}`,
    fiche: p.id,
    version: info?.version ?? "",
    eep: [p.eep, ...p.extra_eeps].join(" + "),
    valeurs: JSON.stringify(state, null, 2).slice(0, 2000),
    telegrammes: recent || t("confirm.noTelegrams"),
  });
  return (
    <div className="confirm-works">
      <h3>{t("confirm.title")}</h3>
      <p className="small muted">{t(p.generic ? "confirm.genericText" : "confirm.text")}</p>
      <a className="button secondary" href={`${REPO}/issues/new?${params}`} target="_blank" rel="noreferrer">
        {t("confirm.button")}
      </a>
    </div>
  );
}
