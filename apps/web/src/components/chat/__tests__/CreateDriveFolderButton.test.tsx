import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";


vi.mock("@/features/create-project/mock", () => ({
  createDriveFolder: vi.fn(),
}));


import { createDriveFolder } from "@/features/create-project/mock";
import { CreateDriveFolderButton } from "../CreateDriveFolderButton";


describe("<CreateDriveFolderButton />", () => {
  beforeEach(() => {
    vi.mocked(createDriveFolder).mockReset();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  it("renders the create button when no folder yet", () => {
    render(<CreateDriveFolderButton projectId="p-1" />);
    expect(screen.getByRole("button", { name: /Criar pasta no Drive/i })).toBeInTheDocument();
  });

  it("starts in success state when initialFolderId is provided", () => {
    render(<CreateDriveFolderButton projectId="p-1" initialFolderId="folder-123" />);
    const link = screen.getByRole("link", { name: /Pasta criada — abrir no Drive/i });
    expect(link).toHaveAttribute(
      "href",
      "https://drive.google.com/drive/folders/folder-123",
    );
  });

  it("transitions idle → loading → success and shows the Drive link", async () => {
    let resolver: ((v: {
      folderId: string;
      folderUrl: string;
      folderName: string;
    }) => void) | undefined;
    vi.mocked(createDriveFolder).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolver = resolve;
        }),
    );

    const user = userEvent.setup();
    render(<CreateDriveFolderButton projectId="p-1" />);
    const button = screen.getByRole("button", { name: /Criar pasta no Drive/i });
    await act(async () => {
      await user.click(button);
    });

    expect(screen.getByRole("button", { name: /Criando pasta no Drive/i })).toHaveAttribute(
      "aria-busy",
      "true",
    );

    await act(async () => {
      resolver?.({
        folderId: "folder-456",
        folderUrl: "https://drive.google.com/drive/folders/folder-456",
        folderName: "26032 - X",
      });
    });

    await waitFor(() =>
      expect(screen.getByRole("link", { name: /Pasta criada — abrir no Drive/i })).toBeInTheDocument(),
    );
    expect(screen.getByRole("link", { name: /Pasta criada/i })).toHaveAttribute(
      "href",
      "https://drive.google.com/drive/folders/folder-456",
    );
  });

  it("renders the backend error message in red on failure", async () => {
    vi.mocked(createDriveFolder).mockRejectedValueOnce(
      new Error(
        "Pasta '26032 - X' já existe no Drive. Verifique se não foi criada manualmente.",
      ),
    );
    const user = userEvent.setup();
    render(<CreateDriveFolderButton projectId="p-1" />);
    await act(async () => {
      await user.click(screen.getByRole("button", { name: /Criar pasta no Drive/i }));
    });
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("já existe no Drive");
  });

  it("ignores extra clicks while loading", async () => {
    let resolver: ((v: unknown) => void) | undefined;
    vi.mocked(createDriveFolder).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolver = resolve as (v: unknown) => void;
        }),
    );
    const user = userEvent.setup();
    render(<CreateDriveFolderButton projectId="p-1" />);
    const button = screen.getByRole("button", { name: /Criar pasta no Drive/i });
    await act(async () => {
      await user.click(button);
    });
    await act(async () => {
      await user.click(screen.getByRole("button", { name: /Criando pasta no Drive/i }));
    });
    expect(createDriveFolder).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolver?.({
        folderId: "f",
        folderUrl: "https://drive.google.com/drive/folders/f",
        folderName: "n",
      });
    });
  });
});
