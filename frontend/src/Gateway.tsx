// Réglages modifiables : Base ID de la clé (reprise d'une clé HS) et serveur MQTT
import { useEffect, useState } from "react";
import { request, useStore } from "./api";
import { useConfirm } from "./Confirm";
import { t } from "./i18n";

type BaseIdResult = { base_id: string; writes_left?: number | null; restored: string[] };

const validBaseId = (v: string) => {
  if (!/^[0-9a-f]{8}$/i.test(v)) return false;
  const n = parseInt(v, 16);
  return n >= 0xff800000 && n <= 0xffffff80 && (n & 0x7f) === 0;
};

// Écrit un Base ID dans la clé ; utilisé dans Réglages et dans le bandeau « nouvelle clé »
function useWriteBaseId(onError: (m: string) => void) {
  const [dialog, confirm] = useConfirm();
  const { info } = useStore();
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<BaseIdResult | null>(null);
  const write = async (value: string) => {
    const left = info?.gateway.base_id_writes_left;
    const ok = await confirm({
      title: t("base.confirmTitle", { base: value.toUpperCase() }),
      text: t("base.confirmText", { left: left ?? "?" }),
      ok: t("base.confirmOk"),
    });
    if (!ok) return false;
    setBusy(true);
    try {
      setDone(await request<BaseIdResult>("gateway/base_id", { base_id: value }));
      return true;
    } catch (e) {
      onError((e as Error).message);
      return false;
    } finally {
      setBusy(false);
    }
  };
  return { dialog, write, busy, done };
}

export function BaseIdSection({ onError }: { onError: (m: string) => void }) {
  const { info } = useStore();
  const gw = info?.gateway;
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");
  const { dialog, write, busy, done } = useWriteBaseId(onError);
  const previous = info?.migration?.previous_base_id;
  if (!gw?.connected) return null;
  return (
    <div className="stack">
      {gw.base_id_writes_left != null && <p className="small muted">{t("base.left", { n: gw.base_id_writes_left })}</p>}
      {done && <p className="small">{t(done.restored.length ? "base.done" : "base.doneNone", { base: done.base_id, n: done.restored.length })}</p>}
      {!open ? (
        <div>
          <button type="button" className="secondary" onClick={() => { setOpen(true); setValue(previous ?? ""); }}>
            {t("base.change")}
          </button>
        </div>
      ) : (
        <div className="stack">
          <p className="small">{t("base.explain")}</p>
          <form
            className="number-form"
            onSubmit={async (e) => {
              e.preventDefault();
              if (await write(value.trim())) setOpen(false);
            }}
          >
            <label className="field grow">
              {t("base.new")}
              <input value={value} onChange={(e) => setValue(e.target.value.trim())} placeholder="FF945B80" spellCheck={false} autoComplete="off" />
            </label>
            <button type="submit" className="primary" disabled={busy || !validBaseId(value)}>
              {busy ? t("loading") : t("base.write")}
            </button>
            <button type="button" className="secondary" onClick={() => setOpen(false)}>
              {t("cancel")}
            </button>
          </form>
          <p className="small muted">{t("base.rules")}</p>
        </div>
      )}
      {dialog}
    </div>
  );
}

// Bandeau « nouvelle clé » : reprendre l'ancien Base ID au lieu de tout réappairer
export function CloneBaseIdButton({ onError }: { onError: (m: string) => void }) {
  const { info } = useStore();
  const previous = info?.migration?.previous_base_id;
  const { dialog, write, busy } = useWriteBaseId(onError);
  if (!previous || !info?.gateway.connected || info.gateway.base_id_writes_left === 0) return null;
  return (
    <>
      <button type="button" className="primary" disabled={busy} onClick={() => write(previous)}>
        {busy ? t("loading") : t("base.clone", { base: previous })}
      </button>
      {dialog}
    </>
  );
}

type MqttSettings = {
  host: string;
  port: number;
  username?: string | null;
  has_password: boolean;
  base_topic: string;
  topic_name: "name" | "id";
  discovery: boolean;
  discovery_prefix: string;
  tls: boolean;
  auto: boolean;
  can_auto: boolean;
  connected: boolean;
};

export function MqttSection({ onError }: { onError: (m: string) => void }) {
  const { info } = useStore();
  const [settings, setSettings] = useState<MqttSettings | null>(null);
  const [form, setForm] = useState<Record<string, unknown>>({});
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const editable = info?.mqtt?.editable !== false;
  const load = () => request<MqttSettings>("config/mqtt").then(setSettings).catch(() => {});
  useEffect(() => {
    load();
  }, [info?.mqtt?.connected]);
  if (!settings) return null;
  const start = () => {
    setForm({ ...settings, password: "" });
    setMessage(null);
    setEditing(true);
  };
  const set = (key: string, value: unknown) => setForm((f) => ({ ...f, [key]: value }));
  const run = async (action: "test" | "set" | "auto") => {
    setBusy(action);
    setMessage(null);
    try {
      if (action === "test") {
        await request("config/mqtt/test", form);
        setMessage(t("mqtt.testOk"));
      } else {
        setSettings(await request<MqttSettings>("config/mqtt/set", action === "auto" ? { auto: true } : form));
        setEditing(false);
      }
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };
  const yes = (v: unknown) => (v ? t("app.yes") : t("app.no"));
  if (!editing) {
    return (
      <div className="stack">
        <dl className="facts">
          <div>
            <dt>{t("app.host")}</dt>
            <dd><code>{settings.host}:{settings.port}</code></dd>
          </div>
          <div>
            <dt>{t("app.baseTopic")}</dt>
            <dd><code>{settings.base_topic}</code></dd>
          </div>
          <div>
            <dt>{t("mqtt.user")}</dt>
            <dd>{settings.username || "—"}</dd>
          </div>
          <div>
            <dt>{t("mqtt.status")}</dt>
            <dd>
              <span className={`badge ${settings.connected ? "valide" : "error"}`}>{settings.connected ? t("mqtt.connected") : t("mqtt.disconnected")}</span>
            </dd>
          </div>
          <div>
            <dt>{t("app.discovery")}</dt>
            <dd>{yes(settings.discovery)}</dd>
          </div>
          <div>
            <dt>{t("mqtt.topicName")}</dt>
            <dd>{settings.topic_name === "id" ? t("mqtt.topicId") : t("mqtt.topicNameName")}</dd>
          </div>
        </dl>
        {settings.auto && <p className="small muted">{t("mqtt.auto")}</p>}
        {editable ? (
          <div>
            <button type="button" className="secondary" onClick={start}>
              {t("mqtt.edit")}
            </button>
          </div>
        ) : (
          <p className="small muted">{t("app.configHint")}</p>
        )}
      </div>
    );
  }
  return (
    <form
      className="stack"
      onSubmit={(e) => {
        e.preventDefault();
        run("set");
      }}
    >
      <div className="grid-2">
        <label className="field">
          {t("app.host")}
          <input value={String(form.host ?? "")} onChange={(e) => set("host", e.target.value)} required spellCheck={false} />
        </label>
        <label className="field">
          {t("mqtt.port")}
          <input type="number" min={1} max={65535} value={String(form.port ?? "")} onChange={(e) => set("port", e.target.value)} required />
        </label>
        <label className="field">
          {t("mqtt.user")}
          <input value={String(form.username ?? "")} onChange={(e) => set("username", e.target.value)} autoComplete="off" spellCheck={false} />
        </label>
        <label className="field">
          {t("mqtt.password")}
          <input type="password" value={String(form.password ?? "")} onChange={(e) => set("password", e.target.value)} placeholder={settings.has_password ? t("mqtt.passwordKeep") : ""} autoComplete="new-password" />
        </label>
        <label className="field">
          {t("app.baseTopic")}
          <input value={String(form.base_topic ?? "")} onChange={(e) => set("base_topic", e.target.value)} required spellCheck={false} />
        </label>
        <label className="field">
          {t("mqtt.topicName")}
          <select value={String(form.topic_name)} onChange={(e) => set("topic_name", e.target.value)}>
            <option value="name">{t("mqtt.topicNameName")}</option>
            <option value="id">{t("mqtt.topicId")}</option>
          </select>
        </label>
        <label className="field">
          {t("mqtt.prefix")}
          <input value={String(form.discovery_prefix ?? "")} onChange={(e) => set("discovery_prefix", e.target.value)} spellCheck={false} />
        </label>
      </div>
      <label className="check">
        <input type="checkbox" checked={!!form.discovery} onChange={(e) => set("discovery", e.target.checked)} /> {t("app.discovery")}
      </label>
      <label className="check">
        <input type="checkbox" checked={!!form.tls} onChange={(e) => set("tls", e.target.checked)} /> {t("mqtt.tls")}
      </label>
      <p className="small muted">{t("mqtt.topicWarning")}</p>
      {message && <p className="small">{message}</p>}
      <div className="button-row">
        <button type="submit" className="primary" disabled={!!busy}>
          {busy === "set" ? t("loading") : t("mqtt.save")}
        </button>
        <button type="button" className="secondary" disabled={!!busy} onClick={() => run("test")}>
          {busy === "test" ? t("loading") : t("mqtt.test")}
        </button>
        <button type="button" className="secondary" disabled={!!busy} onClick={() => setEditing(false)}>
          {t("cancel")}
        </button>
        {settings.can_auto && !settings.auto && (
          <button type="button" className="link" disabled={!!busy} onClick={() => run("auto")}>
            {t("mqtt.backAuto")}
          </button>
        )}
      </div>
    </form>
  );
}
