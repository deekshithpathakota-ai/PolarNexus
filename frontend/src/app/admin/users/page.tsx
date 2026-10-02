"use client";

import { Plus, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { RequireAuth } from "@/components/common/RequireAuth";
import { useToast } from "@/components/common/Toast";
import { Badge, Button, Card, DemoBadge, ErrorState, Field, Modal, PageHeader, Skeleton, inputCls } from "@/components/common/ui";
import { Container } from "@/components/layout/AppShell";
import { patch, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { timeAgo } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { User } from "@/lib/types";

interface UserRow extends User { is_active: boolean; last_login: string | null; created_at: string; content_items: number }
interface RoleInfo { name: string; label: string; description: string; permissions: string[] }

function Users() {
  const { data, error, loading, reload, setData } = useApi<{ results: UserRow[]; roles: RoleInfo[] }>("/api/admin/users");
  const { user: me } = useAuth();
  const toast = useToast();
  const [create, setCreate] = useState(false);
  const [f, setF] = useState({ email: "", name: "", role: "researcher", institution: "", password: "" });
  const [busy, setBusy] = useState(false);

  const update = async (u: UserRow, body: Record<string, unknown>) => {
    try {
      const r = await patch<UserRow>(`/api/admin/users/${u.id}`, body);
      setData(data ? { ...data, results: data.results.map((x) => (x.id === u.id ? { ...x, ...r } : x)) } : null);
      toast("success", "User updated", "Change recorded in the audit log.");
    } catch (e) {
      toast("error", "Update failed", (e as Error).message);
    }
  };

  return (
    <Container className="max-w-[1300px]">
      <PageHeader eyebrow="Administration" title="Users & Roles" description="Role-based access control: each role unlocks a defined set of permissions, enforced by the API on every request."
        actions={<Button icon={<Plus className="h-4 w-4" />} onClick={() => setCreate(true)}>Add user</Button>} />
      {error ? <ErrorState error={error} onRetry={reload} /> : loading || !data ? <Skeleton className="h-96 w-full rounded-2xl" /> : (
        <>
          <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {data.roles.map((r) => (
              <Card key={r.name} className="p-4">
                <p className="flex items-center gap-1.5 font-medium text-night"><ShieldCheck className="h-4 w-4 text-cyan-deep" /> {r.label}</p>
                <p className="mt-1 text-[12.5px] text-steel">{r.description}</p>
                <div className="mt-2 flex flex-wrap gap-1">{r.permissions.map((p) => <span key={p} className="rounded bg-ice px-1.5 py-0.5 font-mono text-[10px] text-deep">{p}</span>)}</div>
              </Card>
            ))}
          </div>
          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[820px] text-left text-[13.5px]">
                <thead className="bg-snow font-mono text-[11px] uppercase tracking-wide text-steel">
                  <tr><th className="px-4 py-3">User</th><th className="px-3 py-3">Institution</th><th className="px-3 py-3">Role</th><th className="px-3 py-3">Status</th><th className="px-3 py-3">Last login</th><th className="px-3 py-3">Content</th></tr>
                </thead>
                <tbody>
                  {data.results.map((u) => (
                    <tr key={u.id} className="border-t border-frost/70">
                      <td className="px-4 py-3"><p className="font-medium text-night">{u.name} {u.id === me?.id && <Badge tone="cyan">you</Badge>}</p><p className="text-[12px] text-steel">{u.email}</p></td>
                      <td className="px-3 py-3 text-ink-soft">{u.institution}{u.is_demo && <> <DemoBadge label="Demo" /></>}</td>
                      <td className="px-3 py-3">
                        <select value={u.role} disabled={u.id === me?.id} onChange={(e) => update(u, { role: e.target.value })} aria-label={`Role for ${u.name}`} className="h-8 rounded-lg border border-frost bg-white px-2 text-[13px] disabled:opacity-60">
                          {data.roles.map((r) => <option key={r.name} value={r.name}>{r.label}</option>)}
                        </select>
                      </td>
                      <td className="px-3 py-3">
                        <button disabled={u.id === me?.id} onClick={() => update(u, { is_active: !u.is_active })} className="disabled:opacity-60" aria-label={u.is_active ? "Deactivate user" : "Activate user"}>
                          <Badge tone={u.is_active ? "teal" : "coral"}>{u.is_active ? "Active" : "Disabled"}</Badge>
                        </button>
                      </td>
                      <td className="px-3 py-3 text-[12.5px] text-steel">{u.last_login ? timeAgo(u.last_login) : "never"}</td>
                      <td className="px-3 py-3 font-mono text-[12.5px]">{u.content_items}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
      <Modal open={create} onClose={() => setCreate(false)} title="Add user">
        <div className="space-y-3">
          <Field label="Name"><input className={inputCls} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
          <Field label="Email"><input type="email" className={inputCls} value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
          <Field label="Institution"><input className={inputCls} value={f.institution} onChange={(e) => setF({ ...f, institution: e.target.value })} /></Field>
          <Field label="Role"><select className={inputCls} value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}>{data?.roles.map((r) => <option key={r.name} value={r.name}>{r.label}</option>)}</select></Field>
          <Field label="Initial password" hint="At least 10 characters. Stored as a bcrypt hash."><input type="password" className={inputCls} value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></Field>
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setCreate(false)}>Cancel</Button>
          <Button loading={busy} disabled={!f.name || !f.email || f.password.length < 10} onClick={async () => {
            setBusy(true);
            try { await post("/api/admin/users", f); toast("success", "User created"); setCreate(false); setF({ email: "", name: "", role: "researcher", institution: "", password: "" }); reload(); }
            catch (e) { toast("error", "Could not create user", (e as Error).message); } finally { setBusy(false); }
          }}>Create user</Button>
        </div>
      </Modal>
    </Container>
  );
}

export default function Page() {
  return <RequireAuth permission="manage_users" title="Users & Roles"><Users /></RequireAuth>;
}
