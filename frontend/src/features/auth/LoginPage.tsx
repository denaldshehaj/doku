/* Login: split layout inspired by the reference design — brand/valuet majtas,
 * forma djathtas. No self-registration and no "forgot password" (local system:
 * password resets go through the administrator). */
import { useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { BrainCircuit, LogIn, Search, ShieldCheck } from "lucide-react";
import { ApiError } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Input, PasswordInput } from "@/components/ui/fields";
import { useAuth } from "@/providers/AuthProvider";

const FEATURES = [
  {
    icon: BrainCircuit,
    title: "Inteligjencë Artificiale",
    text: "RAG + LLM lokal për përgjigje të sakta, të bazuara vetëm në dokumente.",
  },
  {
    icon: Search,
    title: "Kërkim i avancuar",
    text: "Gjej shpejt informacionin që të nevojitet në dokumente të mëdha.",
  },
  {
    icon: ShieldCheck,
    title: "I sigurt dhe konfidencial",
    text: "Gjithçka përpunohet lokalisht — asnjë e dhënë nuk del nga kompjuteri.",
  },
];

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const user = await login(username.trim(), password);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(user.must_change_password ? "/ndrysho-fjalekalimin" : (from ?? "/"),
               { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Hyrja dështoi. Provo përsëri.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-full items-center justify-center bg-gradient-to-br from-slate-100 via-brand-50 to-slate-200 p-4 dark:from-slate-950 dark:via-brand-950 dark:to-slate-900">
      <div className="w-full max-w-4xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-pop dark:border-slate-800 dark:bg-slate-900">
        <div className="grid md:grid-cols-2">
          {/* Brand side */}
          <div className="flex flex-col justify-center gap-6 border-b border-slate-100 p-8 md:border-b-0 md:border-r dark:border-slate-800">
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-400">Mirë se vini në</p>
              <h1 className="mt-1 text-5xl font-black tracking-tight text-brand-800 dark:text-brand-100">
                DOKU
              </h1>
              <div className="mt-2 h-1 w-14 rounded bg-accent-600" aria-hidden />
              <p className="mt-3 font-medium text-slate-700 dark:text-slate-200">
                Sistemi Inteligjent për Analizë Dokumentesh
              </p>
              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                Platformë e sigurt për analizë, kërkim dhe menaxhim inteligjent
                të dokumenteve zyrtare institucionale.
              </p>
            </div>
            <ul className="space-y-4">
              {FEATURES.map(({ icon: Icon, title, text }) => (
                <li key={title} className="flex gap-3">
                  <span className="mt-0.5 rounded-xl bg-brand-50 p-2 text-brand-700 dark:bg-brand-950 dark:text-brand-300">
                    <Icon className="h-5 w-5" aria-hidden />
                  </span>
                  <span>
                    <span className="block text-sm font-semibold text-slate-800 dark:text-slate-100">{title}</span>
                    <span className="block text-sm text-slate-500 dark:text-slate-400">{text}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>

          {/* Form side */}
          <div className="flex flex-col justify-center p-8">
            <div className="mx-auto w-full max-w-sm">
              <div className="mb-6 text-center">
                <span className="inline-flex rounded-2xl bg-brand-50 p-3 text-brand-700 dark:bg-brand-950 dark:text-brand-300">
                  <LogIn className="h-6 w-6" aria-hidden />
                </span>
                <h2 className="mt-3 text-xl font-bold text-slate-900 dark:text-slate-50">
                  Hyrje në sistem
                </h2>
              </div>

              <form onSubmit={onSubmit} className="space-y-4" noValidate>
                <Input label="Emri i përdoruesit" autoComplete="username"
                       value={username} onChange={(e) => setUsername(e.target.value)}
                       placeholder="p.sh. emri.mbiemri" required autoFocus />
                <PasswordInput label="Fjalëkalimi" autoComplete="current-password"
                               value={password} onChange={(e) => setPassword(e.target.value)}
                               required />
                {error && (
                  <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
                    {error}
                  </p>
                )}
                <Button type="submit" size="lg" loading={loading} className="w-full">
                  Hyr në sistem
                </Button>
              </form>

              <p className="mt-6 border-t border-slate-100 pt-4 text-center text-xs text-slate-400 dark:border-slate-800 dark:text-slate-500">
                <ShieldCheck className="mr-1 inline h-3.5 w-3.5 align-[-2px]" aria-hidden />
                Llogaritë krijohen dhe fjalëkalimet resetohen vetëm nga administratori.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
