import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { migrateAppStorage } from "./appStorage";
import "./styles.css";
import "./gpost.css";
import "./validation.css";

migrateAppStorage();

createRoot(document.getElementById("root")!).render(
  <StrictMode><App /></StrictMode>,
);
