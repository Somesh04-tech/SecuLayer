import "./styles/tokens.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { applyTextSize, readTextSize } from "./features/shell/textSize";

// Apply the remembered text size before the first paint, so the page doesn't jump.
applyTextSize(readTextSize());

const root = document.getElementById("root");
if (root) {
  createRoot(root).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}
