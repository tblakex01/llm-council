/**
 * Vitest setup file for React testing.
 */

import '@testing-library/jest-dom';

// Mock window.scrollIntoView
Element.prototype.scrollIntoView = vi.fn();

// Mock fetch globally
global.fetch = vi.fn();

// Reset mocks between tests
beforeEach(() => {
  vi.clearAllMocks();
});
