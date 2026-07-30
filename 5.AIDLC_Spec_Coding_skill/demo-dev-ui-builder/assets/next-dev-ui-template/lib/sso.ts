export type SsoUser = {
  accountId?: string;
  accountName?: string;
  emailAddress?: string;
};

export type SsoSession = {
  authenticated: boolean;
  user: SsoUser | null;
};

const backendBaseUrl = process.env.SSO_BACKEND_BASE_URL ?? "http://localhost:5002";

export async function getSsoSession(request: Request): Promise<SsoSession> {
  const response = await fetch(`${backendBaseUrl}/sso/me`, {
    cache: "no-store",
    headers: {
      cookie: request.headers.get("cookie") ?? ""
    }
  });

  if (!response.ok) return { authenticated: false, user: null };
  return response.json();
}

export async function unauthorizedIfNoSso(request: Request): Promise<Response | null> {
  const session = await getSsoSession(request);
  if (!session.authenticated) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: { "content-type": "application/json" }
    });
  }
  return null;
}
