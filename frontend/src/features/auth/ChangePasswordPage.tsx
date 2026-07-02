/* Forced password change — the account is unusable until this completes
 * (enforced server-side by require_user, mirrored here by the route guard). */
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { KeyRound } from "lucide-react";
import { ApiError } from "@/api/client";
import { authApi } from "@/api/endpoints";
import { Button } from "@/components/ui/Button";
import { PasswordInput } from "@/components/ui/fields";
import { Alert } from "@/components/ui/misc";
import { useAuth } from "@/providers/AuthProvider";

export default function ChangePasswordPage() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [p1, setP1] = useState("");
  const [p2, setP2] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (p1.length < 6) {
      setError("Fjalëkalimi duhet të ketë të paktën 6 karaktere.");
      return;
    }
    if (p1 !== p2) {
      setError("Fjalëkalimet nuk përputhen.");
      return;
    }
    setLoading(true);
    try {
      const user = await authApi.changePassword(p1);
      setUser(user);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ndryshimi dështoi. Provo përsëri.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-full items-center justify-center bg-gradient-to-br from-slate-100 via-brand-50 to-slate-200 p-4 dark:from-slate-950 dark:via-brand-950 dark:to-slate-900">
      <div className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-8 shadow-pop dark:border-slate-800 dark:bg-slate-900">
        <div className="mb-5 text-center">
          <span className="inline-flex rounded-2xl bg-brand-50 p-3 text-brand-700 dark:bg-brand-950 dark:text-brand-300">
            <KeyRound className="h-6 w-6" aria-hidden />
          </span>
          <h1 className="mt-3 text-xl font-bold text-slate-900 dark:text-slate-50">
            Vendos një fjalëkalim të ri
          </h1>
        </div>

        <Alert variant="warning">
          Fjalëkalimi i parazgjedhur duhet ndryshuar përpara se të vazhdosh.
        </Alert>

        <form onSubmit={onSubmit} className="mt-5 space-y-4" noValidate>
          <PasswordInput label="Fjalëkalimi i ri" hint="Të paktën 6 karaktere."
                         autoComplete="new-password" value={p1}
                         onChange={(e) => setP1(e.target.value)} required autoFocus />
          <PasswordInput label="Përsërit fjalëkalimin" autoComplete="new-password"
                         value={p2} onChange={(e) => setP2(e.target.value)} required />
          {error && (
            <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
              {error}
            </p>
          )}
          <Button type="submit" size="lg" loading={loading} className="w-full">
            Ruaj fjalëkalimin
          </Button>
        </form>
      </div>
    </div>
  );
}
