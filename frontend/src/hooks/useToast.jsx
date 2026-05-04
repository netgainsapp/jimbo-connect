import { createContext, useContext, useState, useCallback } from "react";
import { CheckCircle2, XCircle } from "lucide-react";

const ToastContext = createContext(null);

let counter = 0;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const remove = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const show = useCallback(
    (message, type = "success") => {
      const id = ++counter;
      setToasts((prev) => [...prev, { id, message, type }]);
      setTimeout(() => remove(id), 3000);
    },
    [remove]
  );

  return (
    <ToastContext.Provider value={{ show }}>
      {children}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className="flex items-center gap-2 bg-white border border-border-default shadow-card rounded-card px-4 py-3 text-sm text-text-primary min-w-[240px]"
          >
            {t.type === "error" ? (
              <XCircle className="w-4 h-4 text-red-500" />
            ) : (
              <CheckCircle2 className="w-4 h-4 text-primary" />
            )}
            <span>{t.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
