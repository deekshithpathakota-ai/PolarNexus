"use client";

import { CircleCheck, CircleX, Info, TriangleAlert, X } from "lucide-react";
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import clsx from "clsx";

type Kind = "success" | "error" | "info" | "warning";
interface Toast {
  id: number;
  kind: Kind;
  title: string;
  body?: string;
}

const ToastCtx = createContext<(kind: Kind, title: string, body?: string) => void>(() => {});

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((kind: Kind, title: string, body?: string) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t.slice(-3), { id, kind, title, body }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), kind === "error" ? 7000 : 4500);
  }, []);
  const Icon = { success: CircleCheck, error: CircleX, info: Info, warning: TriangleAlert };
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-20 z-[100] flex flex-col items-center gap-2 px-4 lg:bottom-6 lg:items-end lg:pr-6">
        {toasts.map((t) => {
          const I = Icon[t.kind];
          return (
            <div
              key={t.id}
              role="status"
              className="pointer-events-auto flex w-full max-w-sm animate-fade-up items-start gap-3 rounded-xl border border-frost bg-white p-3.5 shadow-lift"
            >
              <I
                className={clsx("mt-0.5 h-5 w-5 shrink-0", {
                  "text-teal": t.kind === "success",
                  "text-coral": t.kind === "error",
                  "text-cyan": t.kind === "info",
                  "text-amber": t.kind === "warning",
                })}
              />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-night">{t.title}</p>
                {t.body && <p className="mt-0.5 text-sm text-ink-soft">{t.body}</p>}
              </div>
              <button aria-label="Dismiss" onClick={() => setToasts((x) => x.filter((y) => y.id !== t.id))} className="text-mist hover:text-night">
                <X className="h-4 w-4" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastCtx.Provider>
  );
}

export const useToast = () => useContext(ToastCtx);
