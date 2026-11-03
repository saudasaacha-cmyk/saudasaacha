"use client";

/**
 * Multi-select user picker for the notification composer.
 *
 * Search hits the same `/admin/users?q=` the Users table uses, so it is
 * already scoped to the actor's pool — but the server intersects the ids
 * again on send, because this component is not what the request has to be
 * trusted on.
 *
 * Selected users are kept as `{id, label}` rather than ids alone. The chips
 * have to stay readable after the search term that found them is cleared,
 * and re-fetching a name for a row already on screen is a round trip to
 * display something the picker had in hand.
 */

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search as SearchIcon, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { UsersAPI } from "@/lib/api";

export type Recipient = { id: string; label: string; sub: string };

export function RecipientPicker({
  selected,
  onChange,
}: {
  selected: Recipient[];
  onChange: (next: Recipient[]) => void;
}) {
  const [term, setTerm] = useState("");
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(term.trim()), 250);
    return () => clearTimeout(t);
  }, [term]);

  const { data, isFetching } = useQuery({
    queryKey: ["admin", "notify", "user-search", debounced],
    queryFn: () => UsersAPI.list({ q: debounced, page_size: 8 }),
    enabled: debounced.length >= 2,
    staleTime: 60_000,
  });

  const chosen = new Set(selected.map((r) => r.id));
  const results = (((data as any)?.items ?? []) as any[]).filter(
    (u) => !chosen.has(String(u.id)),
  );

  function add(u: any) {
    onChange([
      ...selected,
      {
        id: String(u.id),
        label: u.full_name || u.user_code || String(u.id).slice(-8),
        sub: [u.user_code, u.email, u.mobile].filter(Boolean).join(" · "),
      },
    ]);
    setTerm("");
    setDebounced("");
  }

  return (
    <div className="space-y-2">
      <div className="relative">
        <div className="relative">
          <SearchIcon className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={term}
            onChange={(e) => {
              setTerm(e.target.value);
              setOpen(true);
            }}
            onFocus={() => setOpen(true)}
            // Delay close so a click on a result registers before blur.
            onBlur={() => setTimeout(() => setOpen(false), 150)}
            placeholder="Search by User ID, name, email or mobile…"
            className="h-9 pl-8"
          />
        </div>
        {open && debounced.length >= 2 && (
          <div className="absolute z-20 mt-1 max-h-72 w-full overflow-auto rounded-md border border-border bg-background shadow-lg">
            {isFetching && results.length === 0 ? (
              <div className="px-3 py-2 text-xs text-muted-foreground">Searching…</div>
            ) : results.length === 0 ? (
              <div className="px-3 py-2 text-xs text-muted-foreground">
                No more matching users
              </div>
            ) : (
              results.map((u) => (
                <button
                  key={u.id}
                  type="button"
                  onClick={() => add(u)}
                  className="flex w-full flex-col gap-0.5 border-b border-border/50 px-3 py-2 text-left text-xs last:border-0 hover:bg-muted/50"
                >
                  <span className="font-medium text-foreground">
                    {u.full_name || u.user_code || String(u.id).slice(-8)}
                  </span>
                  <span className="font-mono text-[10px] text-muted-foreground">
                    {[u.user_code, u.email, u.mobile].filter(Boolean).join(" · ") ||
                      String(u.id)}
                  </span>
                </button>
              ))
            )}
          </div>
        )}
      </div>

      {selected.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          Nobody picked yet — search above and click a user to add them.
        </p>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {selected.map((r) => (
            <span
              key={r.id}
              title={r.sub}
              className="inline-flex items-center gap-1 rounded-full border border-border bg-muted/40 py-1 pl-2.5 pr-1 text-xs"
            >
              {r.label}
              <button
                type="button"
                aria-label={`Remove ${r.label}`}
                onClick={() => onChange(selected.filter((x) => x.id !== r.id))}
                className="rounded-full p-0.5 text-muted-foreground hover:bg-background hover:text-foreground"
              >
                <X className="size-3" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
