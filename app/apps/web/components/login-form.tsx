"use client";

import { AuthCardGradient } from "@/components/auth-card-gradient";
import { authClient } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { Button } from "@ai-router/ui/button";
import { Card, CardContent } from "@ai-router/ui/card";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
  FieldSeparator,
} from "@ai-router/ui/field";
import { Input } from "@ai-router/ui/input";
import { Tooltip, TooltipContent, TooltipTrigger } from "@ai-router/ui/tooltip";
import Link from "next/link";
import { useState } from "react";

export function LoginForm({
  className,
  ...props
}: React.ComponentProps<"div">) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const form = e.currentTarget;
    const formData = new FormData(form);
    const email = formData.get("email") as string;
    const password = formData.get("password") as string;

    if (!email || !password) return;

    setIsLoading(true);
    const redirectTo =
      typeof window !== "undefined"
        ? (new URLSearchParams(window.location.search).get("redirect") ?? "/")
        : "/";
    const { error: signInError } = await authClient.signIn.email(
      {
        email,
        password,
      },
      {
        onSuccess: () => {
          window.location.replace(redirectTo);
        },
        onError: (ctx) => {
          setError(ctx.error?.message ?? "Something went wrong");
        },
      },
    );
    setIsLoading(false);

    if (signInError) {
      setError(signInError.message ?? "Invalid email or password");
    } else if (typeof window !== "undefined") {
      window.location.replace(redirectTo);
    }
  }

  return (
    <div className={cn("flex flex-col gap-6", className)} {...props}>
      <Card className="overflow-hidden p-0">
        <CardContent className="grid p-0 md:grid-cols-2">
          <form className="p-6 md:p-8" onSubmit={onSubmit}>
            <FieldGroup>
              <div className="flex flex-col items-center gap-2 text-center">
                <h1 className="text-2xl font-bold">Welcome back</h1>
                <p className="text-muted-foreground text-balance">
                  Login to your GeminiMesh account
                </p>
              </div>
              {error && (
                <p
                  className="text-destructive text-center text-sm"
                  role="alert"
                >
                  {error}
                </p>
              )}
              <Field>
                <FieldLabel htmlFor="email">Email</FieldLabel>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  placeholder="m@example.com"
                  required
                  disabled={isLoading}
                  autoComplete="email"
                />
              </Field>
              <Field>
                <div className="flex items-center">
                  <FieldLabel htmlFor="password">Password</FieldLabel>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span className="ml-auto cursor-not-allowed text-sm text-muted-foreground underline-offset-2">
                        Forgot your password?
                      </span>
                    </TooltipTrigger>
                    <TooltipContent>Disabled for now</TooltipContent>
                  </Tooltip>
                </div>
                <Input
                  id="password"
                  name="password"
                  type="password"
                  required
                  disabled={isLoading}
                  autoComplete="current-password"
                />
              </Field>
              <Field>
                <Button type="submit" disabled={isLoading}>
                  {isLoading ? "Signing in…" : "Login"}
                </Button>
              </Field>
              <FieldSeparator className="*:data-[slot=field-separator-content]:bg-card">
                Or continue with
              </FieldSeparator>
              <Field>
                <Button variant="outline" type="button" disabled={isLoading}>
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                    <path
                      d="M12.48 10.92v3.28h7.84c-.24 1.84-.853 3.187-1.787 4.133-1.147 1.147-2.933 2.4-6.053 2.4-4.827 0-8.6-3.893-8.6-8.72s3.773-8.72 8.6-8.72c2.6 0 4.507 1.027 5.907 2.347l2.307-2.307C18.747 1.44 16.133 0 12.48 0 5.867 0 .307 5.387.307 12s5.56 12 12.173 12c3.573 0 6.267-1.173 8.373-3.36 2.16-2.16 2.84-5.213 2.84-7.667 0-.76-.053-1.467-.173-2.053H12.48z"
                      fill="currentColor"
                    />
                  </svg>
                  <span className="sr-only">Login with Google</span>
                </Button>
              </Field>
              <FieldDescription className="text-center">
                Don&apos;t have an account?{" "}
                <Link href="/auth/sign-up">Sign up</Link>
              </FieldDescription>
            </FieldGroup>
          </form>
          <AuthCardGradient />
        </CardContent>
      </Card>
      <FieldDescription className="px-6 text-center">
        By clicking continue, you agree to our{" "}
        <Link href="#" className="underline underline-offset-4">
          Terms of Service
        </Link>{" "}
        and{" "}
        <Link href="#" className="underline underline-offset-4">
          Privacy Policy
        </Link>
        .
      </FieldDescription>
    </div>
  );
}
