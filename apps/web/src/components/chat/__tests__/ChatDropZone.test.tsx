import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { ChatDropZone, validateFile } from "../ChatDropZone";


function makeFile(name: string, sizeBytes = 1024, type = "application/octet-stream"): File {
  const file = new File(["x".repeat(Math.min(sizeBytes, 1024))], name, { type });
  Object.defineProperty(file, "size", { value: sizeBytes });
  return file;
}


describe("validateFile", () => {
  it("accepts a .gsheet file under the size limit", () => {
    const file = makeFile("orcamento.gsheet", 1024);
    expect(validateFile(file)).toBeNull();
  });

  it("rejects non-.gsheet extensions with a clear message", () => {
    const file = makeFile("documento.pdf");
    expect(validateFile(file)).toMatch(/inválido/i);
  });

  it("rejects files larger than 10MB", () => {
    const oversize = 11 * 1024 * 1024;
    const file = makeFile("muito-grande.gsheet", oversize);
    expect(validateFile(file)).toMatch(/10MB/);
  });
});


describe("<ChatDropZone />", () => {
  it("opens the file picker when registerOpenPicker is invoked", () => {
    const opens: Array<() => void> = [];
    render(
      <ChatDropZone
        active
        onFileAccepted={() => undefined}
        registerOpenPicker={(open) => opens.push(open)}
      >
        <div>child</div>
      </ChatDropZone>,
    );

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const clickSpy = vi.spyOn(input, "click");

    expect(opens.length).toBeGreaterThan(0);
    opens[opens.length - 1]();

    expect(clickSpy).toHaveBeenCalledTimes(1);
  });

  it("shows the pending file preview when a valid file is dropped, then sends on click", () => {
    const onAccept = vi.fn();
    const { container } = render(
      <ChatDropZone active onFileAccepted={onAccept}>
        <div>child</div>
      </ChatDropZone>,
    );

    const dropTarget = container.firstChild as HTMLElement;
    const file = makeFile("orcamento.gsheet", 2048);

    fireEvent.drop(dropTarget, {
      dataTransfer: { files: [file], types: ["Files"] },
    });

    expect(screen.getByText("orcamento.gsheet")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    expect(onAccept).toHaveBeenCalledWith(file);
  });

  it("shows an error when an invalid file is dropped", () => {
    const onAccept = vi.fn();
    const onError = vi.fn();
    const { container } = render(
      <ChatDropZone active onFileAccepted={onAccept} onError={onError}>
        <div>child</div>
      </ChatDropZone>,
    );

    const dropTarget = container.firstChild as HTMLElement;
    const file = makeFile("texto.txt");

    fireEvent.drop(dropTarget, {
      dataTransfer: { files: [file], types: ["Files"] },
    });

    expect(onAccept).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledWith(expect.stringMatching(/inválido/i));
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("does not respond to drop when active=false", () => {
    const onAccept = vi.fn();
    const { container } = render(
      <ChatDropZone active={false} onFileAccepted={onAccept}>
        <div>child</div>
      </ChatDropZone>,
    );

    const dropTarget = container.firstChild as HTMLElement;
    fireEvent.drop(dropTarget, {
      dataTransfer: { files: [makeFile("ok.gsheet")], types: ["Files"] },
    });

    expect(onAccept).not.toHaveBeenCalled();
  });
});
