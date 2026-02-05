import { validate as isValidUuid } from "uuid";
import { ValidationError } from "./errors";

/** Normalize Express param to string (Express can give string | string[]). */
export function paramId(value: string | string[] | undefined): string {
  if (Array.isArray(value)) return value[0] ?? "";
  return value ?? "";
}

/** Like paramId but validates UUID; throws ValidationError if invalid (e.g. literal "{id}"). */
export function paramUuid(value: string | string[] | undefined): string {
  const id = paramId(value);
  if (!id || !isValidUuid(id)) {
    throw new ValidationError(
      id ? `Invalid UUID: ${id}` : "Missing or invalid id parameter",
    );
  }
  return id;
}
