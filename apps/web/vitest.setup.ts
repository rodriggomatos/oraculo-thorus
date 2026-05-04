import "@testing-library/jest-dom/vitest";


type GlobalWithObserver = typeof globalThis & {
  ResizeObserver?: new (...args: unknown[]) => {
    observe: () => void;
    unobserve: () => void;
    disconnect: () => void;
  };
};


const g = globalThis as GlobalWithObserver;
if (typeof g.ResizeObserver === "undefined") {
  class ResizeObserverPolyfill {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
  }
  g.ResizeObserver = ResizeObserverPolyfill as unknown as typeof g.ResizeObserver;
}


type ElementWithPointer = Element & {
  hasPointerCapture?: () => boolean;
  releasePointerCapture?: () => void;
  setPointerCapture?: () => void;
  scrollIntoView?: () => void;
};


if (typeof Element !== "undefined") {
  const proto = Element.prototype as ElementWithPointer;
  if (!proto.scrollIntoView) {
    proto.scrollIntoView = function () {};
  }
  if (!proto.hasPointerCapture) {
    proto.hasPointerCapture = (): boolean => false;
    proto.releasePointerCapture = (): void => {};
    proto.setPointerCapture = (): void => {};
  }
}
