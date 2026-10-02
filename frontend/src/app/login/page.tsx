"use client";

import { ArrowLeft, ClipboardCheck, FlaskConical, LogIn, Shield, UserRound } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { PolarScene } from "@/components/art/PolarScene";
import { Logo } from "@/components/art/Logo";
import { useToast } from "@/components/common/Toast";
import { Button, Field, inputCls } from "@/components/common/ui";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import type { Role } from "@/lib/types";

const ICONS: Record<string, typeof UserRound> = { public: UserRound, researcher: FlaskConical, editor: ClipboardCheck, admin: Shield };

function Login() {
  const { login, demoLogin } = useAuth();
  const router = useRouter();
  const sp = useSearchParams();
  const next = sp.get("next") || "/";
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState("");
  const demo = useApi<{ enabled: boolean; accounts: { role: Role; label: string; email: string; name: string; description: string }[] }>("/api/auth/demo-accounts");

  const done = (name: string, role: string) => {
    toast("success", `Welcome, ${name}`, `Signed in as ${role}.`);
    router.push(next.startsWith("/") ? next : "/");
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden overflow-hidden bg-night lg:block">
        <PolarScene scene="station-night" seed="login" className="absolute inset-0 h-full w-full opacity-80" />
        <div className="absolute inset-0 bg-gradient-to-t from-night via-night/40 to-transparent" />
        <div className="relative flex h-full flex-col justify-between p-10 text-white">
          <Logo />
          <div>
            <h1 className="text-[40px] leading-tight">From Polar Research<br />to Public Understanding.</h1>
            <p className="mt-3 max-w-md text-frost/80">Researchers upload and create, editors review and approve, administrators manage the repository. Every role sees the tools it needs.</p>
          </div>
        </div>
      </div>
      <div className="flex items-center justify-center bg-snow px-5 py-10">
        <div className="w-full max-w-md">
          <Link href="/" className="mb-8 inline-flex items-center gap-1.5 text-[13px] text-steel hover:text-cyan-deep"><ArrowLeft className="h-3.5 w-3.5" /> Back to the portal</Link>
          <div className="mb-6 lg:hidden"><Logo dark={false} /></div>
          <h2 className="text-[28px] text-night">Sign in</h2>
          <p className="mt-1 text-[14px] text-ink-soft">Public visitors can explore without an account.</p>

          {demo.data?.enabled && (
            <div className="mt-6">
              <p className="mb-2 font-mono text-[11px] uppercase tracking-wider text-steel">One-click demo accounts</p>
              <div className="grid grid-cols-2 gap-2">
                {demo.data.accounts.map((a) => {
                  const I = ICONS[a.role] || UserRound;
                  return (
                    <button
                      key={a.role}
                      disabled={!!busy}
                      onClick={async () => {
                        setBusy(a.role);
                        setErr("");
                        try {
                          const u = await demoLogin(a.role);
                          done(u.name, u.role_label);
                        } catch (e) {
                          setErr((e as Error).message);
                        } finally {
                          setBusy(null);
                        }
                      }}
                      className="group rounded-xl border border-frost bg-white p-3 text-left shadow-card transition hover:border-cyan disabled:opacity-60"
                    >
                      <I className="mb-1.5 h-4.5 w-4.5 text-cyan-deep" />
                      <span className="block text-[14px] font-medium text-night">{a.label} Demo</span>
                      <span className="mt-0.5 line-clamp-2 block text-[12px] text-steel">{busy === a.role ? "Signing in…" : a.description}</span>
                    </button>
                  );
                })}
              </div>
              <div className="my-6 flex items-center gap-3 text-[12px] text-mist">
                <span className="h-px flex-1 bg-frost" /> or use email <span className="h-px flex-1 bg-frost" />
              </div>
            </div>
          )}

          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy("form");
              setErr("");
              try {
                const u = await login(email, password);
                done(u.name, u.role_label);
              } catch (e2) {
                setErr((e2 as Error).message);
              } finally {
                setBusy(null);
              }
            }}
            className="space-y-4"
          >
            <Field label="Email">
              <input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={inputCls} placeholder="you@institute.org" />
            </Field>
            <Field label="Password">
              <input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} className={inputCls} />
            </Field>
            {err && <p role="alert" className="rounded-lg bg-[#fbe9e5] px-3 py-2 text-[13px] text-coral">{err}</p>}
            <Button type="submit" className="w-full" size="lg" loading={busy === "form"} icon={<LogIn className="h-4 w-4" />}>Sign in</Button>
          </form>
          <p className="mt-6 text-[12px] leading-relaxed text-steel">
            Demo accounts use prototype data only. In production this would connect to institutional single sign-on — not implemented in this prototype.
          </p>
        </div>
      </div>
    </div>
  );
}

export default function Page() {
  return (
    <Suspense>
      <Login />
    </Suspense>
  );
}
