/**
 * Injects runtime env into window so the client can read it.
 */
export function EnvScript() {
  const apiUrl = process.env.API_URL ?? "";
  return (
    <script
      dangerouslySetInnerHTML={{
        __html: `window.__API_BASE_URL__=${JSON.stringify(apiUrl)}`,
      }}
    />
  );
}
