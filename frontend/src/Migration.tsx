// Reprise des produits de NodOcean for HA, import d'un fichier, sauvegarde et restauration
import { useEffect, useRef, useState } from "react";
import { request, useStore } from "./api";
import { t } from "./i18n";
import type { Key } from "./i18n";
import type { MigrationPlan } from "./types";

export type MigrationTarget = { kind: "ha"; index: number } | { kind: "file"; file: unknown; backup: boolean };
type Mode = "same" | "new" | "fresh";
type Step = "key" | "check" | "preview" | "done";

export function MigrationBanner({ onStart }: { onStart: (target: MigrationTarget) => void }) {
  const { info } = useStore();
  const sources = info?.migration?.nodocean ?? [];
  if (!sources.length || info?.migration?.dismissed) return null;
  const s = sources[0];
  return (
    <div className="card banner" role="region" aria-label={t("mig.bannerTitle")}>
      <div>
        <h3>{t("mig.bannerTitle")}</h3>
        <p className="small muted">{t("mig.bannerText", { n: s.devices, base: s.base_id ?? "?" })}</p>
      </div>
      <div className="button-row">
        <button type="button" className="primary" onClick={() => onStart({ kind: "ha", index: 0 })}>
          {t("mig.start")}
        </button>
        <button type="button" className="secondary" onClick={() => request("migration/dismiss")}>
          {t("mig.fresh")}
        </button>
      </div>
    </div>
  );
}

export function RepairBanner() {
  const { devices, info } = useStore();
  const count = devices.filter((d) => d.needs_pairing).length;
  if (!count) return null;
  return (
    <div className="card banner warn" role="status">
      <div>
        <h3>{t("repair.bannerTitle")}</h3>
        <p className="small muted">{t("repair.bannerText", { n: count, base: info?.migration?.previous_base_id ?? "?" })}</p>
      </div>
    </div>
  );
}

export function MigrationWizard({ target, onClose, onError }: { target: MigrationTarget; onClose: () => void; onError: (m: string) => void }) {
  const { info } = useStore();
  const backup = target.kind === "file" && target.backup;
  const [step, setStep] = useState<Step>(backup ? "preview" : "key");
  const [mode, setMode] = useState<Mode>("same");
  const [plan, setPlan] = useState<MigrationPlan | null>(null);
  const [result, setResult] = useState<{ imported: number; repair: number; codes?: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const params = () => (target.kind === "ha" ? { index: target.index } : { file: target.file });
  const haSource = target.kind === "ha" ? info?.migration?.nodocean[target.index] : undefined;
  const [active, setActive] = useState<boolean | null | undefined>(haSource?.active);
  const nodoceanActive = active === true;
  // Étape « désactiver NodOcean » : l'état est relu toutes les 3 s
  useEffect(() => {
    if (step !== "check" || target.kind !== "ha") return;
    const timer = window.setInterval(() => {
      request<{ active?: boolean | null }[]>("migration/sources")
        .then((list) => setActive(list[target.index]?.active))
        .catch(() => {});
    }, 3000);
    return () => window.clearInterval(timer);
  }, [step, target]);
  const stick = info?.gateway;

  useEffect(() => {
    if (step !== "preview") return;
    request<MigrationPlan>("migration/preview", { ...params(), mode: mode === "fresh" ? "new" : mode })
      .then(setPlan)
      .catch((e: Error) => {
        onError(e.message);
        onClose();
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, mode, stick?.base_id]);

  const next = async () => {
    if (mode === "fresh") {
      await request("migration/dismiss").catch(() => {});
      setStep("done");
      return;
    }
    setStep(mode === "same" ? "check" : "preview");
  };
  const run = async () => {
    setBusy(true);
    try {
      setResult(await request("migration/import", { ...params(), mode: mode === "fresh" ? "new" : mode }));
      setStep("done");
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const title = target.kind === "ha" ? t("mig.title") : backup ? t("mig.titleBackup") : t("mig.titleFile");
  const toImport = plan?.items.filter((i) => i.status === "ok" || i.status === "repair" || i.status === "code").length ?? 0;

  return (
    <div className="dialog-backdrop" role="presentation" onClick={onClose}>
      <div className="dialog wide" role="dialog" aria-modal="true" aria-labelledby="mig-title" onClick={(e) => e.stopPropagation()}>
        <div className="row-title">
          <h2 id="mig-title">{title}</h2>
          <button type="button" className="secondary" onClick={onClose}>
            {t("close")}
          </button>
        </div>

        {step === "key" && (
          <div className="stack">
            <p className="strong">{t("mig.chooseKey")}</p>
            {(
              [
                ["same", "mig.sameKey", "mig.sameKeyHint"],
                ["new", "mig.newKey", "mig.newKeyHint"],
                ...(target.kind === "ha" ? [["fresh", "mig.freshKey", "mig.freshKeyHint"]] : []),
              ] as [Mode, Key, Key][]
            ).map(([value, label, hint]) => (
              <label key={value} className={`choice ${mode === value ? "selected" : ""}`}>
                <input type="radio" name="mig-mode" checked={mode === value} onChange={() => setMode(value)} />
                <span>
                  <strong>{t(label)}</strong>
                  <span className="small muted">{t(hint)}</span>
                </span>
              </label>
            ))}
            <div className="dialog-actions">
              <span className="spacer" />
              <button type="button" className="primary" onClick={next}>
                {t("mig.next")}
              </button>
            </div>
          </div>
        )}

        {step === "check" && (
          <div className="stack">
            {target.kind === "ha" && nodoceanActive ? (
              <div className="callout warn">
                <h3>{t("mig.disableTitle")}</h3>
                <p>{t("mig.disableText")}</p>
              </div>
            ) : target.kind === "ha" ? (
              <p className="callout ok">✓ {t("mig.disabledOk")}</p>
            ) : (
              <div className="callout warn">
                <h3>{t("mig.disableTitle")}</h3>
                <p>{t("mig.disableText")}</p>
              </div>
            )}
            <p className={stick?.connected ? "strong" : "callout warn"}>
              {stick?.connected ? t("mig.keyStatus", { base: stick.base_id ?? "?" }) : t("mig.keyAbsent")}
            </p>
            <div className="dialog-actions">
              <button type="button" className="secondary" onClick={() => setStep("key")}>
                {t("mig.back")}
              </button>
              <span className="spacer" />
              <button type="button" className="primary" onClick={() => setStep("preview")}>
                {t("mig.next")}
              </button>
            </div>
          </div>
        )}

        {step === "preview" && (
          <div className="stack">
            {!plan ? (
              <p className="muted">{t("loading")}</p>
            ) : (
              <>
                {plan.key_mismatch && <p className="callout warn">{t("mig.mismatch", { current: plan.current_base_id ?? "?", source: plan.source.base_id ?? "?" })}</p>}
                <h3>{t("mig.preview")}</h3>
                <div className="table-card">
                  <table className="table">
                    <tbody>
                      {plan.items.map((i) => (
                        <tr key={i.id}>
                          <td className="strong">{i.name}</td>
                          <td className="muted small">{i.room ?? ""}</td>
                          <td className="small">
                            {i.brand} {i.model}
                          </td>
                          <td className="small">
                            <code>{i.id}</code>
                            {i.recom && <span className="muted"> · {t("mig.recom")}</span>}
                          </td>
                          <td>
                            <span className={`badge ${{ ok: "valide", repair: "communaute", exists: "neutral", unknown: "error", code: "valide" }[i.status]}`}>{t(`mig.st.${i.status}` as Key)}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="dialog-actions">
                  {!backup && (
                    <button type="button" className="secondary" onClick={() => setStep(mode === "same" ? "check" : "key")}>
                      {t("mig.back")}
                    </button>
                  )}
                  <span className="spacer" />
                  <button type="button" className="primary" disabled={busy || !toImport} onClick={run}>
                    {t("mig.import", { n: toImport })}
                  </button>
                </div>
              </>
            )}
          </div>
        )}

        {step === "done" && (
          <div className="stack">
            {result ? (
              <>
                <h3>✓ {t("mig.doneTitle")}</h3>
                <p>{t("mig.done", { n: result.imported, r: result.repair })}</p>
                {!!result.codes && <p>{t("mig.doneCodes", { n: result.codes })}</p>}
                {target.kind !== "file" || !backup ? <p className="callout">{t("mig.after")}</p> : null}
              </>
            ) : (
              <p>{t("mig.freshDone")}</p>
            )}
            <div className="dialog-actions">
              <span className="spacer" />
              <button type="button" className="primary" onClick={onClose}>
                {t("close")}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/** Section « Migration et sauvegarde » de la page Réglages. */
export function MigrationSettings({ onStart, onError }: { onStart: (target: MigrationTarget) => void; onError: (m: string) => void }) {
  const { info } = useStore();
  const sources = info?.migration?.nodocean ?? [];
  const exportInput = useRef<HTMLInputElement>(null);
  const backupInput = useRef<HTMLInputElement>(null);
  const readFile = async (input: HTMLInputElement | null, backup: boolean) => {
    const file = input?.files?.[0];
    if (!file) return;
    try {
      onStart({ kind: "file", file: JSON.parse(await file.text()), backup });
    } catch {
      onError(t("mig.badFile"));
    } finally {
      if (input) input.value = "";
    }
  };
  const download = async () => {
    try {
      const data = await request("backup/create");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `ocean2mqtt-sauvegarde-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) {
      onError((e as Error).message);
    }
  };
  return (
    <section className="card stack">
      <h3>{t("mig.section")}</h3>
      <div className="row setting">
        <span>
          <strong>{t("mig.fromHa")}</strong>
          {!sources.length && <span className="small muted block">{t("mig.fromHaNone")}</span>}
          {sources.map((s, i) => (
            <span key={i} className="small muted block">
              {s.title ?? s.base_id} · {t("add.count", { n: s.devices })}
            </span>
          ))}
        </span>
        <button type="button" className="secondary" disabled={!sources.length} onClick={() => onStart({ kind: "ha", index: 0 })}>
          {t("mig.start")}
        </button>
      </div>
      <div className="row setting">
        <span>
          <strong>{t("mig.fromFile")}</strong>
          <span className="small muted block">{t("mig.fromFileHint")}</span>
        </span>
        <button type="button" className="secondary" onClick={() => exportInput.current?.click()}>
          {t("mig.fromFile")}
        </button>
        <input ref={exportInput} type="file" accept=".json,application/json" hidden onChange={() => readFile(exportInput.current, false)} />
      </div>
      <div className="row setting">
        <span>
          <strong>{t("mig.backupTitle")}</strong>
          <span className="small muted block">{t("mig.backupHint")}</span>
        </span>
        <div className="button-row">
          <button type="button" className="secondary" onClick={download}>
            {t("mig.backup")}
          </button>
          <button type="button" className="secondary" onClick={() => backupInput.current?.click()}>
            {t("mig.restore")}
          </button>
        </div>
        <input ref={backupInput} type="file" accept=".json,application/json" hidden onChange={() => readFile(backupInput.current, true)} />
      </div>
    </section>
  );
}
