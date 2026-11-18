// Remote Commissioning : page (liste des produits + journal) et panneau d'un produit
import { useState } from "react";
import { request, useStore } from "./api";
import { formatValue, label, locale, option, t } from "./i18n";
import type { Device, Recom } from "./types";

export function RecomPage({ onOpen }: { onOpen: (device: Device) => void }) {
  const { devices, recomLog } = useStore();
  const items = devices.filter((d) => d.recom);
  return (
    <div className="stack">
      <p className="muted">{t("recom.intro")}</p>
      {items.length === 0 ? (
        <div className="card empty">
          <p>{t("recom.none")}</p>
        </div>
      ) : (
        <div className="card table-card">
          <table className="table">
            <thead>
              <tr>
                <th>{t("detail.name")}</th>
                <th>{t("detail.product")}</th>
                <th>{t("recom.access")}</th>
                <th>{t("recom.links")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {items.map((d) => (
                <tr key={d.id}>
                  <td className="strong">{d.name}</td>
                  <td>
                    {d.product.brand} {d.product.model}
                  </td>
                  <td>
                    <Access recom={d.recom!} />
                  </td>
                  <td>{d.recom?.links ? t("recom.linksCount", { n: d.recom.links.length, max: d.recom.links_max ?? "?" }) : "—"}</td>
                  <td>
                    <button type="button" className="link" onClick={() => onOpen(d)}>
                      {t("recom.open")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <section className="card stack">
        <h3>{t("recom.log")}</h3>
        <RecomLogTable entries={recomLog} />
      </section>
    </div>
  );
}

function Access({ recom }: { recom: Recom }) {
  if (recom.secured) return <span className="badge valide">{t("recom.secured")}</span>;
  if (recom.pending) return <span className="badge communaute">{t("recom.pending")}</span>;
  return <span className="badge neutral">{t("recom.locked")}</span>;
}

function RecomLogTable({ entries }: { entries: { time: string; name: string; action: string; ok: boolean; detail?: string | null }[] }) {
  if (!entries.length) return <p className="muted small">{t("recom.logEmpty")}</p>;
  return (
    <table className="table small">
      <tbody>
        {[...entries].reverse().map((e, i) => (
          <tr key={`${e.time}-${i}`}>
            <td className="muted">{new Date(e.time).toLocaleTimeString(locale())}</td>
            <td>{e.name}</td>
            <td>{option(e.action)}</td>
            <td>
              <span className={`badge ${e.ok ? "valide" : "error"}`}>{e.ok ? t("recom.ok") : t("recom.failed")}</span>
            </td>
            <td className="muted">{e.detail ? option(e.detail) : ""}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function RecomPanel({ device, onError }: { device: Device; onError: (m: string) => void }) {
  const { recomLog } = useStore();
  const recom = device.recom!;
  const [busy, setBusy] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [linkId, setLinkId] = useState("");
  const [linkType, setLinkType] = useState(recom.link_types[0] ?? "rocker_a");
  const run = async (action: string, data: Record<string, unknown> = {}) => {
    setBusy(action);
    try {
      await request(`device/recom/${action}`, { id: device.id, ...data });
      return true;
    } catch (e) {
      onError((e as Error).message);
      return false;
    } finally {
      setBusy(null);
    }
  };
  const isShutter = device.settings.some((s) => s.key === "rs_switch_type");
  const links = recom.links;
  return (
    <div className="stack">
      <section className="stack">
        <div className="row">
          <span className="strong">{t("recom.access")}</span>
          <Access recom={recom} />
        </div>
        <div className="button-row">
          <button type="button" className="primary" disabled={!!busy} onClick={() => run("unlock")}>
            {busy === "unlock" ? t("loading") : t("recom.unlock")}
          </button>
          <button type="button" className="secondary" disabled={!!busy} onClick={() => run("ping")}>
            {busy === "ping" ? t("loading") : t("recom.ping")}
          </button>
        </div>
        <form
          className="number-form"
          onSubmit={async (e) => {
            e.preventDefault();
            if (await run("code", { code })) setCode("");
          }}
        >
          <label className="field grow">
            {t("recom.code")}
            <input value={code} onChange={(e) => setCode(e.target.value)} placeholder={t("recom.codeHint")} autoComplete="off" spellCheck={false} />
          </label>
          <button type="submit" className="secondary" disabled={!!busy || !code.trim()}>
            {t("recom.useCode")}
          </button>
        </form>
        <p className="small muted">{t("recom.warning")}</p>
      </section>

      <section className="stack">
        <div className="row-title">
          <h3>{t("recom.links")}</h3>
          <button type="button" className="secondary" disabled={!!busy} onClick={() => run("links")}>
            {busy === "links" ? t("loading") : t("recom.linksRead")}
          </button>
        </div>
        {!links ? (
          <p className="muted small">{t("recom.linksUnknown")}</p>
        ) : links.length === 0 ? (
          <p className="muted small">{t("recom.linksEmpty")}</p>
        ) : (
          <>
            <p className="small muted">{t("recom.linksCount", { n: links.length, max: recom.links_max ?? "?" })}</p>
            <table className="table">
              <tbody>
                {links.map((l) => (
                  <tr key={l.index}>
                    <td className="muted">#{l.index}</td>
                    <td>
                      <code>{l.id}</code>
                    </td>
                    <td>
                      <code>{l.eep}</code>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="link danger-link"
                        disabled={!!busy}
                        onClick={() => window.confirm(t("recom.linkDeleteConfirm", { id: l.id })) && run("links/delete", { index: l.index })}
                      >
                        {t("recom.linkDelete")}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
        <form
          className="number-form wrap"
          onSubmit={async (e) => {
            e.preventDefault();
            if (await run("links/add", { link_id: linkId.trim(), type: linkType })) setLinkId("");
          }}
        >
          <label className="field grow">
            {t("recom.linkId")}
            <input value={linkId} onChange={(e) => setLinkId(e.target.value)} placeholder="FEDCBA98" spellCheck={false} />
          </label>
          <label className="field">
            {t("recom.linkType")}
            <select value={linkType} onChange={(e) => setLinkType(e.target.value)}>
              {recom.link_types.map((lt) => (
                <option key={lt} value={lt}>
                  {option(lt)}
                </option>
              ))}
            </select>
          </label>
          <button type="submit" className="secondary" disabled={!!busy || linkId.trim().length !== 8}>
            {t("recom.linkAddBtn")}
          </button>
        </form>
      </section>

      {isShutter && (
        <section className="stack">
          <div className="row-title">
            <h3>{t("recom.config")}</h3>
            <button type="button" className="secondary" disabled={!!busy} onClick={() => run("config")}>
              {busy === "config" ? t("loading") : t("recom.configRead")}
            </button>
          </div>
          {Object.keys(recom.config).length > 0 && (
            <dl className="facts">
              {Object.entries(recom.config).map(([k, v]) => (
                <div key={k}>
                  <dt>{label(k)}</dt>
                  <dd>{typeof v === "number" ? formatValue(v, "s") : option(String(v))}</dd>
                </div>
              ))}
            </dl>
          )}
        </section>
      )}

      <section className="stack">
        <h3>{t("recom.log")}</h3>
        <RecomLogTable entries={recomLog.filter((e) => e.id === device.id)} />
      </section>
    </div>
  );
}
