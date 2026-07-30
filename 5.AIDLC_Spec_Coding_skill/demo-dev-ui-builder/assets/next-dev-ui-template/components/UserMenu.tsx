"use client";

import { LogIn, LogOut } from "lucide-react";
import { useEffect, useState } from "react";
import type { SsoSession } from "@/lib/sso";

export function UserMenu() {
  const [session, setSession] = useState<SsoSession | null>(null);

  useEffect(() => {
    fetch("/api/sso/me", { cache: "no-store" })
      .then((response) => response.json())
      .then(setSession)
      .catch(() => setSession({ authenticated: false, user: null }));
  }, []);

  if (!session) {
    return <span className="user-menu">Checking session</span>;
  }

  if (!session.authenticated) {
    return (
      <a className="button-link" href={process.env.NEXT_PUBLIC_SSO_LOGIN_PATH ?? "/sso/login"}>
        <LogIn size={16} /> Sign in
      </a>
    );
  }

  return (
    <div className="user-menu">
      <span>{session.user?.emailAddress ?? session.user?.accountName ?? "SSO user"}</span>
      <a className="button-link" href={process.env.NEXT_PUBLIC_SSO_LOGOUT_PATH ?? "/sso/logout"}>
        <LogOut size={16} /> Sign out
      </a>
    </div>
  );
}
