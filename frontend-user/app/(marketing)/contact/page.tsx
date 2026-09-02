"use client";

import { useState } from "react";
import { CheckCircle2, Mail } from "lucide-react";
import {
  MpButton,
  MpCard,
  MpPageHero,
  MpSection,
} from "@/components/marketing/mp-ui";

const CHANNELS = [
  {
    label: "Support",
    email: "support@saudasaacha.com",
    note: "for account, payout, and platform issues. Have your account ID ready.",
  },
  {
    label: "Affiliates & partnerships",
    email: "partners@saudasaacha.com",
    note: "for referrals, partnerships, and volume deals.",
  },
  {
    label: "Press / general",
    email: "hello@saudasaacha.com",
    note: "for everything else.",
  },
];

const TOPICS = ["Support", "Billing", "Affiliates", "Other"];

const FIELD =
  "h-11 w-full rounded-xl border border-mp-border bg-mp-surface px-3.5 text-sm text-mp-text placeholder:text-mp-text-mut/70 focus:border-mp-primary focus:outline-none focus:ring-2 focus:ring-mp-primary/20";

export default function ContactPage() {
  const [sent, setSent] = useState(false);

  return (
    <>
      <MpPageHero
        eyebrow="Contact"
        title="Get in touch."
        lead="Quick questions are usually answered fastest in the Help Center and FAQ. For everything else, here is how to reach us."
      />

      <MpSection>
        <div className="grid gap-10 lg:grid-cols-2">
          {/* Reach us */}
          <div>
            <h2 className="font-display text-2xl font-bold text-mp-text">Reach us</h2>
            <div className="mt-6 flex flex-col gap-4">
              {CHANNELS.map((c) => (
                <MpCard key={c.email} hover={false} className="flex items-start gap-4">
                  <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-mp-primary/10 text-mp-primary">
                    <Mail className="size-5" />
                  </span>
                  <div>
                    <div className="text-sm font-semibold text-mp-text">
                      {c.label}
                    </div>
                    <a
                      href={`mailto:${c.email}`}
                      className="mp-num text-sm text-mp-primary hover:text-mp-primary-2"
                    >
                      {c.email}
                    </a>
                    <p className="mt-1 text-sm leading-[1.5] text-mp-text-mut">
                      {c.note}
                    </p>
                  </div>
                </MpCard>
              ))}
              <p className="text-sm leading-[1.6] text-mp-text-mut">
                <span className="font-semibold text-mp-text">Hours:</span>{" "}
                Monday to Saturday, IST hours. We answer in English and Hindi.
              </p>
            </div>
          </div>

          {/* Form */}
          <div>
            <h2 className="font-display text-2xl font-bold text-mp-text">
              Send a message
            </h2>
            {sent ? (
              <MpCard hover={false} className="mt-6 flex items-center gap-4">
                <CheckCircle2 className="size-6 shrink-0 text-mp-primary" />
                <p className="text-sm text-mp-text">
                  Thanks. We have your message and will get back to you soon.
                </p>
              </MpCard>
            ) : (
              <form
                className="mt-6 flex flex-col gap-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  setSent(true);
                }}
              >
                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="flex flex-col gap-1.5">
                    <span className="text-sm font-medium text-mp-text">Name</span>
                    <input className={FIELD} type="text" name="name" required />
                  </label>
                  <label className="flex flex-col gap-1.5">
                    <span className="text-sm font-medium text-mp-text">Email</span>
                    <input className={FIELD} type="email" name="email" required />
                  </label>
                </div>
                <label className="flex flex-col gap-1.5">
                  <span className="text-sm font-medium text-mp-text">
                    Account ID{" "}
                    <span className="font-normal text-mp-text-mut">(optional)</span>
                  </span>
                  <input className={FIELD} type="text" name="accountId" />
                </label>
                <label className="flex flex-col gap-1.5">
                  <span className="text-sm font-medium text-mp-text">Topic</span>
                  <select className={FIELD} name="topic" defaultValue="Support">
                    {TOPICS.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex flex-col gap-1.5">
                  <span className="text-sm font-medium text-mp-text">Message</span>
                  <textarea
                    className="min-h-[120px] w-full rounded-xl border border-mp-border bg-mp-surface px-3.5 py-3 text-sm text-mp-text placeholder:text-mp-text-mut/70 focus:border-mp-primary focus:outline-none focus:ring-2 focus:ring-mp-primary/20"
                    name="message"
                    required
                  />
                </label>
                <MpButton type="submit" className="self-start">
                  Send message
                </MpButton>
                <p className="text-xs leading-[1.6] text-mp-text-mut">
                  We usually reply within a day. For anything time-sensitive
                  about a live trade, email support directly with
                  &ldquo;URGENT&rdquo; in the subject.
                </p>
              </form>
            )}
          </div>
        </div>

        {/* Registered office */}
        <div className="mt-12 border-t border-mp-border pt-8">
          <p className="text-sm text-mp-text-mut">
            <span className="font-semibold text-mp-text">Registered office:</span>{" "}
            Based in India. Full legal entity details are published in our Terms
            &amp; Conditions.
          </p>
        </div>
      </MpSection>
    </>
  );
}
