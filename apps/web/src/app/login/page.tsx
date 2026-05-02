"use client";

import { useCallback, useState } from "react";
import { getBrowserSupabase } from "@/lib/supabase/client";

export default function LoginPage(): React.ReactElement {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGoogleLogin = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const supabase = getBrowserSupabase();
      const origin = typeof window !== "undefined" ? window.location.origin : "";
      const { error: signInError } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: `${origin}/auth/callback`,
          queryParams: {
            hd: "thorus.com.br",
            access_type: "offline",
            prompt: "consent",
          },
        },
      });
      if (signInError) {
        setError(signInError.message);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao iniciar login");
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--main-bg,#0b0b0c)] text-white">
      <div className="w-full max-w-sm space-y-6 rounded-xl border border-white/10 bg-black/20 p-8 backdrop-blur">
        <div className="text-center">
          <h1 className="text-2xl font-semibold">Oráculo Thórus</h1>
          <p className="mt-2 text-sm text-white/60">
            Acesso restrito a colaboradores Thórus
          </p>
        </div>

        <button
          type="button"
          onClick={handleGoogleLogin}
          disabled={loading}
          className="flex w-full items-center justify-center gap-3 rounded-md bg-white px-4 py-2.5 text-sm font-medium text-black shadow-sm transition hover:bg-white/90 disabled:opacity-50"
        >
          <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden>
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.76h3.56c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.56-2.76c-.99.66-2.25 1.06-3.72 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.11A6.6 6.6 0 0 1 5.5 12c0-.74.13-1.45.34-2.11V7.05H2.18a11 11 0 0 0 0 9.9l3.66-2.84z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.07.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1A11 11 0 0 0 2.18 7.05l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38z"
            />
          </svg>
          {loading ? "Redirecionando..." : "Entrar com Google"}
        </button>

        {error ? (
          <p className="text-center text-sm text-red-400">{error}</p>
        ) : null}

        <p className="text-center text-xs text-white/40">
          Apenas e-mails @thorus.com.br têm acesso.
        </p>
      </div>
    </div>
  );
}
