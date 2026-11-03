"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { Send, Users, Link2 } from "lucide-react";
import { NotificationsAPI } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { PageHeader } from "@/components/common/PageHeader";
import { RecipientPicker, type Recipient } from "@/components/notifications/RecipientPicker";

const LEVELS = [
  { k: "INFO", label: "Info", tone: "border-blue-500/40 text-blue-500" },
  { k: "SUCCESS", label: "Success", tone: "border-emerald-500/40 text-emerald-500" },
  { k: "WARNING", label: "Warning", tone: "border-amber-500/40 text-amber-500" },
  { k: "DANGER", label: "Alert", tone: "border-destructive/40 text-destructive" },
];

export default function SendNotificationPage() {
  const [title, setTitle] = useState("");
  const [message, setMessage] = useState("");
  const [link, setLink] = useState("");
  const [level, setLevel] = useState("INFO");
  // `null` = the whole pool, which is what this page did before and what
  // leaving `user_ids` out of the request still means to the server.
  const [picked, setPicked] = useState<Recipient[] | null>(null);

  // How many users this actor's broadcast reaches (their own pool).
  const { data: rec } = useQuery({
    queryKey: ["admin", "broadcast-recipients"],
    queryFn: () => NotificationsAPI.broadcastRecipients(),
  });
  const count = rec?.count ?? 0;

  const mut = useMutation({
    mutationFn: () =>
      NotificationsAPI.broadcast({
        title: title.trim(),
        message: message.trim(),
        link: link.trim() || undefined,
        level,
        ...(picked ? { user_ids: picked.map((r) => r.id) } : {}),
      }),
    onSuccess: (r) => {
      toast.success(`Sent to ${r.count} user${r.count === 1 ? "" : "s"}`);
      setTitle("");
      setMessage("");
      setLink("");
      setLevel("INFO");
      setPicked(null);
    },
    onError: (e: any) => toast.error(e?.message || "Failed to send"),
  });

  const targets = picked === null ? count : picked.length;
  const canSend =
    title.trim().length > 0 && message.trim().length > 0 && targets > 0 && !mut.isPending;

  function submit() {
    if (!canSend) return;
    // Name the recipients when there are few enough to read. "Send to 2
    // users?" is not a check an admin can fail safely; the names are.
    const who =
      picked === null
        ? `all ${count} of your users`
        : picked.length <= 5
          ? picked.map((r) => r.label).join(", ")
          : `${picked.length} selected users`;
    if (!window.confirm(`Send this notification to ${who}? This cannot be undone.`))
      return;
    mut.mutate();
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Send Notification"
        description="Message everyone in your pool, or pick the users it should reach."
      />

      <Card className="max-w-2xl">
        <CardContent className="space-y-5 p-5">
          {/* Who it goes to */}
          <div className="space-y-2.5 rounded-md border border-border bg-muted/30 p-3">
            <div className="flex items-center gap-2 text-sm">
              <Users className="size-4 text-primary" />
              <span className="font-medium">Recipients</span>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setPicked(null)}
                className={`rounded-md border px-3 py-1.5 text-xs font-medium ${
                  picked === null
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border text-muted-foreground hover:text-foreground"
                }`}
              >
                Everyone in my pool ({count})
              </button>
              <button
                type="button"
                onClick={() => setPicked(picked ?? [])}
                className={`rounded-md border px-3 py-1.5 text-xs font-medium ${
                  picked !== null
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border text-muted-foreground hover:text-foreground"
                }`}
              >
                Specific users
              </button>
            </div>
            {picked !== null && (
              <RecipientPicker selected={picked} onChange={setPicked} />
            )}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="n-title">Title</Label>
            <Input
              id="n-title"
              value={title}
              maxLength={120}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Platform maintenance tonight"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="n-msg">Message</Label>
            <textarea
              id="n-msg"
              value={message}
              maxLength={1000}
              onChange={(e) => setMessage(e.target.value)}
              rows={4}
              placeholder="Type the message your users will see…"
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
            <div className="text-right text-[11px] text-muted-foreground">{message.length}/1000</div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="n-link" className="flex items-center gap-1.5">
              <Link2 className="size-3.5" /> Link <span className="text-muted-foreground">(optional)</span>
            </Label>
            <Input
              id="n-link"
              value={link}
              maxLength={500}
              onChange={(e) => setLink(e.target.value)}
              placeholder="https://…  (users can tap to open)"
            />
          </div>

          <div className="space-y-1.5">
            <Label>Level</Label>
            <div className="flex flex-wrap gap-2">
              {LEVELS.map((l) => (
                <button
                  key={l.k}
                  type="button"
                  onClick={() => setLevel(l.k)}
                  className={`rounded-md border px-3 py-1.5 text-xs font-semibold transition-colors ${
                    level === l.k ? l.tone + " bg-accent" : "border-border text-muted-foreground hover:bg-accent/50"
                  }`}
                >
                  {l.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex justify-end pt-1">
            <Button onClick={submit} disabled={!canSend}>
              <Send className="size-4" /> {mut.isPending ? "Sending…" : `Send to ${count} users`}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
