"use client";

import { useSearchParams } from "next/navigation";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";

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
}: {
  currentPage: number;
  hasMore: boolean;
}) {
  const searchParams = useSearchParams();

  if (currentPage === 1 && !hasMore) return null;

  return (
    <Pagination className="mt-6">
      <PaginationContent>
        {currentPage > 1 && (
          <PaginationItem>
            <PaginationPrevious href={buildHref(searchParams, currentPage - 1)} />
          </PaginationItem>
        )}

        <PaginationItem>
          <span className="px-3 text-sm text-muted-foreground">
            Page {currentPage}
          </span>
        </PaginationItem>

        {hasMore && (
          <PaginationItem>
            <PaginationNext href={buildHref(searchParams, currentPage + 1)} />
          </PaginationItem>
        )}
      </PaginationContent>
    </Pagination>
  );
}
