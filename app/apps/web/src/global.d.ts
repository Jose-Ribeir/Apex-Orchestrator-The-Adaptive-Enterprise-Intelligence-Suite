export {};

declare global {
  interface Window {
    __API_BASE_URL__?: string;
    __APP_URL__?: string;
  }
}
