import '@testing-library/jest-dom/vitest'

// Provide minimal mocks for APIs that jsdom does not implement by default.
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// @ts-expect-error - expose mock globally for components relying on it
global.ResizeObserver = ResizeObserver
