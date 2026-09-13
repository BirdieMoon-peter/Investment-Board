import '@testing-library/jest-dom/vitest'

// jsdom does not implement ResizeObserver; stub it for components that need it
if (typeof globalThis.ResizeObserver === 'undefined') {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof globalThis.ResizeObserver
}

// jsdom has no layout. Fluent's Tabster considers a zero-size body / null
// offsetParent a hidden document, so model visibility while retaining hidden
// ancestor semantics. Actual geometry and keyboard flows are browser-verified.
Object.defineProperty(document.body, 'getBoundingClientRect', {
  configurable: true,
  value: () => new DOMRect(0, 0, 1024, 768),
})
Object.defineProperty(HTMLElement.prototype, 'offsetParent', {
  configurable: true,
  get(this: HTMLElement) {
    if (!this.isConnected || this === document.body) return null
    for (let element: HTMLElement | null = this; element; element = element.parentElement) {
      if (element.hidden || getComputedStyle(element).display === 'none') return null
    }
    if (getComputedStyle(this).position === 'fixed') return null
    return this.parentElement ?? document.body
  },
})
