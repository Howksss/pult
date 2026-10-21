import "./App.css";
import { StatusBadge } from "./components/StatusBadge";

export default function App() {
  return (
    <main>
      <h1>Pult</h1>
      <p>
        <StatusBadge status="ok" /> <StatusBadge status="warn" /> <StatusBadge status="fail" />{" "}
        <StatusBadge status="unknown" />
      </p>
    </main>
  );
}
