import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

/** Catches render errors anywhere in the tree so a bug in one page never produces a blank white screen. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error("LifeRoom crashed:", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: "100vh",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 12,
            padding: 24,
            textAlign: "center",
            fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
          }}
        >
          <h1 style={{ fontSize: 20, fontWeight: 700, color: "#0B1220" }}>Something went wrong</h1>
          <p style={{ color: "#475569", maxWidth: 360 }}>
            LifeRoom hit an unexpected error. Try reloading the page - your household data is safe on the server.
          </p>
          <button
            onClick={() => window.location.assign("/")}
            style={{
              background: "#2563EB",
              color: "#fff",
              border: "none",
              padding: "10px 18px",
              borderRadius: 10,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Back to home
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
