import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
  scale: vi.fn(), clearRect: vi.fn(), fillRect: vi.fn(), beginPath: vi.fn(),
  moveTo: vi.fn(), lineTo: vi.fn(), stroke: vi.fn(), setLineDash: vi.fn(),
  closePath: vi.fn(), fill: vi.fn(),
})) as never;
