import { useState } from "react";
import { request } from "./api";
import { t } from "./i18n";
import type { Device, Identity } from "./types";

export function GenericIdentity({ device }: { device: Device }) {
  const [identity, setIdentity] = useState<Identity>(device.identity ?? {});
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const field = (key: keyof Identity, value: string) => {
    setIdentity({ ...identity, [key]: value }); setSaved(false);
  };
  return <form className="card stack" onSubmit={async (event) => {
    event.preventDefault(); setBusy(true); setError("");
    try { await request("device/identify", { id: device.id, ...identity }); setSaved(true); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }}>
    <h3>{t("identity.title")}</h3>
    <p className="small muted">{t("identity.help")}</p>
    {(["brand", "model", "photo", "manual"] as const).map((key) =>
      <label className="field" key={key}>{t(`identity.${key}`)}
        <input type={key === "photo" || key === "manual" ? "url" : "text"} maxLength={500}
          required={key === "brand" || key === "model"} minLength={key === "brand" || key === "model" ? 2 : undefined}
          placeholder={key === "photo" || key === "manual" ? "https://…" : ""}
          value={identity[key] ?? ""} onChange={(e) => field(key, e.target.value)} />
      </label>)}
    <label className="field">{t("identity.pairing")}<textarea maxLength={2000} rows={3}
      value={identity.pairing ?? ""} onChange={(e) => field("pairing", e.target.value)} /></label>
    <button type="submit" disabled={busy}>{t("save")}</button>
    {saved && <p role="status">{t("identity.saved")}</p>}
    {error && <p role="alert" className="error">{error}</p>}
  </form>;
}
