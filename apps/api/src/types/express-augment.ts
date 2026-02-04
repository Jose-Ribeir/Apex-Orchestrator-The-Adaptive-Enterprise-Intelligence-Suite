import type { AuthSession } from "../middleware/requireAuth";

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace -- Express types use namespace for Request augmentation
  namespace Express {
    interface Request {
      session?: AuthSession;
      user?: AuthSession["user"];
    }
  }
}

export {};
