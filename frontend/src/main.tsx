import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { connect } from "./api";
import { App } from "./App";
import "./styles.css";

connect();
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
