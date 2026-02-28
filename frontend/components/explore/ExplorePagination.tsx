"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

function buildHref(searchParams: URLSearchParams, page: number) {
  const params = new URLSearchParams(searchParams.toString());
  if (page <= 1) {
    params.delete("page");
  } else {
    params.set("page", String(page));
  }
  return `/explore?${params.toString()}`;
}

export function ExplorePagination({
  currentPage,
  hasMore,
  totalPages,
}: {
  currentPage: number;
  hasMore: boolean;
  totalPages: number;
}) {
  const searchParams = useSearchParams();
  const router = useRouter();

  if (totalPages <= 1) return null;

  const hasPrev = currentPage > 1;
  const hasNext = hasMore;

  // Build page numbers: 1, 2, 3, 4, 5 ... last
  const pages: (number | "ellipsis")[] = [];
  const maxVisible = 5;

  if (totalPages <= maxVisible + 2) {
    for (let i = 1; i <= totalPages; i++) pages.push(i);
  } else {
    // Always show page 1
    pages.push(1);

    let start = Math.max(2, currentPage - 1);
    let end = Math.min(totalPages - 1, currentPage + 1);

    // Adjust window near edges
    if (currentPage <= 3) {
      start = 2;
      end = maxVisible;
    } else if (currentPage >= totalPages - 2) {
      start = totalPages - maxVisible + 1;
      end = totalPages - 1;
    }

    if (start > 2) pages.push("ellipsis");
    for (let i = start; i <= end; i++) pages.push(i);
    if (end < totalPages - 1) pages.push("ellipsis");

    // Always show last page
    pages.push(totalPages);
  }

  const go = (page: number) => router.push(buildHref(searchParams, page));

  return (
    <div className="flex items-center justify-center gap-1 mt-6 px-4">
      <Button
        variant="outline"
        size="sm"
        onClick={() => go(currentPage - 1)}
        disabled={!hasPrev}
        className="rounded-xl"
      >
        &larr;
      </Button>
      {pages.map((p, i) =>
        p === "ellipsis" ? (
          <span
            key={`ellipsis-${i}`}
            className="px-2 text-xs text-muted-foreground"
          >
            &hellip;
          </span>
        ) : (
          <Button
            key={p}
            variant="ghost"
            size="sm"
            onClick={() => go(p)}
            className={cn(
              "px-2 h-auto py-1 text-xs",
              currentPage === p
                ? "font-bold text-foreground"
                : "text-muted-foreground"
            )}
          >
            {p}
          </Button>
        )
      )}
      <Button
        variant="outline"
        size="sm"
        onClick={() => go(currentPage + 1)}
        disabled={!hasNext}
        className="rounded-xl"
      >
        &rarr;
      </Button>
    </div>
  );
}
