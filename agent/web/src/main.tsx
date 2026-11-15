import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { App } from "./App";
import { AsyncActivityIndicator } from "./components/AsyncActivityIndicator";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary><App /><AsyncActivityIndicator /></ErrorBoundary>
  </StrictMode>,
);
