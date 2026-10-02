"use client";

import { Component, type ReactNode } from "react";

/** Contains a failing widget so one broken component never takes down the page. */
export class ErrorBoundary extends Component<{ children: ReactNode; fallback?: ReactNode; label?: string }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch(error: Error) {
    console.warn(`[${this.props.label || "widget"}] failed:`, error.message);
  }
  render() {
    if (this.state.failed)
      return (
        this.props.fallback ?? (
          <div className="rounded-2xl border border-dashed border-frost bg-white p-6 text-center text-sm text-ink-soft">
            This {this.props.label || "section"} could not be displayed.{" "}
            <button className="text-cyan-deep underline" onClick={() => this.setState({ failed: false })}>
              Try again
            </button>
          </div>
        )
      );
    return this.props.children;
  }
}
