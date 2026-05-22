/**
 * Clanker Ops - Layout Calculations
 *
 * Adaptive pane proportions based on terminal width.
 * Reader pane is protected; left rail collapses first.
 */

import type { LayoutSpec, LayoutMode } from "./types.js";

// ---------------------------------------------------------------------------
// Layout Calculation
// ---------------------------------------------------------------------------

export function getLayout(terminalWidth: number): LayoutSpec {
  if (terminalWidth >= 120) {
    return { mode: "three-pane", left: 18, center: 46, right: 56 };
  }
  if (terminalWidth >= 100) {
    return { mode: "three-pane", left: 14, center: 40, right: 56 };
  }
  if (terminalWidth >= 80) {
    return { mode: "two-pane", left: 0, center: 32, right: 48 };
  }
  return { mode: "stacked", left: 0, center: 60, right: 60 };
}

// ---------------------------------------------------------------------------
// Pane Dimensions
// ---------------------------------------------------------------------------

export interface PaneDimensions {
  leftWidth: number;
  centerWidth: number;
  rightWidth: number;
  separator: string;
}

export function getPanes(width: number, layout: LayoutSpec): PaneDimensions {
  const { left, center, right } = layout;
  return {
    leftWidth: left,
    centerWidth: center,
    rightWidth: right,
    separator: "│",
  };
}

// ---------------------------------------------------------------------------
// Terminal Capability Detection
// ---------------------------------------------------------------------------

export function supportsTrueColor(): boolean {
  return process.env.COLORTERM === "truecolor" || 
    process.env.TERM?.includes("24bit");
}

export function supportsUnicode(): boolean {
  return !process.env.LC_ALL?.includes("C") && 
    !process.env.LANG?.includes("C");
}