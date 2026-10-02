"use client";

import clsx from "clsx";
import {
  Bell,
  Bot,
  ChevronDown,
  Compass,
  House,
  Lock,
  LogIn,
  LogOut,
  Map as MapIcon,
  Menu,
  Search,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { Logo } from "@/components/art/Logo";
import { useToast } from "@/components/common/Toast";
import { api, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { timeAgo } from "@/lib/format";
import type { Notification, Role } from "@/lib/types";
import { NAV, type NavItem } from "./nav";

function isActive(pathname: string, href: string) {
  if (href.includes("?")) return false;
  const base = href;
  if (base === "/") return pathname === "/";
  if (base === "/admin") return pathname === "/admin";
  return pathname === base || pathname.startsWith(base + "/");
}

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { user, can } = useAuth();
  const visible = (i: NavItem) => (i.permission ? can(i.permission) : i.auth ? !!user : true);
  return (
    <nav aria-label="Main navigation" className="flex h-full flex-col">
      <div className="px-5 pb-4 pt-5">
        <Link href="/" onClick={onNavigate} aria-label="PolarNexus home">
          <Logo />
        </Link>
      </div>
      <div className="flex-1 overflow-y-auto px-3 pb-6 scrollbar-thin">
        {NAV.map((g) => {
          const items = g.items.filter(visible);
          const locked = g.items.filter((i) => !visible(i));
          if (!items.length && g.tone !== "pro") return null;
          return (
            <div key={g.label} className="mt-4 first:mt-1">
              <p className="mb-1.5 flex items-center gap-2 px-3 font-mono text-[10px] uppercase tracking-[0.2em] text-mist/80">
                {g.label}
                {g.tone === "admin" && <span className="rounded bg-white/10 px-1 py-px text-[9px] tracking-wider text-glacier">Admin</span>}
                {g.tone === "pro" && <span className="rounded bg-white/10 px-1 py-px text-[9px] tracking-wider text-glacier">Pro</span>}
              </p>
              <ul className="space-y-0.5">
                {items.map((i) => {
                  const active = isActive(pathname, i.href);
                  const I = i.icon;
                  return (
                    <li key={i.href}>
                      <Link
                        href={i.href}
                        onClick={onNavigate}
                        aria-current={active ? "page" : undefined}
                        className={clsx(
                          "group flex items-center gap-3 rounded-lg px-3 py-2 text-[13.5px] transition-colors",
                          active ? "bg-white/[0.09] text-white" : "text-frost/75 hover:bg-white/[0.05] hover:text-white",
                        )}
                      >
                        <I className={clsx("h-[17px] w-[17px] shrink-0", active ? "text-aurora" : "text-mist group-hover:text-glacier")} />
                        {i.label}
                        {active && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-aurora" />}
                      </Link>
                    </li>
                  );
                })}
                {g.tone === "pro" && locked.length > 0 && (
                  <li>
                    <Link href="/login" onClick={onNavigate} className="flex items-center gap-3 rounded-lg px-3 py-2 text-[12.5px] text-mist/70 hover:text-glacier">
                      <Lock className="h-[15px] w-[15px]" /> Sign in for {locked.length} professional tools
                    </Link>
                  </li>
                )}
              </ul>
            </div>
          );
        })}
      </div>
      <div className="border-t border-white/10 px-5 py-4 text-[11px] leading-relaxed text-mist/80">
        <p className="font-mono uppercase tracking-wider text-glacier/80">SIH26063 Prototype</p>
        <p className="mt-1">Demo corpus — not official institutional data.</p>
      </div>
    </nav>
  );
}

function GlobalSearch() {
  const router = useRouter();
  const [q, setQ] = useState("");
  return (
    <form
      role="search"
      onSubmit={(e) => {
        e.preventDefault();
        if (q.trim()) router.push(`/explore?q=${encodeURIComponent(q.trim())}`);
      }}
      className="relative hidden max-w-md flex-1 md:block"
    >
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-mist" />
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search polar knowledge…"
        aria-label="Search polar knowledge"
        className="h-10 w-full rounded-xl border border-frost bg-snow pl-9 pr-3 text-sm text-night placeholder:text-mist focus:border-cyan focus:bg-white focus:outline-none focus:ring-2 focus:ring-cyan/20"
      />
    </form>
  );
}

function Notifications() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Notification[]>([]);
  const [unread, setUnread] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const router = useRouter();

  const load = useCallback(() => {
    if (!user) return;
    api<{ unread: number; results: Notification[] }>("/api/notifications")
      .then((d) => {
        setItems(d.results);
        setUnread(d.unread);
      })
      .catch(() => {});
  }, [user]);

  useEffect(() => {
    load();
    if (!user) return;
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, [load, user]);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  if (!user) return null;
  return (
    <div className="relative" ref={ref}>
      <button
        aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`}
        onClick={() => {
          setOpen((o) => !o);
          if (!open) load();
        }}
        className="relative rounded-lg p-2 text-ink-soft hover:bg-ice hover:text-night"
      >
        <Bell className="h-5 w-5" />
        {unread > 0 && <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-coral px-1 text-[10px] font-semibold text-white">{unread}</span>}
      </button>
      {open && (
        <div className="absolute right-0 top-12 z-50 w-[min(92vw,380px)] animate-fade-up overflow-hidden rounded-2xl border border-frost bg-white shadow-lift">
          <div className="flex items-center justify-between border-b border-frost px-4 py-3">
            <p className="font-medium text-night">Notifications</p>
            {unread > 0 && (
              <button
                className="text-xs text-cyan-deep hover:underline"
                onClick={async () => {
                  await post("/api/notifications/read-all").catch(() => {});
                  load();
                }}
              >
                Mark all read
              </button>
            )}
          </div>
          <ul className="max-h-[60vh] overflow-y-auto scrollbar-thin">
            {items.length === 0 && <li className="px-4 py-8 text-center text-sm text-steel">You&apos;re all caught up.</li>}
            {items.map((n) => (
              <li key={n.id}>
                <button
                  onClick={async () => {
                    await post(`/api/notifications/${n.id}/read`).catch(() => {});
                    setOpen(false);
                    load();
                    if (n.link) router.push(n.link);
                  }}
                  className={clsx("flex w-full gap-3 border-b border-frost/60 px-4 py-3 text-left hover:bg-snow", !n.read && "bg-[#f3fafc]")}
                >
                  <span
                    className={clsx("mt-1.5 h-2 w-2 shrink-0 rounded-full", {
                      "bg-teal": n.kind === "success",
                      "bg-amber": n.kind === "warning" || n.kind === "review",
                      "bg-coral": n.kind === "error",
                      "bg-cyan": n.kind === "info",
                      "opacity-0": n.read,
                    })}
                  />
                  <span className="min-w-0">
                    <span className="block text-sm font-medium text-night">{n.title}</span>
                    <span className="block text-[13px] text-ink-soft">{n.body}</span>
                    <span className="mt-0.5 block font-mono text-[10.5px] text-mist">{timeAgo(n.at)}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

const ROLE_ORDER: Role[] = ["public", "researcher", "editor", "admin"];

function UserMenu() {
  const { user, logout, demoLogin } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const toast = useToast();
  const router = useRouter();
  useEffect(() => {
    const onDoc = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);
  if (!user)
    return (
      <Link href="/login" className="inline-flex h-9 items-center gap-2 rounded-lg bg-night px-3.5 text-sm font-medium text-white hover:bg-deep">
        <LogIn className="h-4 w-4" /> <span className="hidden sm:inline">Sign in</span>
      </Link>
    );
  const initials = user.name.replace(/^Dr\.\s*/, "").split(" ").map((p) => p[0]).slice(0, 2).join("");
  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen((o) => !o)} className="flex items-center gap-2 rounded-xl py-1 pl-1 pr-2 hover:bg-ice" aria-haspopup="menu" aria-expanded={open}>
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-cyan to-teal text-xs font-semibold text-white">{initials}</span>
        <span className="hidden text-left leading-tight sm:block">
          <span className="block max-w-[140px] truncate text-[13px] font-medium text-night">{user.name}</span>
          <span className="block font-mono text-[10px] uppercase tracking-wide text-steel">{user.role_label}</span>
        </span>
        <ChevronDown className="h-4 w-4 text-mist" />
      </button>
      {open && (
        <div role="menu" className="absolute right-0 top-12 z-50 w-64 animate-fade-up rounded-2xl border border-frost bg-white p-2 shadow-lift">
          <div className="px-3 py-2">
            <p className="truncate text-sm font-medium text-night">{user.name}</p>
            <p className="truncate text-xs text-steel">{user.email}</p>
          </div>
          {user.is_demo && (
            <div className="border-t border-frost px-3 pb-1 pt-2.5">
              <p className="mb-1.5 font-mono text-[10px] uppercase tracking-wider text-steel">Switch demo role</p>
              <div className="grid grid-cols-2 gap-1">
                {ROLE_ORDER.map((r) => (
                  <button
                    key={r}
                    disabled={r === user.role}
                    onClick={async () => {
                      try {
                        const u = await demoLogin(r);
                        toast("success", `Now signed in as ${u.role_label}`, u.name);
                        setOpen(false);
                        router.refresh();
                      } catch (e) {
                        toast("error", "Could not switch role", (e as Error).message);
                      }
                    }}
                    className={clsx("rounded-lg px-2 py-1.5 text-[12.5px] capitalize", r === user.role ? "bg-night text-white" : "bg-ice text-deep hover:bg-frost")}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>
          )}
          <div className="mt-1 border-t border-frost pt-1">
            <Link href="/my-knowledge" onClick={() => setOpen(false)} className="block rounded-lg px-3 py-2 text-sm text-ink-soft hover:bg-ice">My Knowledge</Link>
            <button
              onClick={async () => {
                await logout();
                setOpen(false);
                toast("info", "Signed out");
                router.push("/");
              }}
              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-ink-soft hover:bg-ice"
            >
              <LogOut className="h-4 w-4" /> Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function MobileBottomNav({ onMenu }: { onMenu: () => void }) {
  const pathname = usePathname();
  const items = [
    { href: "/", label: "Home", icon: House },
    { href: "/explore", label: "Explore", icon: Compass },
    { href: "/assistant", label: "Ask AI", icon: Bot },
    { href: "/map", label: "Map", icon: MapIcon },
  ];
  return (
    <nav aria-label="Quick navigation" className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t border-frost bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden">
      {items.map(({ href, label, icon: I }) => {
        const active = isActive(pathname, href);
        return (
          <Link key={href} href={href} className={clsx("flex flex-col items-center gap-0.5 py-2 text-[10.5px]", active ? "text-cyan-deep" : "text-steel")}>
            <I className="h-5 w-5" />
            {label}
          </Link>
        );
      })}
      <button onClick={onMenu} className="flex flex-col items-center gap-0.5 py-2 text-[10.5px] text-steel" aria-label="Open full menu">
        <Menu className="h-5 w-5" />
        Menu
      </button>
    </nav>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [drawer, setDrawer] = useState(false);
  const pathname = usePathname();
  useEffect(() => setDrawer(false), [pathname]);
  const fullBleed = pathname === "/login";

  if (fullBleed) return <>{children}</>;

  return (
    <div className="min-h-screen">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[200] focus:rounded-lg focus:bg-white focus:px-3 focus:py-2">
        Skip to content
      </a>
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[264px] bg-night lg:block">
        <Sidebar />
      </aside>
      {drawer && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation menu">
          <div className="absolute inset-0 bg-abyss/60 backdrop-blur-sm" onClick={() => setDrawer(false)} />
          <aside className="absolute inset-y-0 left-0 w-[284px] max-w-[85vw] animate-fade-up bg-night">
            <button onClick={() => setDrawer(false)} aria-label="Close menu" className="absolute right-3 top-5 z-10 rounded-lg p-1.5 text-frost hover:bg-white/10">
              <X className="h-5 w-5" />
            </button>
            <Sidebar onNavigate={() => setDrawer(false)} />
          </aside>
        </div>
      )}
      <div className="lg:pl-[264px]">
        <header className="sticky top-0 z-30 border-b border-frost/80 bg-white/85 backdrop-blur-md">
          <div className="flex h-16 items-center gap-3 px-4 md:px-6">
            <button className="rounded-lg p-2 text-ink-soft hover:bg-ice lg:hidden" onClick={() => setDrawer(true)} aria-label="Open menu">
              <Menu className="h-5 w-5" />
            </button>
            <Link href="/" className="lg:hidden" aria-label="Home">
              <Logo dark={false} compact />
            </Link>
            <Suspense>
              <GlobalSearch />
            </Suspense>
            <div className="ml-auto flex items-center gap-1.5">
              <Link href="/explore" className="rounded-lg p-2 text-ink-soft hover:bg-ice md:hidden" aria-label="Search">
                <Search className="h-5 w-5" />
              </Link>
              <Link href="/assistant" className="hidden items-center gap-2 rounded-lg border border-frost px-3 py-1.5 text-[13px] text-deep hover:border-glacier hover:bg-ice sm:inline-flex">
                <Bot className="h-4 w-4 text-cyan-deep" /> Ask AI
              </Link>
              <Notifications />
              <UserMenu />
            </div>
          </div>
        </header>
        <main id="main" className="min-h-[calc(100vh-4rem)] pb-24 lg:pb-10">
          {children}
        </main>
      </div>
      <MobileBottomNav onMenu={() => setDrawer(true)} />
    </div>
  );
}

export function Container({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={clsx("mx-auto w-full max-w-[1280px] px-4 py-6 md:px-8 md:py-8", className)}>{children}</div>;
}
