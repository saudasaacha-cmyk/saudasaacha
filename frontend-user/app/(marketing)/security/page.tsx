import Link from "next/link";
import type { Metadata } from "next";
import {
  AlertTriangle,
  ArrowRight,
  Banknote,
  Database,
  Eye,
  FileCheck2,
  Fingerprint,
  KeyRound,
  Lock,
  MailWarning,
  Network,
  Server,
  ShieldCheck,
  Snowflake,
  Sparkles,
  UserCheck,
} from "lucide-react";

export const metadata: Metadata = {
  title: "Security & Compliance",
  description:
    "How SaudaSaacha protects your money, your data and your trading account — and the regulatory framework we operate under.",
};

const PILLARS = [
  {
    icon: Banknote,
    title: "Your money",
    body: "Customer funds in a regulated escrow account, separate from the broker's working capital. Withdrawals only to the bank account that funded the deposit.",
  },
  {
    icon: Database,
    title: "Your data",
    body: "Data residency in AWS Mumbai (ap-south-1). DPDP-compliant data handling. You can export everything and delete your account from the dashboard.",
  },
  {
    icon: Lock,
    title: "Your access",
    body: "Refresh-token allowlist in Redis, TOTP-based 2FA, IP-allowlist option for high-value accounts. Lost device — one click revokes everything.",
  },
];

const CONTROLS = [
  { icon: KeyRound,    title: "TOTP-based 2FA",       body: "Google Authenticator / Authy / 1Password — your call. Backup recovery codes generated at enrolment." },
  { icon: Fingerprint, title: "Biometric mobile login", body: "Face ID / Touch ID / Android biometrics. Token cache wiped on biometric failure threshold." },
  { icon: UserCheck,   title: "Per-device sessions",  body: "Every login is a separate session you can revoke individually. See location, device and last-seen time." },
  { icon: Eye,         title: "Login alerts",         body: "Email + push on every new-device login. Anomaly heuristics flag unusual hours / unusual IP." },
  { icon: MailWarning, title: "Withdrawal email lock", body: "Every withdrawal triggers an email + push. 1-hour cooling-off window for first-time large amounts." },
  { icon: Lock,        title: "Hardware-token (opt-in)", body: "Optional FIDO2 / WebAuthn enrolment for users who carry a YubiKey." },
];

const INFRA = [
  { icon: Server,    title: "AWS Mumbai (ap-south-1)", body: "Primary region for all India-resident data. Singapore region kept hot as DR for global-only segments (forex, crypto)." },
  { icon: Network,   title: "TLS 1.3 + HSTS preload",  body: "Modern cipher suites only. HSTS preload across all sub-domains. Cert pinning on the mobile app." },
  { icon: Database,  title: "MongoDB + Redis cluster", body: "Replica set with daily snapshots, append-only ledger, hourly reconciliation across replicas." },
  { icon: ShieldCheck, title: "WAF + rate limiting",  body: "CloudFront + AWS WAF in front of every public endpoint. Burst limits per IP, per user, per route." },
  { icon: Snowflake, title: "Cold-wallet crypto",     body: "95% of crypto holdings in cold storage. Hot wallet refilled in chunks, multi-sig withdrawal." },
  { icon: FileCheck2, title: "ISO 27001 in progress", body: "Audit kick-off Q1 2026. SOC 2 Type I scoping in parallel. Compliance roadmap published quarterly." },
];

const REG_POINTS = [
  "SEBI-aligned operating model · stock-broker membership in progress for NSE / BSE / MCX",
  "Funds segregated in a SEBI-recognised settlement bank account",
  "Statutory contract notes generated nightly, signed and emailed within T+1",
  "Grievance redressal published — escalation path to SEBI SCORES in the footer",
  "AML / KYC framework aligned with PMLA + RBI Master Direction on KYC",
  "DPDP Act compliance — Indian data principal rights honoured in the dashboard",
];

const RESPONSIBLE_DISCLOSURE = [
  "Email security@saudasaacha.com with a clear write-up and steps to reproduce.",
  "Encrypt sensitive details with our PGP key (linked from the email autoresponder).",
  "We acknowledge within 48 hours and triage within 7 days.",
  "Eligible reports earn a bounty — paid in INR via UPI or NEFT, your choice.",
  "Public credit on the security wall of fame after the fix is shipped (if you want it).",
];

export default function SecurityPage() {
  return (
    <>
      <section className="relative overflow-hidden border-b border-border">
        <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 bg-gradient-to-b from-primary/8 via-background to-background" />
        <div className="mx-auto max-w-5xl px-4 py-20 text-center sm:px-6 sm:py-24 lg:px-8">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-semibold text-primary">
            <ShieldCheck className="size-3" /> Security &amp; compliance
          </span>
          <h1 className="mt-5 text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
            Your money is yours.
            <br />
            <span className="mp-gradient-text">We just hold the door.</span>
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            We operate under SEBI's framework for stock brokers and India's
            DPDP Act for data. The systems below are how we keep both
            promises — your capital and your information.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24 lg:px-8">
        <div className="grid gap-5 lg:grid-cols-3">
          {PILLARS.map((p) => {
            const Icon = p.icon;
            return (
              <div key={p.title} className="rounded-2xl border border-border/40 bg-card/60 p-7">
                <div className="grid size-12 place-items-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/20">
                  <Icon className="size-6" />
                </div>
                <h2 className="mt-5 text-lg font-bold tracking-tight">{p.title}</h2>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{p.body}</p>
              </div>
            );
          })}
        </div>
      </section>

      <section className="border-y border-border/40 bg-muted/20">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24 lg:px-8">
          <div className="max-w-2xl">
            <span className="text-xs font-semibold uppercase tracking-wider text-primary">Account controls</span>
            <h2 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Six layers between an attacker and your trades.</h2>
            <p className="mt-3 text-muted-foreground">
              Every one is optional except the first two. We strongly recommend
              all six for any account with more than ₹5 lakh on it.
            </p>
          </div>
          <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {CONTROLS.map((c) => {
              const Icon = c.icon;
              return (
                <div key={c.title} className="rounded-2xl border border-border/40 bg-card/60 p-6">
                  <div className="grid size-10 place-items-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/20">
                    <Icon className="size-5" />
                  </div>
                  <h3 className="mt-4 text-base font-semibold">{c.title}</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{c.body}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24 lg:px-8">
        <div className="grid items-start gap-12 lg:grid-cols-2">
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-primary">Infrastructure</span>
            <h2 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Boring, hardened, audited.</h2>
            <p className="mt-4 text-muted-foreground">
              We optimise for "no surprises". Standard AWS primitives, mandatory
              code review, branch-protection rules on every repo, daily backups
              with restore drills. The systems list below is exhaustive — not
              marketing-friendly.
            </p>
            <Link href="/contact" className="mt-6 inline-flex items-center gap-1.5 text-sm font-semibold text-primary hover:underline">
              Ask a security question <ArrowRight className="size-3.5" />
            </Link>
          </div>
          <div className="grid gap-4">
            {INFRA.map((c) => {
              const Icon = c.icon;
              return (
                <div key={c.title} className="rounded-2xl border border-border/40 bg-card/60 p-5">
                  <div className="flex items-start gap-3">
                    <div className="grid size-10 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/20">
                      <Icon className="size-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold">{c.title}</h3>
                      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{c.body}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="border-y border-border/40 bg-card/40">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24 lg:px-8">
          <div className="grid items-start gap-12 lg:grid-cols-2">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-primary">Regulatory posture</span>
              <h2 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">We're regulated. Here's the actual list.</h2>
            </div>
            <ul className="space-y-3">
              {REG_POINTS.map((r) => (
                <li key={r} className="flex items-start gap-3 rounded-xl border border-border bg-background p-4">
                  <FileCheck2 className="mt-0.5 size-4 shrink-0 text-primary" />
                  <span className="text-sm text-muted-foreground">{r}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24 lg:px-8">
        <div className="grid items-start gap-12 lg:grid-cols-2">
          <div>
            <AlertTriangle className="size-9 text-primary" />
            <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">Responsible disclosure</h2>
            <p className="mt-3 text-muted-foreground">
              If you've found something — a way to bypass an auth check, a
              ledger inconsistency, a CSRF gap — please tell us before you tell
              anyone else. We pay for it, we credit you, and we never sue
              researchers acting in good faith.
            </p>
            <Link href="mailto:security@saudasaacha.com" className="mt-5 inline-flex h-11 items-center gap-2 rounded-full bg-primary px-6 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/25 hover:bg-primary/90">
              security@saudasaacha.com <ArrowRight className="size-4" />
            </Link>
          </div>
          <ol className="space-y-3">
            {RESPONSIBLE_DISCLOSURE.map((r, i) => (
              <li key={r} className="flex items-start gap-3 rounded-xl border border-border/40 bg-card/60 p-4">
                <span className="grid size-7 shrink-0 place-items-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                  {i + 1}
                </span>
                <span className="text-sm text-muted-foreground">{r}</span>
              </li>
            ))}
          </ol>
        </div>
      </section>
    </>
  );
}
