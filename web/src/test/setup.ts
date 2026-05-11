import "@testing-library/jest-dom/vitest";

class MockIntersectionObserver implements IntersectionObserver {
  readonly root = null;
  readonly rootMargin = "";
  readonly thresholds = [0];

  disconnect(): void {}

  observe(): void {}

  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }

  unobserve(): void {}
}

if (!("IntersectionObserver" in globalThis)) {
  globalThis.IntersectionObserver =
    MockIntersectionObserver as typeof globalThis.IntersectionObserver;
}
