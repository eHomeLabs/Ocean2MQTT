// Fenêtre de confirmation (remplace window.confirm, bloqué dans certains iframes)
import { useCallback, useRef, useState } from "react";
import { t } from "./i18n";

type Ask = { title: string; text: string; ok: string };

export function useConfirm(): [React.ReactNode, (ask: Ask) => Promise<boolean>] {
  const [ask, setAsk] = useState<Ask | null>(null);
  const resolver = useRef<(value: boolean) => void>();
  const confirm = useCallback(
    (a: Ask) =>
      new Promise<boolean>((resolve) => {
        resolver.current = resolve;
        setAsk(a);
      }),
    [],
  );
  const close = (value: boolean) => {
    resolver.current?.(value);
    setAsk(null);
  };
  const dialog = ask ? (
    <div className="dialog-backdrop confirm-backdrop" role="presentation" onClick={() => close(false)}>
      <div className="dialog" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title" onClick={(e) => e.stopPropagation()}>
        <h2 id="confirm-title">{ask.title}</h2>
        <p>{ask.text}</p>
        <div className="dialog-actions">
          <span className="spacer" />
          <button type="button" className="secondary" autoFocus onClick={() => close(false)}>
            {t("cancel")}
          </button>
          <button type="button" className="primary" onClick={() => close(true)}>
            {ask.ok}
          </button>
        </div>
      </div>
    </div>
  ) : null;
  return [dialog, confirm];
}
