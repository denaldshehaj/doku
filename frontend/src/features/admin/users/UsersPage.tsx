/* Admin — user management: create (forced password change on first login),
 * edit (role/status with last-admin guard surfaced from the API), passwords. */
import { useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, KeyRound, Pencil, Search, UserPlus } from "lucide-react";
import { ApiError } from "@/api/client";
import { usersApi } from "@/api/endpoints";
import type { UserRow } from "@/api/types";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input, PasswordInput, Select } from "@/components/ui/fields";
import { Modal } from "@/components/ui/Modal";
import { Alert, EmptyState, Skeleton } from "@/components/ui/misc";
import { TableShell, Td, Th, Tr } from "@/components/shared/DataTable";
import { PageHeader } from "@/components/shared/PageHeader";
import { useAuth } from "@/providers/AuthProvider";
import { useToast } from "@/providers/ToastProvider";
import { formatDate } from "@/lib/format";

const ROLE_LABELS: Record<string, string> = { admin: "Administrator", punonjes: "Punonjës" };

function CreateUserModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("punonjes");

  const create = useMutation({
    mutationFn: () => usersApi.create({ username: username.trim(), password,
                                        full_name: fullName.trim(), role }),
    onSuccess: (u) => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      toast("success", `U krijua '${u.username}'`,
            "Do t'i kërkohet të ndryshojë fjalëkalimin në hyrjen e parë.");
      setUsername(""); setFullName(""); setPassword(""); setRole("punonjes");
      onClose();
    },
    onError: (err) => toast("error", "Krijimi dështoi",
                            err instanceof ApiError ? err.message : undefined),
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    create.mutate();
  };

  return (
    <Modal open={open} onClose={onClose} title="Krijo përdorues të ri"
           footer={
             <>
               <Button variant="outline" onClick={onClose}>Anulo</Button>
               <Button type="submit" form="create-user-form" loading={create.isPending}>
                 Krijo përdoruesin
               </Button>
             </>
           }>
      <form id="create-user-form" onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Input label="Emri i përdoruesit" value={username} required
                 hint="3–32 karaktere: shkronja, numra, '_' ose '.'"
                 onChange={(e) => setUsername(e.target.value)} />
          <Input label="Emri i plotë" value={fullName}
                 onChange={(e) => setFullName(e.target.value)} />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <PasswordInput label="Fjalëkalimi fillestar" value={password} required
                         hint="Të paktën 6 karaktere; ndryshohet në hyrjen e parë."
                         onChange={(e) => setPassword(e.target.value)} />
          <Select label="Roli" value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="punonjes">Punonjës</option>
            <option value="admin">Administrator</option>
          </Select>
        </div>
      </form>
    </Modal>
  );
}

function EditUserModal({ user, onClose }: { user: UserRow; onClose: () => void }) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { user: me } = useAuth();
  const [fullName, setFullName] = useState(user.full_name);
  const [role, setRole] = useState<string>(user.role);
  const [active, setActive] = useState(user.is_active ? "1" : "0");
  const [newPassword, setNewPassword] = useState("");
  const [mustChange, setMustChange] = useState(true);
  const [tempPassword, setTempPassword] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: () => usersApi.patch(user.username, {
      full_name: fullName, role, is_active: active === "1",
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      toast("success", `Ndryshimet për '${user.username}' u ruajtën`);
      onClose();
    },
    onError: (err) => toast("error", "Ruajtja dështoi",
                            err instanceof ApiError ? err.message : undefined),
  });

  const setPassword = useMutation({
    mutationFn: () => usersApi.setPassword(user.username, newPassword, mustChange),
    onSuccess: () => {
      toast("success", `Fjalëkalimi i '${user.username}' u ndryshua`);
      setNewPassword("");
    },
    onError: (err) => toast("error", "Ndryshimi dështoi",
                            err instanceof ApiError ? err.message : undefined),
  });

  const reset = useMutation({
    mutationFn: () => usersApi.resetPassword(user.username),
    onSuccess: (r) => setTempPassword(r.temporary_password),
    onError: (err) => toast("error", "Resetimi dështoi",
                            err instanceof ApiError ? err.message : undefined),
  });

  const copyTemp = async () => {
    if (!tempPassword) return;
    try {
      await navigator.clipboard.writeText(tempPassword);
      toast("success", "U kopjua në clipboard");
    } catch {
      /* clipboard blocked */
    }
  };

  const isSelf = me?.username === user.username;

  return (
    <Modal open onClose={onClose} title={`Ndrysho — ${user.username}`} width="max-w-xl"
           footer={
             <>
               <Button variant="outline" onClick={onClose}>Mbyll</Button>
               <Button onClick={() => save.mutate()} loading={save.isPending}>
                 Ruaj ndryshimet
               </Button>
             </>
           }>
      <div className="space-y-4">
        <Input label="Emri i plotë" value={fullName}
               onChange={(e) => setFullName(e.target.value)} />
        <div className="grid gap-4 sm:grid-cols-2">
          <Select label="Roli" value={role} onChange={(e) => setRole(e.target.value)}
                  disabled={isSelf}
                  hint={isSelf ? "Nuk mund të ndryshosh rolin tënd." : undefined}>
            <option value="punonjes">Punonjës</option>
            <option value="admin">Administrator</option>
          </Select>
          <Select label="Statusi" value={active} onChange={(e) => setActive(e.target.value)}
                  disabled={isSelf}
                  hint={isSelf ? "Nuk mund të çaktivizosh veten." : undefined}>
            <option value="1">Aktiv</option>
            <option value="0">Joaktiv</option>
          </Select>
        </div>

        <div className="border-t border-slate-100 pt-4 dark:border-slate-800">
          <p className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
            <KeyRound className="h-4 w-4" aria-hidden /> Menaxhimi i fjalëkalimit
          </p>
          <div className="space-y-3">
            <PasswordInput label="Fjalëkalim i ri" value={newPassword}
                           onChange={(e) => setNewPassword(e.target.value)} />
            <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
              <input type="checkbox" checked={mustChange}
                     onChange={(e) => setMustChange(e.target.checked)}
                     className="accent-brand-700" />
              Detyro ndryshimin në hyrjen e parë
            </label>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" onClick={() => setPassword.mutate()}
                      loading={setPassword.isPending} disabled={newPassword.length < 6}>
                Vendos fjalëkalimin
              </Button>
              <Button variant="outline" size="sm" onClick={() => reset.mutate()}
                      loading={reset.isPending}>
                Reseto në fjalëkalim të përkohshëm
              </Button>
            </div>
            {tempPassword && (
              <Alert variant="info" title="Fjalëkalimi i përkohshëm (shfaqet vetëm një herë)">
                <span className="flex items-center gap-2">
                  <code className="rounded bg-white/60 px-2 py-0.5 font-mono text-sm dark:bg-slate-800">
                    {tempPassword}
                  </code>
                  <button onClick={copyTemp} aria-label="Kopjo fjalëkalimin e përkohshëm"
                          className="rounded p-1 hover:bg-white/60 dark:hover:bg-slate-800">
                    <Copy className="h-4 w-4" aria-hidden />
                  </button>
                </span>
              </Alert>
            )}
          </div>
        </div>
      </div>
    </Modal>
  );
}

export default function UsersPage() {
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<UserRow | null>(null);

  const users = useQuery({ queryKey: ["users"], queryFn: usersApi.list });

  const filtered = useMemo(() => {
    if (!users.data) return [];
    const kw = search.trim().toLowerCase();
    if (!kw) return users.data;
    return users.data.filter((u) =>
      u.username.toLowerCase().includes(kw) || u.full_name.toLowerCase().includes(kw));
  }, [users.data, search]);

  return (
    <>
      <PageHeader title="Menaxhimi i Përdoruesve"
                  subtitle="Krijo llogari, cakto role dhe menaxho fjalëkalimet. Nuk ka vetë-regjistrim publik."
                  actions={
                    <Button onClick={() => setCreateOpen(true)}>
                      <UserPlus className="h-4 w-4" aria-hidden />
                      Shto përdorues
                    </Button>
                  } />

      <div className="relative mb-4 max-w-sm">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden />
        <Input aria-label="Kërko përdorues" placeholder="Kërko përdorues…" className="pl-9"
               value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      <Card>
        {users.isPending ? (
          <div className="space-y-3 p-5">
            {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-9 w-full" />)}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState title="Asnjë përdorues i gjetur" />
        ) : (
          <TableShell ariaLabel="Përdoruesit e sistemit">
            <thead>
              <tr>
                <Th>Përdoruesi</Th>
                <Th className="hidden sm:table-cell">Emri i plotë</Th>
                <Th>Roli</Th>
                <Th>Statusi</Th>
                <Th className="hidden md:table-cell">Krijuar</Th>
                <Th><span className="sr-only">Veprime</span></Th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((u) => (
                <Tr key={u.id}>
                  <Td className="font-medium text-slate-800 dark:text-slate-100">{u.username}</Td>
                  <Td className="hidden sm:table-cell">{u.full_name || "—"}</Td>
                  <Td>
                    <Badge variant={u.role === "admin" ? "brand" : "neutral"}>
                      {ROLE_LABELS[u.role] ?? u.role}
                    </Badge>
                  </Td>
                  <Td>
                    <Badge variant={u.is_active ? "success" : "danger"}>
                      {u.is_active ? "Aktiv" : "Joaktiv"}
                    </Badge>
                  </Td>
                  <Td className="hidden tabular-nums md:table-cell">{formatDate(u.created_at)}</Td>
                  <Td>
                    <div className="flex justify-end">
                      <button onClick={() => setEditing(u)} title="Ndrysho" aria-label={`Ndrysho ${u.username}`}
                              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200">
                        <Pencil className="h-4 w-4" aria-hidden />
                      </button>
                    </div>
                  </Td>
                </Tr>
              ))}
            </tbody>
          </TableShell>
        )}
      </Card>

      <CreateUserModal open={createOpen} onClose={() => setCreateOpen(false)} />
      {editing && <EditUserModal key={editing.id} user={editing} onClose={() => setEditing(null)} />}
    </>
  );
}
