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
} from "@ai-router/ui/field";
import { Input } from "@ai-router/ui/input";
import Link from "next/link";
import { useState } from "react";

export function SignUpForm({
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
    const name = formData.get("name") as string;
    const email = formData.get("email") as string;
    const password = formData.get("password") as string;

    if (!name || !email || !password) return;

    setIsLoading(true);
    const { error: signUpError } = await authClient.signUp.email(
      {
        name,
        email,
        password,
      },
      {
        onError: (ctx) => {
          setError(ctx.error?.message ?? "Something went wrong");
        },
      },
    );
    setIsLoading(false);

    if (signUpError) {
      setError(signUpError.message ?? "Failed to create account");
    } else {
      window.location.replace("/auth/sign-in");
    }
  }

  return (
    <div className={cn("flex flex-col gap-6", className)} {...props}>
      <Card className="overflow-hidden p-0">
        <CardContent className="grid p-0 md:grid-cols-2">
          <form className="p-6 md:p-8" onSubmit={onSubmit}>
            <FieldGroup>
              <div className="flex flex-col items-center gap-2 text-center">
                <h1 className="text-2xl font-bold">Create an account</h1>
                <p className="text-muted-foreground text-balance">
                  Enter your details to get started
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
                <FieldLabel htmlFor="name">Name</FieldLabel>
                <Input
                  id="name"
                  name="name"
                  type="text"
                  placeholder="John Doe"
                  required
                  disabled={isLoading}
                  autoComplete="name"
                />
              </Field>
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
                <FieldLabel htmlFor="password">Password</FieldLabel>
                <Input
                  id="password"
                  name="password"
                  type="password"
                  required
                  disabled={isLoading}
                  autoComplete="new-password"
                />
              </Field>
              <Field>
                <Button type="submit" disabled={isLoading}>
                  {isLoading ? "Creating account…" : "Sign up"}
                </Button>
              </Field>
              <FieldDescription className="text-center">
                Already have an account? <Link href="/auth/sign-in">Login</Link>
              </FieldDescription>
            </FieldGroup>
          </form>
          <AuthCardGradient />
        </CardContent>
      </Card>
    </div>
  );
}
