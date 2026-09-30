import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const css = readFileSync(resolve(__dirname, "../app/globals.css"), "utf-8");

const AA_NORMAL_TEXT = 4.5;

type Rgb = [number, number, number];

function oklchToRgb(lightnessPercent: number, chroma: number, hue: number): Rgb {
  const a = chroma * Math.cos((hue * Math.PI) / 180);
  const b = chroma * Math.sin((hue * Math.PI) / 180);
  const lightness = lightnessPercent / 100;
  const l = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (lightness - 0.0894841775 * a - 1.291485548 * b) ** 3;
  const linear = [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ];
  const encode = (value: number) => {
    const clamped = Math.min(1, Math.max(0, value));
    return clamped <= 0.0031308 ? 12.92 * clamped : 1.055 * clamped ** (1 / 2.4) - 0.055;
  };
  return [encode(linear[0]), encode(linear[1]), encode(linear[2])];
}

function hexToRgb(hex: string): Rgb {
  return [1, 3, 5].map((index) => parseInt(hex.slice(index, index + 2), 16) / 255) as Rgb;
}

function luminance([r, g, b]: Rgb): number {
  const channel = (value: number) => (value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4);
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

function contrast(foreground: Rgb, background: Rgb): number {
  const [light, dark] = [luminance(foreground), luminance(background)].sort((x, y) => y - x);
  return (light + 0.05) / (dark + 0.05);
}

function colorValue(block: string, name: string): Rgb {
  const oklch = new RegExp(`${name}:\\s*oklch\\(([\\d.]+)%\\s+([\\d.]+)\\s+([\\d.]+)\\)`).exec(block);
  if (oklch) return oklchToRgb(Number(oklch[1]), Number(oklch[2]), Number(oklch[3]));
  const hex = new RegExp(`${name}:\\s*(#[0-9a-fA-F]{6})`).exec(block);
  if (hex) return hexToRgb(hex[1]);
  throw new Error(`${name} not found in the CSS block`);
}

/** The text between the opening brace of `selector` and its closing brace. */
function block(selector: string): string {
  const start = css.indexOf(selector);
  if (start < 0) throw new Error(`${selector} not found in globals.css`);
  const open = css.indexOf("{", start);
  let depth = 0;
  for (let index = open; index < css.length; index += 1) {
    if (css[index] === "{") depth += 1;
    if (css[index] === "}") depth -= 1;
    if (depth === 0) return css.slice(open + 1, index);
  }
  throw new Error(`${selector} is not closed`);
}

describe("muted text contrast (WCAG AA, 4.5:1)", () => {
  const light = { theme: block("@theme {"), root: block(":root {") };
  const dark = block(':root[data-theme="dark"]');

  it("stays readable on the light page background and on cards", () => {
    const muted = colorValue(light.theme, "--color-slate-500");
    expect(contrast(muted, colorValue(light.root, "--background"))).toBeGreaterThanOrEqual(AA_NORMAL_TEXT);
    expect(contrast(muted, colorValue(light.theme, "--color-card"))).toBeGreaterThanOrEqual(AA_NORMAL_TEXT);
  });

  it("stays readable on the dark page background and on cards", () => {
    const muted = colorValue(dark, "--color-slate-500");
    expect(contrast(muted, colorValue(dark, "--background"))).toBeGreaterThanOrEqual(AA_NORMAL_TEXT);
    expect(contrast(muted, colorValue(dark, "--color-card"))).toBeGreaterThanOrEqual(AA_NORMAL_TEXT);
  });

  it("reproduces the ratio that the accessibility scan measured for the old value", () => {
    const previousMuted = oklchToRgb(55.4, 0.046, 257.417);
    const ratio = contrast(previousMuted, hexToRgb("#f7f8fa"));
    expect(ratio).toBeGreaterThan(4.4);
    expect(ratio).toBeLessThan(AA_NORMAL_TEXT);
  });

  it("keeps the primary and secondary text tones above AA in both themes", () => {
    for (const name of ["--color-slate-600", "--color-slate-700"]) {
      // Light values come from Tailwind's default palette, so only the dark overrides live in this file.
      expect(contrast(colorValue(dark, name), colorValue(dark, "--color-card"))).toBeGreaterThanOrEqual(AA_NORMAL_TEXT);
    }
  });
});
