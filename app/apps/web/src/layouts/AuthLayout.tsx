import { Outlet } from "react-router-dom";

export function AuthLayout() {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-6 bg-muted/30 p-6 md:p-10">
      <div className="flex w-full max-w-2xl flex-col gap-6">
        <Outlet />
      </div>
    </div>
  );
}
