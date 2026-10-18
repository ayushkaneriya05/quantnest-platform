import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Checkbox } from "@/shared/components/ui/checkbox";
import Turnstile from "./Turnstile";
import { requestPublicApi } from "@/shared/services/api";
import { brand } from "./config";
import { usePlatform } from "@/shared/context/platform";
import WorkspaceState from "@/shared/components/WorkspaceState";
import { useNotifications } from "@/shared/hooks/useNotifications";

export default function NewsletterForm() {
  const { notify } = useNotifications();
  const { catalog, loading, error: platformError, refresh } = usePlatform();
  const policyRevision = catalog?.privacy_policy_revision;
  const { pathname, search } = useLocation();
  const confirmation = pathname.includes("/confirmed");
  const confirmationToken = useRef(new URLSearchParams(search).get("token"));
  useEffect(() => {
    const incoming = new URLSearchParams(search).get("token");
    if (incoming) confirmationToken.current = incoming;
  }, [search]);
  const [token, setToken] = useState("");
  const [reset, setReset] = useState(0);
  const [granted, setGranted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const handleVerificationError = useCallback(
    (value) => notify.error(value),
    [notify],
  );
  const confirmNewsletterSubscription = useCallback(async () => {
    if (!confirmationToken.current) {
      setError("This link has no confirmation token. Request a new email.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await requestPublicApi("support/newsletter/confirm/", {
        token: confirmationToken.current,
      });
      setMessage(
        "Your email is confirmed. You can withdraw this choice using the unsubscribe link or account preferences.",
      );
      window.history.replaceState(null, "", pathname);
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }, [pathname]);
  useEffect(() => {
    if (confirmation) confirmNewsletterSubscription();
  }, [confirmation, confirmNewsletterSubscription]);
  async function submitNewsletterRequest(event) {
    event.preventDefault();
    if (busy || !policyRevision) return;
    if (!granted || (brand.turnstile && !token)) {
      notify.warning(
        "Choose to receive updates and complete the verification.",
      );
      return;
    }
    const email = new FormData(event.currentTarget).get("email");
    setBusy(true);
    setError("");
    try {
      await requestPublicApi("support/consent/", {
        email,
        purpose: "marketing",
        granted: true,
        policy_revision: policyRevision,
        turnstile_token: token,
      });
      notify.success("Check your email and confirm the link to subscribe.");
    } catch (failure) {
      notify.error(failure.message);
    } finally {
      setBusy(false);
      setToken("");
      setReset((value) => value + 1);
    }
  }
  if (confirmation)
    return (
      <section className="site-card max-w-2xl">
        {busy && <p role="status">Checking confirmation…</p>}
        {message && <p role="status">{message}</p>}
        {error && (
          <p role="alert" className="text-destructive-text">
            {error}
          </p>
        )}
        {!message && (
          <Button
            onClick={confirmNewsletterSubscription}
            disabled={busy}
            className="mt-5"
          >
            Check again
          </Button>
        )}
      </section>
    );
  return (
    <form
      onSubmit={submitNewsletterRequest}
      className="site-card max-w-2xl space-y-5"
    >
      {!policyRevision && (
        <WorkspaceState
          loading={loading}
          error={
            platformError
              ? "Privacy settings could not load. Please retry."
              : ""
          }
          onRetry={platformError ? refresh : undefined}
        />
      )}
      <label className="block space-y-2 text-sm">
        <span>Email address</span>
        <Input
          type="email"
          name="email"
          autoComplete="email"
          required
          maxLength={254}
        />
      </label>
      <label className="flex cursor-pointer gap-3 text-sm leading-7">
        <Checkbox
          checked={granted}
          onCheckedChange={setGranted}
          className="mt-1"
        />
        <span>
          I want product updates and educational workflow guides. I can
          unsubscribe at any time.
        </span>
      </label>
      <Turnstile
        action="newsletter"
        onToken={setToken}
        onError={handleVerificationError}
        reset={reset}
      />
      <Button disabled={busy || !policyRevision}>
        {busy ? "Sending…" : "Send confirmation email"}
      </Button>
    </form>
  );
}
