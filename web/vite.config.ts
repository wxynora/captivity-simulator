import fs from "node:fs";
import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";


function readNames() {
  const root = path.resolve(__dirname, "..");
  const paths = [path.join(root, "config", "local.json"), path.join(root, "config", "default.json")];
  for (const file of paths) {
    try {
      const parsed = JSON.parse(fs.readFileSync(file, "utf8"));
      if (parsed?.actors) return parsed.actors;
    } catch {
      // Fall through to the checked-in placeholders.
    }
  }
  return { user: "{user}", assistant: "{assistant}" };
}


const names = readNames();
const escaped = (value: unknown, fallback: string) => JSON.stringify(String(value || fallback)).slice(1, -1);


export default defineConfig({
  plugins: [
    react(),
    {
      name: "captivity-actor-placeholders",
      enforce: "pre",
      transform(code, id) {
        if (!id.includes("/src/") || !/\.[jt]sx?$/.test(id)) return null;
        return code
          .replaceAll("{user}", escaped(names.user, "{user}"))
          .replaceAll("{assistant}", escaped(names.assistant, "{assistant}"));
      },
    },
  ],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:5058",
    },
  },
});
