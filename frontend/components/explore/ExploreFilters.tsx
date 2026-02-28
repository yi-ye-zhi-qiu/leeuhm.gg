"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Button } from "@/components/ui/button";
import { Check, ChevronsUpDown, X } from "lucide-react";
import { cn } from "@/lib/utils";
import champions from "@/lib/champions.json";

const RANKS = [
  { value: "CHALLENGER", label: "Challenger" },
  { value: "GRANDMASTER", label: "Grandmaster" },
  { value: "MASTER", label: "Master" },
  { value: "DIAMOND", label: "Diamond" },
  { value: "EMERALD", label: "Emerald" },
];

export function ExploreFilters({
  currentRank,
  currentChampion,
}: {
  currentRank: string;
  currentChampion?: number;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [champOpen, setChampOpen] = useState(false);

  const selectedChampion = champions.find((c) => c.id === currentChampion);

  function updateParams(updates: Record<string, string | undefined>) {
    const params = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(updates)) {
      if (value === undefined) {
        params.delete(key);
      } else {
        params.set(key, value);
      }
    }
    // Reset to page 1 on filter change
    params.delete("page");
    router.push(`/explore?${params.toString()}`);
  }

  return (
    <div className="mb-6 flex items-center gap-3">
      <Select
        value={currentRank}
        onValueChange={(value) => updateParams({ rank: value })}
      >
        <SelectTrigger className="w-40">
          <SelectValue placeholder="Rank" />
        </SelectTrigger>
        <SelectContent>
          {RANKS.map((r) => (
            <SelectItem key={r.value} value={r.value}>
              {r.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Popover open={champOpen} onOpenChange={setChampOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={champOpen}
            className="w-48 justify-between"
          >
            {selectedChampion ? selectedChampion.name : "All Champions"}
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-48 p-0">
          <Command>
            <CommandInput placeholder="Search champion..." />
            <CommandList>
              <CommandEmpty>No champion found.</CommandEmpty>
              <CommandGroup>
                {champions.map((c) => (
                  <CommandItem
                    key={c.id}
                    value={c.name}
                    onSelect={() => {
                      updateParams({
                        champion:
                          c.id === currentChampion
                            ? undefined
                            : String(c.id),
                      });
                      setChampOpen(false);
                    }}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        currentChampion === c.id
                          ? "opacity-100"
                          : "opacity-0"
                      )}
                    />
                    {c.name}
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      {selectedChampion && (
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => updateParams({ champion: undefined })}
        >
          <X className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}
