"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { FileSpreadsheet, FileText } from "lucide-react";
import { UsersAPI } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

/**
 * Super admin: take the whole user book out as a file.
 *
 * The Users page lists an actor's OWN pool, so a super admin whose clients
 * all sit under sub-admins sees an empty page while the platform carries
 * hundreds. Here they pick whose pool to take — one admin, one broker, or
 * everybody — and get it as a sheet or a PDF.
 */
export function UserExportDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const [owner, setOwner] = useState("all");
  const [includeDemo, setIncludeDemo] = useState(false);
  const [includeClosed, setIncludeClosed] = useState(false);
  const [busy, setBusy] = useState<"xlsx" | "pdf" | null>(null);

  const { data: owners } = useQuery({
    queryKey: ["admin", "users", "export-owners"],
    queryFn: () => UsersAPI.exportOwners(),
    enabled: open,
    staleTime: 5 * 60_000,
  });

  async function download(format: "xlsx" | "pdf") {
    setBusy(format);
    try {
      const blob = await UsersAPI.exportFile({
        owner,
        format,
        include_demo: includeDemo,
        include_closed: includeClosed,
      });
      // Object URL + synthetic click — the request carries the auth header,
      // so a plain <a href> to the endpoint would 401.
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const stamp = new Date().toISOString().slice(0, 10);
      a.href = url;
      a.download = `users-${owner}-${stamp}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      onOpenChange(false);
    } catch (e: any) {
      toast.error(e?.message || "Could not build the file");
    } finally {
      setBusy(null);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Download users</DialogTitle>
          <DialogDescription>
            Pick whose clients to take. Balance, credit, used margin, settlement
            due, this week&apos;s P&amp;L and open positions come with every row.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Whose users
            </label>
            <select
              value={owner}
              onChange={(e) => setOwner(e.target.value)}
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
            >
              {(owners ?? [{ value: "all", label: "All owners — the whole platform" }]).map(
                (o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ),
              )}
            </select>
          </div>

          <div className="flex flex-wrap gap-4 text-sm">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                className="size-4 accent-primary"
                checked={includeDemo}
                onChange={(e) => setIncludeDemo(e.target.checked)}
              />
              Include demo accounts
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                className="size-4 accent-primary"
                checked={includeClosed}
                onChange={(e) => setIncludeClosed(e.target.checked)}
              />
              Include closed accounts
            </label>
          </div>

          <p className="text-xs leading-relaxed text-muted-foreground">
            Email and phone stay hidden, the same as on screen — the PDF leaves
            those two columns out entirely. Every download is written to the
            audit log.
          </p>
        </div>

        <DialogFooter className="gap-2">
          <Button
            variant="secondary"
            className="gap-2"
            disabled={busy !== null}
            loading={busy === "xlsx"}
            onClick={() => download("xlsx")}
          >
            <FileSpreadsheet className="size-4" /> Excel
          </Button>
          <Button
            className="gap-2"
            disabled={busy !== null}
            loading={busy === "pdf"}
            onClick={() => download("pdf")}
          >
            <FileText className="size-4" /> PDF
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
