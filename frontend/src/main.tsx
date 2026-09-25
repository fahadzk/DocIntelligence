import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles/global.css";
import "./styles/search.css";
import "./styles/pipeline.css";

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
