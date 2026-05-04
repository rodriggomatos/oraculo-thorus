"use client";


export type UserPermissions = {
  canCreateProject: boolean;
};


export function useUserPermissions(): UserPermissions {
  // MOCK: substituir por leitura real de user_profiles.role quando backend
  // tiver endpoint (provavelmente /auth/me já tem `role`; mapear role==='admin'
  // ou role==='engineer' → canCreateProject=true).
  return {
    canCreateProject: true,
  };
}
