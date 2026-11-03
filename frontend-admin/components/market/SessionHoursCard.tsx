"use client";

/**
 * Editable session hours for one segment group.
 *
 * Blank means "use the code default", and the placeholder shows what that
 * default resolves to — so an empty field reads as inherited rather than
 * broken. The backend stores overrides only; clearing a field returns that end
 * of the session to the shipped value, which is why there is always a
 * known-good floor and no way to leave a group with no session at all.
 *
 * Two closes, because they are two different gates. "Order entry" is when the
 * validator stops accepting new orders. "Risk gate" is when `is_after_close`
 * starts treating the session as over, which silences the pending-order poller
 * and the risk enforcer and fires the EOD rollover. NSE/BSE runs the gate 30
 * minutes past the bell so late prints settle; MCX cannot, because the
 * rollover fires the minute after the gate.
 */

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MarketAPI } from "@/lib/api";

type Row = {
  group: string;
  label: string;
  open_time: string | null;
  entry_close: string | null;
  gate_close: string | null;
  auto_dst: boolean;
  supports_auto_dst: boolean;
  warn_lead_minutes: number[];
  effective: { open: string | null; entry_close: string | null; gate_close: string | null };
};

export function SessionHoursCard({ row, onSaved }: { row: Row; onSaved: () => void }) {
  const [open, setOpen] = useState(row.open_time ?? "");
  const [entry, setEntry] = useState(row.entry_close ?? "");
  const [gate, setGate] = useState(row.gate_close ?? "");
  const [auto, setAuto] = useState(row.auto_dst);
  const [warn, setWarn] = useState((row.warn_lead_minutes ?? []).join(", "));
  const [saving, setSaving] = useState(false);

  // Re-seed when the server sends a fresh row (another admin saved, or our own
  // save came back) so the inputs never drift from what is stored.
  useEffect(() => {
    setOpen(row.open_time ?? "");
    setEntry(row.entry_close ?? "");
    setGate(row.gate_close ?? "");
    setAuto(row.auto_dst);
    setWarn((row.warn_lead_minutes ?? []).join(", "));
  }, [row.open_time, row.entry_close, row.gate_close, row.auto_dst, row.warn_lead_minutes]);

  async function save() {
    setSaving(true);
    try {
      await MarketAPI.saveSession(row.group, {
        open_time: open,
        entry_close: entry,
        gate_close: gate,
        warn_lead_minutes: warn,
        ...(row.supports_auto_dst ? { auto_dst: auto } : {}),
      });
      toast.success(`${row.label} hours saved`);
      onSaved();
    } catch (e: any) {
      toast.error(e?.message ?? "Save failed");
    } finally {
      setSaving(false);
    }
  }

  const autoPinned = row.supports_auto_dst && auto;

  function field(
    id: string,
    label: string,
    value: string,
    set: (v: string) => void,
    effective: string | null,
    hint: string,
    disabled = false,
  ) {
    return (
      <div className="space-y-1.5">
        <Label htmlFor={id}>{label}</Label>
        <Input
          id={id}
          value={value}
          onChange={(e) => set(e.target.value)}
          placeholder={effective ?? "HH:MM"}
          disabled={disabled}
          className="font-tabular"
        />
        <p className="text-xs text-muted-foreground">
          {disabled || value ? hint : `Blank — using ${effective ?? "—"}. ${hint}`}
        </p>
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{row.label}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-3">
          {field(
            `open-${row.group}`,
            "Opens",
            open,
            setOpen,
            row.effective.open,
            "Before this, orders are refused and parked fills are held.",
          )}
          {field(
            `entry-${row.group}`,
            "Order entry closes",
            entry,
            setEntry,
            row.effective.entry_close,
            autoPinned
              ? "Derived from US daylight saving — turn the toggle off to pin it."
              : "After this, new orders are refused. Exits and AMO are unaffected.",
            autoPinned,
          )}
          {field(
            `gate-${row.group}`,
            "Risk gate closes",
            gate,
            setGate,
            row.effective.gate_close,
            "Stops the poller and the risk enforcer, and fires the EOD rollover.",
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor={`warn-${row.group}`}>Margin warning, minutes before the gate</Label>
          <Input
            id={`warn-${row.group}`}
            value={warn}
            onChange={(e) => setWarn(e.target.value)}
            placeholder="30, 10"
            className="font-tabular sm:max-w-[16rem]"
          />
          <p className="text-xs text-muted-foreground">
            {warn.trim()
              ? `Users who still cannot fund their overnight carry are told how much to add, ${warn
                  .trim()} minute(s) before ${row.effective.gate_close ?? "the gate"}. Only users who are actually short are messaged, and only once per mark per day — someone who funds after the first ping does not get the second.`
              : "Blank — no warning is sent. Users find out when the position is squared off."}
          </p>
        </div>

        {row.supports_auto_dst && (
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              checked={auto}
              onChange={(e) => setAuto(e.target.checked)}
              className="mt-0.5 size-4 accent-primary"
            />
            <span>
              Follow US daylight saving automatically
              <span className="block text-xs text-muted-foreground">
                MCX&apos;s circulars track it — 23:30 IST while US DST is in effect, 23:55 IST
                otherwise, flipping each March and November. Turning this off freezes that flip
                at whatever you pin above, and you will have to change it twice a year yourself.
              </span>
            </span>
          </label>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">
            In force now: opens {row.effective.open ?? "—"} · entry closes{" "}
            {row.effective.entry_close ?? "—"} · gate closes {row.effective.gate_close ?? "—"} ·{" "}
            {warn.trim() ? `warns ${warn.trim()} min before` : "no margin warning"}
          </p>
          <Button onClick={save} disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
