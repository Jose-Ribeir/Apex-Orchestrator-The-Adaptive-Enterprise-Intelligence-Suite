import { config as reactConfig } from "@ai-router/eslint-config/react-internal";
import { defineConfig, globalIgnores } from "eslint/config";

const eslintConfig = defineConfig([
  ...reactConfig,
  globalIgnores(["dist/**", "node_modules/**"]),
]);

export default eslintConfig;
