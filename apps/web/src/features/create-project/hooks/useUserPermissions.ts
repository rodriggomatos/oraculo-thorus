"use client";

import { useEffect, useState } from "react";
import { getMe } from "@/lib/api";


export type UserPermissions = {
  canCreateProject: boolean;
  loading: boolean;
};


function hasCreateProject(
  role: string | undefined,
  permissions: string[] | undefined,
): boolean {
  if (role === "admin") return true;
  if (Array.isArray(permissions) && permissions.includes("create_project")) {
    return true;
  }
  return false;
}


export function useUserPermissions(): UserPermissions {
  const [canCreateProject, setCanCreateProject] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    void (async () => {
      try {
        const me = await getMe();
        if (!mounted) return;
        const profile = (me ?? {}) as {
          role?: string;
          permissions?: string[];
        };
        setCanCreateProject(hasCreateProject(profile.role, profile.permissions));
      } catch {
        if (mounted) setCanCreateProject(false);
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  return { canCreateProject, loading };
}
