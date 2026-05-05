"use client";

import { useState } from "react";
import { ExternalLink, FolderPlus, Loader2 } from "lucide-react";

import { createDriveFolder } from "@/features/create-project/mock";


export type CreateDriveFolderButtonProps = {
  projectId: string;
  initialFolderId?: string | null;
};


type Status = "idle" | "loading" | "success" | "error";


function driveUrlFor(folderId: string): string {
  return `https://drive.google.com/drive/folders/${folderId}`;
}


export function CreateDriveFolderButton({
  projectId,
  initialFolderId = null,
}: CreateDriveFolderButtonProps): React.ReactElement {
  const [status, setStatus] = useState<Status>(initialFolderId ? "success" : "idle");
  const [folderId, setFolderId] = useState<string | null>(initialFolderId);
  const [folderUrl, setFolderUrl] = useState<string | null>(
    initialFolderId ? driveUrlFor(initialFolderId) : null,
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleClick = async (): Promise<void> => {
    if (status === "loading" || status === "success") return;
    setStatus("loading");
    setErrorMessage(null);
    try {
      const result = await createDriveFolder(projectId);
      setFolderId(result.folderId);
      setFolderUrl(result.folderUrl);
      setStatus("success");
    } catch (e) {
      setErrorMessage(e instanceof Error ? e.message : "Falha desconhecida");
      setStatus("error");
    }
  };

  if (status === "success" && folderUrl && folderId) {
    return (
      <a
        href={folderUrl}
        target="_blank"
        rel="noreferrer"
        className="inline-flex items-center gap-2 rounded-full border border-emerald-400/40 bg-emerald-500/10 px-4 py-2 text-sm font-medium text-emerald-300 transition-colors hover:bg-emerald-500/20"
      >
        <ExternalLink className="h-4 w-4" aria-hidden />
        <span>✅ Pasta criada — abrir no Drive</span>
      </a>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        onClick={handleClick}
        disabled={status === "loading"}
        aria-busy={status === "loading"}
        className="inline-flex items-center gap-2 self-start rounded-full bg-white px-4 py-2 text-sm font-medium text-zinc-900 transition-colors hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {status === "loading" ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            <span>Criando pasta no Drive…</span>
          </>
        ) : (
          <>
            <FolderPlus className="h-4 w-4" aria-hidden />
            <span>Criar pasta no Drive</span>
          </>
        )}
      </button>
      {status === "error" && errorMessage ? (
        <p
          role="alert"
          className="text-sm text-red-400"
        >
          {errorMessage}
        </p>
      ) : null}
    </div>
  );
}
