import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AttachmentMenu } from "../AttachmentMenu";


describe("<AttachmentMenu />", () => {
  it("opens the menu and shows Anexar arquivo", async () => {
    const user = userEvent.setup();
    render(
      <AttachmentMenu
        canCreateProject
        onAttachFile={() => undefined}
        onCreateProject={() => undefined}
      />,
    );

    await user.click(screen.getByRole("button", { name: /menu/i }));
    expect(await screen.findByText("Anexar arquivo")).toBeInTheDocument();
    expect(screen.getByText("Agente")).toBeInTheDocument();
  });

  it("hides the Agente submenu when canCreateProject is false", async () => {
    const user = userEvent.setup();
    render(
      <AttachmentMenu
        canCreateProject={false}
        onAttachFile={() => undefined}
        onCreateProject={() => undefined}
      />,
    );

    await user.click(screen.getByRole("button", { name: /menu/i }));
    expect(await screen.findByText("Anexar arquivo")).toBeInTheDocument();
    expect(screen.queryByText("Agente")).not.toBeInTheDocument();
  });

  it("calls onAttachFile when Anexar arquivo is selected", async () => {
    const user = userEvent.setup();
    const onAttachFile = vi.fn();
    render(
      <AttachmentMenu
        canCreateProject
        onAttachFile={onAttachFile}
        onCreateProject={() => undefined}
      />,
    );

    await user.click(screen.getByRole("button", { name: /menu/i }));
    await user.click(await screen.findByText("Anexar arquivo"));
    expect(onAttachFile).toHaveBeenCalledTimes(1);
  });

  it("opens the agente submenu via keyboard and exposes Criar projeto novo", async () => {
    const user = userEvent.setup();
    const onCreate = vi.fn();
    render(
      <AttachmentMenu
        canCreateProject
        onAttachFile={() => undefined}
        onCreateProject={onCreate}
      />,
    );

    await user.click(screen.getByRole("button", { name: /menu/i }));
    await screen.findByText("Anexar arquivo");

    await user.keyboard("{ArrowDown}{ArrowDown}{ArrowRight}");
    const createItem = await screen.findByText("Criar projeto novo");
    await user.keyboard("{Enter}");
    expect(onCreate).toHaveBeenCalledTimes(1);
    expect(createItem).toBeInTheDocument();
  });
});
