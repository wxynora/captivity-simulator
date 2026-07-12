import { CaptivitySimulatorGameTab } from "./CaptivitySimulator";


export function App() {
  return (
    <CaptivitySimulatorGameTab
      onBack={() => {
        if (window.history.length > 1) window.history.back();
      }}
    />
  );
}
