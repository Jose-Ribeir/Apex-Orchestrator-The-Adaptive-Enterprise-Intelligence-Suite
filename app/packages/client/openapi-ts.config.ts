import { defaultPlugins, defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  input: "./openapi.json",
  output: "src",
  plugins: [
    ...defaultPlugins,
    "@hey-api/schemas",
    {
      name: "@hey-api/client-axios",
      runtimeConfigPath: "./src/client.config.ts",
    },
    "@tanstack/react-query",
    "@hey-api/transformers",
    { enums: "javascript", name: "@hey-api/typescript" },
    { name: "@hey-api/sdk", transformer: true },
  ],
});
