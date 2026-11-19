// Remote Commissioning : page (liste des produits + journal) et panneau d'un produit
import { useState } from "react";
import { request, useNow, useStore } from "./api";
import { useConfirm } from "./Confirm";
import { formatValue, label, locale, option, t } from "./i18n";
import type { Device, Info, Recom } from "./types";

export function RecomPage({ onOpen }: { onOpen: (device: Device) => void }) {
  const { devices, recomLog, info } = useStore();
  if (info && info.recom_enabled === false) {
    return (
      <div className="card empty">
        <h2>{t("recom.disabled")}</h2>
        <p>{t("recom.disabledHint")}</p>
      </div>
    );
  }
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
  if (recom.secured) return <span className="badge valide">{t(`recom.mode.${recom.mode ?? "custom"}`)}</span>;
  if (recom.pending) return <span className="badge communaute">{t("recom.pending")}</span>;
  if (recom.mode === "none") return <span className="badge neutral">{t("recom.mode.none")}</span>;
  return <span className="badge neutral">{t("recom.locked")}</span>;
}

export type CodeMode = "auto" | "custom" | "none";

// Choix du code de sécurité (à l'appairage ou plus tard, dans la fenêtre qui suit la mise sous tension)
export function CodeChoice({ mode, code, onChange }: { mode: CodeMode; code: string; onChange: (mode: CodeMode, code: string) => void }) {
  return (
    <div className="stack">
      {(["auto", "custom", "none"] as CodeMode[]).map((m) => (
        <label key={m} className={`choice${mode === m ? " selected" : ""}`}>
          <input type="radio" name="recom-code-mode" checked={mode === m} onChange={() => onChange(m, code)} />
          <span>
            <span className="strong">{t(`recom.choice.${m}`)}</span>
            <span className="small muted block">{t(`recom.choice.${m}Hint`)}</span>
          </span>
        </label>
      ))}
      {mode === "custom" && (
        <input value={code} onChange={(e) => onChange(mode, e.target.value)} placeholder={t("recom.codeHint")} autoComplete="off" spellCheck={false} />
      )}
    </div>
  );
}

export const codeChoiceValid = (mode: CodeMode, code: string) =>
  mode !== "custom" || /^(11Z)?[0-9A-F]{8}$/i.test(code.trim().replace(/ /g, ""));

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
  const { recomLog, info } = useStore();
  const recom = device.recom!;
  const [busy, setBusy] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [mode, setMode] = useState<CodeMode>("auto");
  const [newCode, setNewCode] = useState("");
  const [linkId, setLinkId] = useState("");
  const [linkType, setLinkType] = useState(recom.link_types[0] ?? "rocker_a");
  const [dialog, confirm] = useConfirm();
  const now = useNow(15000);
  const sessionLeft = Math.max(0, Math.round(((recom.session_until ?? 0) * 1000 - now) / 60000));
  const run = async (action: string, data: Record<string, unknown> = {}) => {
    // Toute opération autre que le Ping peut renvoyer le code : confirmation hors session
    if (action !== "ping" && !(action === "assign" && data.mode === "none") && (["unlock", "code", "assign", "detect"].includes(action) || !sessionLeft)) {
      const ok = await confirm({ title: t("recom.confirmTitle"), text: t("recom.confirmText", { name: device.name }), ok: t("recom.confirmOk") });
      if (!ok) return false;
    }
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
  const isGatewayId = gatewayIdMatcher(info);
  return (
    <div className="stack">
      <section className="stack">
        <div className="row">
          <span className="strong">{t("recom.access")}</span>
          <span className="button-row">
            {sessionLeft > 0 && <span className="badge valide">{t("recom.session", { n: sessionLeft })}</span>}
            <Access recom={recom} />
          </span>
        </div>
        {!recom.has_code && recom.mode !== "none" ? (
          <div className="stack">
            <p className="small">{t("recom.assignIntro")}</p>
            <CodeChoice mode={mode} code={newCode} onChange={(m, c) => { setMode(m); setNewCode(c); }} />
            <div className="button-row">
              <button type="button" className="primary" disabled={!!busy || !codeChoiceValid(mode, newCode)} onClick={() => run("assign", { mode, code: newCode })}>
                {busy === "assign" ? t("loading") : t("recom.assign")}
              </button>
              <button type="button" className="secondary" disabled={!!busy} onClick={() => run("ping")}>
                {busy === "ping" ? t("loading") : t("recom.ping")}
              </button>
            </div>
          </div>
        ) : (
          <div className="button-row">
            {recom.has_code && (
              <button type="button" className="primary" disabled={!!busy} onClick={() => run("unlock")}>
                {busy === "unlock" ? t("loading") : recom.pending ? t("recom.retry") : t("recom.unlock")}
              </button>
            )}
            {recom.mode === "none" && (
              <button type="button" className="secondary" disabled={!!busy} onClick={() => run("assign", { mode: "auto" })}>
                {busy === "assign" ? t("loading") : t("recom.assignAuto")}
              </button>
            )}
            <button type="button" className="secondary" disabled={!!busy} onClick={() => run("ping")}>
              {busy === "ping" ? t("loading") : t("recom.ping")}
            </button>
          </div>
        )}
        {recom.mode === "none" && <p className="small muted">{t("recom.noneInfo")}</p>}
        <details className="small">
          <summary>{t("recom.known")}</summary>
          <div className="stack">
            <p className="muted">{t("recom.detectHint")}</p>
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
            <div>
              <button type="button" className="secondary" disabled={!!busy} onClick={() => run("detect", { code })}>
                {busy === "detect" ? t("loading") : t("recom.detect")}
              </button>
            </div>
            <p className="muted">{t("recom.reset")}</p>
          </div>
        </details>
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
                      {isGatewayId(l.id) && (
                        <span className="badge valide gw-badge" title={t("recom.gatewayLinkHint")}>
                          Gateway Control
                        </span>
                      )}
                    </td>
                    <td>
                      <code>{l.eep}</code>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="link danger-link"
                        disabled={!!busy}
                        onClick={() => window.confirm(t(isGatewayId(l.id) ? "recom.gatewayDeleteConfirm" : "recom.linkDeleteConfirm", { id: l.id })) && run("links/delete", { index: l.index })}
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
      {dialog}
    </div>
  );
}

/** Adresse d'émission de la clé : son Chip ID ou Base ID + 0…127 (clé actuelle ou clé reprise). */
function gatewayIdMatcher(info: Info | null | undefined): (id: string) => boolean {
  const ranges: number[] = [];
  for (const base of [info?.gateway?.base_id, info?.migration?.previous_base_id]) {
    if (base && /^[0-9A-F]{8}$/i.test(base)) ranges.push(parseInt(base, 16));
  }
  const chip = info?.gateway?.chip_id?.toUpperCase();
  return (id: string) => {
    const up = (id || "").toUpperCase();
    if (chip && up === chip) return true;
    const value = parseInt(up, 16);
    return !Number.isNaN(value) && ranges.some((b) => value >= b && value < b + 128);
  };
}
