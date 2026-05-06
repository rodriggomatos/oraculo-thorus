import Link from "next/link";

type SearchParams = Promise<{ reason?: string }>;

export default async function AuthErrorPage({
  searchParams,
}: {
  searchParams: SearchParams;
}): Promise<React.ReactElement> {
  const { reason } = await searchParams;
  const message = decodeURIComponent(reason ?? "Erro de autenticação");

  const friendly =
    reason === "domain"
      ? "Apenas e-mails @thorusengenharia.com.br podem acessar o Oráculo."
      : message;

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--main-bg,#0b0b0c)] text-white">
      <div className="w-full max-w-md space-y-6 rounded-xl border border-white/10 bg-black/20 p-8 text-center">
        <h1 className="text-xl font-semibold">Acesso negado</h1>
        <p className="text-sm text-white/70">{friendly}</p>
        <Link
          href="/login"
          className="inline-block rounded-md bg-white px-4 py-2 text-sm font-medium text-black hover:bg-white/90"
        >
          Voltar pro login
        </Link>
      </div>
    </div>
  );
}
