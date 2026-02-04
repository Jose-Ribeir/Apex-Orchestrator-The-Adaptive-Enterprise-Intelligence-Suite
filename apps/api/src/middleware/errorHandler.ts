import { Request, Response, NextFunction } from "express";
import { AppError } from "../lib/errors";
import { env } from "../config/env";

export function errorHandler(
  err: Error,
  _req: Request,
  res: Response,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _next: NextFunction,
): void {
  if (err instanceof AppError) {
    res.status(err.statusCode).json({
      error: err.message,
      code: err.code,
      ...(err instanceof Error &&
        "details" in err && {
          details: (err as { details?: unknown }).details,
        }),
    });
    return;
  }

  const statusCode = 500;
  const message =
    env.nodeEnv === "production" ? "Internal server error" : err.message;

  if (env.nodeEnv !== "production") {
    console.error(err);
  }

  res.status(statusCode).json({
    error: message,
    code: "INTERNAL_ERROR",
  });
}
