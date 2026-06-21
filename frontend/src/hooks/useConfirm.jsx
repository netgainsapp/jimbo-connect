import { createContext, useContext, useState, useCallback, useRef } from "react";
import Modal from "../components/Modal.jsx";

const ConfirmContext = createContext(null);

/**
 * App-styled replacement for window.confirm(). Returns a promise that resolves
 * true if the user confirms and false if they cancel / dismiss.
 *
 *   const confirm = useConfirm();
 *   if (!(await confirm({ title, body, destructive: true }))) return;
 */
export function ConfirmProvider({ children }) {
  const [state, setState] = useState(null);
  const resolverRef = useRef(null);

  const settle = useCallback((result) => {
    setState(null);
    const resolve = resolverRef.current;
    resolverRef.current = null;
    if (resolve) resolve(result);
  }, []);

  const confirm = useCallback((opts = {}) => {
    // If a dialog is already open, resolve it as cancelled before opening anew.
    if (resolverRef.current) settle(false);
    return new Promise((resolve) => {
      resolverRef.current = resolve;
      setState({
        title: opts.title || "Are you sure?",
        body: opts.body || "",
        confirmLabel: opts.confirmLabel || "Confirm",
        cancelLabel: opts.cancelLabel || "Cancel",
        destructive: Boolean(opts.destructive),
      });
    });
  }, [settle]);

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      <Modal open={Boolean(state)} onClose={() => settle(false)} maxWidth="max-w-md">
        {state && (
          <div className="p-6" role="alertdialog" aria-modal="true" aria-label={state.title}>
            <h2 className="text-lg font-bold text-text-primary">{state.title}</h2>
            {state.body && (
              <p className="text-sm text-text-secondary mt-2 whitespace-pre-wrap">
                {state.body}
              </p>
            )}
            <div className="flex justify-end gap-2 mt-6">
              <button type="button" className="btn-ghost" onClick={() => settle(false)}>
                {state.cancelLabel}
              </button>
              <button
                type="button"
                className={state.destructive ? "btn-danger" : "btn-primary"}
                onClick={() => settle(true)}
                autoFocus={!state.destructive}
              >
                {state.confirmLabel}
              </button>
            </div>
          </div>
        )}
      </Modal>
    </ConfirmContext.Provider>
  );
}

export function useConfirm() {
  const ctx = useContext(ConfirmContext);
  if (!ctx) throw new Error("useConfirm must be used within ConfirmProvider");
  return ctx;
}
