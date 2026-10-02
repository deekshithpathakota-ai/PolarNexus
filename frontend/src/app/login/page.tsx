"use client";

import { ArrowLeft, ClipboardCheck, FlaskConical, LogIn, Shield, UserRound } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { PolarBackdrop } from "@/components/auth/PolarBackdrop";
import { LogoMark } from "@/components/art/Logo";
import { PolarLoader } from "@/components/common/PolarLoader";
import { useToast } from "@/components/common/Toast";
import { useAuth } from "@/lib/auth";
import { BRAND } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Role } from "@/lib/types";

const ICONS: Record<string, typeof UserRound> = { public: UserRound, researcher: FlaskConical, editor: ClipboardCheck, admin: Shield };
const STAGES = ["Discover", "Understand", "Verify", "Create", "Review", "Disseminate", "Measure"];

function Login() {
  // Authentication logic is unchanged from v2: same context calls, same errors, same redirect.
  const { login, demoLogin } = useAuth();
  const router = useRouter();
  const sp = useSearchParams();
  const next = sp.get("next") || "/";
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [entering, setEntering] = useState(false);
  const [err, setErr] = useState("");
  const demo = useApi<{ enabled: boolean; accounts: { role: Role; label: string; email: string; name: string; description: string }[] }>("/api/auth/demo-accounts");

  const done = (name: string, role: string) => {
    toast("success", `Welcome, ${name}`, `Signed in as ${role}.`);
    setEntering(true);
    router.push(next.startsWith("/") ? next : "/");
  };

  return (
    <div className="relative min-h-[100dvh] overflow-hidden bg-abyss text-white">
      <PolarBackdrop />

      <div className="relative z-10 mx-auto grid min-h-[100dvh] w-full max-w-[1240px] items-center gap-8 px-4 py-8 md:px-8 lg:grid-cols-[minmax(0,1fr)_440px] lg:gap-16">
        {/* brand statement */}
        <section className="order-1 max-w-xl" aria-labelledby="pn-hero">
          <Link href="/" className="mb-6 inline-flex items-center gap-1.5 text-[13px] text-glacier/80 hover:text-white sm:mb-8">
            <ArrowLeft className="h-3.5 w-3.5" aria-hidden /> Back to the portal
          </Link>
          <div className="flex items-center gap-3">
            <span className="pn-logo-in inline-flex rounded-2xl bg-white/5 p-2 ring-1 ring-white/10 backdrop-blur">
              <LogoMark size={48} />
            </span>
            <span className="pn-rise leading-none" style={{ animationDelay: "0.15s" }}>
              <span className="block font-display text-[26px] font-semibold tracking-tight">{BRAND}</span>
              <span className="mt-1 block font-mono text-[10px] uppercase tracking-[0.24em] text-glacier/75">SIH26063 · Polar Knowledge Platform</span>
            </span>
          </div>
          <h1 id="pn-hero" className="pn-rise mt-6 text-[28px] leading-[1.12] sm:mt-8 sm:text-[34px] md:text-[46px]" style={{ animationDelay: "0.25s" }}>
            AI-powered polar science knowledge and outreach
          </h1>
          <p className="pn-rise mt-4 max-w-lg text-[16px] leading-relaxed text-frost/85" style={{ animationDelay: "0.35s" }}>
            Unified polar science knowledge, evidence-grounded AI, and research outreach.
          </p>
          <ol className="pn-rise mt-7 hidden flex-wrap items-center gap-x-2 gap-y-2 sm:flex" style={{ animationDelay: "0.45s" }} aria-label="Knowledge journey">
            {STAGES.map((s, i) => (
              <li key={s} className="flex items-center gap-2">
                <span className="rounded-full border border-white/12 bg-white/[0.04] px-2.5 py-1 font-mono text-[10.5px] uppercase tracking-wider text-glacier/85">{s}</span>
                {i < STAGES.length - 1 && <span className="h-px w-3 bg-glacier/30" aria-hidden />}
              </li>
            ))}
          </ol>
          <p className="pn-rise mt-8 hidden font-mono text-[11px] tracking-wide text-mist/70 lg:block" style={{ animationDelay: "0.55s" }} aria-hidden>
            Maitri 70.77°S 11.73°E · Bharati 69.41°S 76.19°E · Himadri 78.92°N 11.93°E
          </p>
        </section>

        {/* sign-in card */}
        <section className="pn-card-in order-2 w-full" aria-labelledby="pn-signin">
          <div className="rounded-[22px] border border-white/10 bg-white/[0.06] p-1.5 shadow-[0_30px_80px_-30px_rgba(0,0,0,0.6)] backdrop-blur-xl">
            <div className="rounded-[18px] bg-snow px-5 py-6 text-ink sm:px-7 sm:py-7">
              {entering ? (
                <div className="flex min-h-[340px] items-center justify-center">
                  <PolarLoader dark={false} />
                </div>
              ) : (
                <>
                  <h2 id="pn-signin" className="text-[26px] text-night">Sign in</h2>
                  <p className="mt-1 text-[13.5px] text-ink-soft">Public visitors can explore without an account.</p>

                  {demo.data?.enabled && (
                    <div className="mt-5">
                      <p className="mb-2 font-mono text-[10.5px] uppercase tracking-wider text-steel">One-click demo accounts</p>
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
                              className="group rounded-xl border border-frost bg-white p-3 text-left shadow-card transition hover:-translate-y-px hover:border-cyan hover:shadow-lift focus-visible:border-cyan disabled:opacity-60"
                            >
                              <I className="mb-1.5 h-4.5 w-4.5 text-cyan-deep" aria-hidden />
                              <span className="block text-[14px] font-medium text-night">{a.label} Demo</span>
                              <span className="mt-0.5 line-clamp-2 block text-[12px] text-steel">{busy === a.role ? "Signing in…" : a.description}</span>
                            </button>
                          );
                        })}
                      </div>
                      <div className="my-5 flex items-center gap-3 text-[12px] text-mist">
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
                    <div>
                      <label htmlFor="pn-email" className="mb-1.5 block text-[13px] font-medium text-night">Email</label>
                      <input id="pn-email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                        className="pn-input h-11 w-full rounded-xl border border-frost bg-white/80 px-3.5 text-[15px] text-night placeholder:text-mist" placeholder="you@institute.org" />
                    </div>
                    <div>
                      <label htmlFor="pn-password" className="mb-1.5 block text-[13px] font-medium text-night">Password</label>
                      <input id="pn-password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)}
                        className="pn-input h-11 w-full rounded-xl border border-frost bg-white/80 px-3.5 text-[15px] text-night" />
                    </div>
                    {err && <p role="alert" className="rounded-lg bg-[#fbe9e5] px-3 py-2 text-[13px] text-coral">{err}</p>}
                    <button
                      type="submit"
                      disabled={!!busy}
                      className="pn-sheen inline-flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-night text-[15px] font-medium text-white shadow-[0_10px_30px_-12px_rgba(26,163,200,0.7)] transition-colors hover:bg-deep disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {busy === "form" ? <PolarLoader label="" size={20} /> : <LogIn className="h-4 w-4" aria-hidden />}
                      {busy === "form" ? "Signing in…" : "Sign in"}
                    </button>
                  </form>
                  <p className="mt-5 text-[12px] leading-relaxed text-steel">
                    Demo accounts use prototype data only. In production this would connect to institutional single sign-on — not implemented in this prototype.
                  </p>
                </>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

export default function Page() {
  return (
    <Suspense fallback={<div className="flex min-h-[100dvh] items-center justify-center bg-abyss"><PolarLoader /></div>}>
      <Login />
    </Suspense>
  );
}
