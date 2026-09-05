"use client";

import { useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Download, Trash2, Upload } from "lucide-react";
import { ChartLevelsAPI, type ChartLevelRow } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable, type Column } from "@/components/common/DataTable";

/**
 * Chart lines — Excel round-trip.
 *
 * Pick a segment, download the template (pre-filled with whatever is already
 * saved), type up to four price/colour pairs per instrument, upload it back.
 * Each price is drawn as a horizontal line on that instrument's chart, in the
 * colour given, for the users under this admin.
 */
export default function ChartLevelsPage() {
  const qc = useQueryClient();
  const [segment, setSegment] = useState<string>("CRYPTO_SPOT");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: segments } = useQuery({
    queryKey: ["admin", "chart-levels", "segments"],
    queryFn: () => ChartLevelsAPI.segments(),
  });

  const { data: rows, isFetching } = useQuery({
    queryKey: ["admin", "chart-levels", segment],
    queryFn: () => ChartLevelsAPI.list(segment),
  });

  const configured = useMemo(() => (rows ?? []).length, [rows]);

  async function download() {
    setBusy(true);
    try {
      const blob = await ChartLevelsAPI.template(segment);
      // Object URL + synthetic click — the request needs the auth header, so
      // a plain <a href> to the endpoint would 401.
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `chart-levels-${segment}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Could not build the template");
    } finally {
      setBusy(false);
    }
  }

  async function upload(file: File) {
    setBusy(true);
    try {
      const res = await ChartLevelsAPI.import(file);
      const bits = [`${res.updated} updated`];
      if (res.cleared) bits.push(`${res.cleared} cleared`);
      toast.success(`Saved — ${bits.join(", ")}`);
      // Show every rejected row rather than a single generic failure: with
      // forty rows the operator needs to know WHICH ones to fix.
      for (const e of (res.errors ?? []).slice(0, 8)) toast.error(e);
      if ((res.errors ?? []).length > 8) {
        toast.error(`…and ${res.errors.length - 8} more problems`);
      }
      qc.invalidateQueries({ queryKey: ["admin", "chart-levels"] });
    } catch (e: any) {
      toast.error(e?.message || "Upload failed");
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function clearRow(token: string) {
    try {
      await ChartLevelsAPI.clear(token);
      toast.success("Lines removed");
      qc.invalidateQueries({ queryKey: ["admin", "chart-levels"] });
    } catch {
      toast.error("Could not remove");
    }
  }

  const columns: Column<ChartLevelRow>[] = [
    { key: "symbol", header: "Symbol", render: (r) => <span className="font-medium">{r.symbol}</span> },
    { key: "token", header: "Token", render: (r) => <span className="text-xs text-muted-foreground">{r.token}</span> },
    {
      key: "levels",
      header: "Lines",
      render: (r) => (
        <div className="flex flex-wrap gap-2">
          {r.levels.map((lv, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1.5 rounded-full border border-border px-2 py-0.5 text-xs tabular-nums"
              title={lv.label || undefined}
            >
              <span
                className="size-2.5 rounded-full ring-1 ring-inset ring-black/20"
                style={{ backgroundColor: lv.color }}
              />
              {lv.price}
              {lv.label ? <span className="text-muted-foreground">· {lv.label}</span> : null}
            </span>
          ))}
        </div>
      ),
    },
    {
      key: "actions",
      header: "",
      render: (r) => (
        <Button size="sm" variant="ghost" onClick={() => clearRow(r.token)} title="Remove all lines">
          <Trash2 className="size-4" />
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      <PageHeader
        title="Chart lines"
        description="Draw horizontal price lines on your users' charts. Download the segment's sheet, fill in prices and colours, upload it back."
      />

      <div className="flex flex-wrap items-end gap-3 rounded-xl border border-border bg-card p-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-muted-foreground">Segment</label>
          <select
            value={segment}
            onChange={(e) => setSegment(e.target.value)}
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          >
            {(segments ?? [segment]).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        <Button onClick={download} disabled={busy} className="gap-2">
          <Download className="size-4" /> Download sheet
        </Button>

        <Button
          variant="secondary"
          disabled={busy}
          className="gap-2"
          onClick={() => fileRef.current?.click()}
        >
          <Upload className="size-4" /> Upload filled sheet
        </Button>
        <input
          ref={fileRef}
          type="file"
          accept=".xlsx,.xlsm"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void upload(f);
          }}
        />

        <span className="ml-auto text-sm text-muted-foreground">
          {configured} instrument{configured === 1 ? "" : "s"} with lines in this segment
        </span>
      </div>

      <DataTable
        columns={columns}
        rows={rows}
        keyExtractor={(r) => r.token}
        loading={isFetching}
        empty="No lines set for this segment yet."
      />

      <p className="text-xs leading-relaxed text-muted-foreground">
        Re-uploading replaces the lines for every instrument listed in the sheet. A row with all four
        prices blank clears that instrument. Colours accept hex (<code>#E31E24</code>) or names
        (red, green, blue, orange, purple…).
      </p>
    </div>
  );
}
