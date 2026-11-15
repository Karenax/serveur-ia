import { Component, type ReactNode } from "react";

export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (this.state.failed) return <main role="alert" style={{ padding: 32 }}>
      <h1>Un écran ne peut pas être affiché</h1>
      <p>Recharge l’application pour retrouver tes projets enregistrés.</p>
      <button onClick={() => window.location.reload()}>Recharger</button>
    </main>;
    return this.props.children;
  }
}
