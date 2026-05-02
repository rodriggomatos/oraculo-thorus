"use client";

import { useEffect, useState } from "react";
import { getBrowserSupabase } from "@/lib/supabase/client";

export type AuthUser = {
  id: string;
  email: string;
  name: string;
  initials: string;
};


function deriveInitials(name: string): string {
  const words = name.trim().split(/\s+/);
  if (words.length === 0 || !words[0]) return "?";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return `${words[0][0]}${words[words.length - 1][0]}`.toUpperCase();
}


export function useUser(): { user: AuthUser | null; loading: boolean } {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let supabase;
    try {
      supabase = getBrowserSupabase();
    } catch {
      setLoading(false);
      return;
    }
    let mounted = true;

    async function load(): Promise<void> {
      const {
        data: { user: sbUser },
      } = await supabase.auth.getUser();
      if (!mounted) return;
      if (sbUser) {
        const meta = (sbUser.user_metadata ?? {}) as Record<string, unknown>;
        const name =
          (meta["full_name"] as string | undefined) ??
          (meta["name"] as string | undefined) ??
          sbUser.email ??
          "Usuário";
        setUser({
          id: sbUser.id,
          email: sbUser.email ?? "",
          name,
          initials: deriveInitials(name),
        });
      }
      setLoading(false);
    }

    void load();

    const { data: subscription } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!mounted) return;
      if (!session?.user) {
        setUser(null);
        return;
      }
      const meta = (session.user.user_metadata ?? {}) as Record<string, unknown>;
      const name =
        (meta["full_name"] as string | undefined) ??
        (meta["name"] as string | undefined) ??
        session.user.email ??
        "Usuário";
      setUser({
        id: session.user.id,
        email: session.user.email ?? "",
        name,
        initials: deriveInitials(name),
      });
    });

    return () => {
      mounted = false;
      subscription.subscription.unsubscribe();
    };
  }, []);

  return { user, loading };
}
