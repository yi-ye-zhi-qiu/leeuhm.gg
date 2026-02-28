import { Skeleton } from "@/components/ui/skeleton";

export function MatchRowSkeleton() {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-3 rounded-lg border-l-4 border-l-muted px-3 py-2">
        <div className="flex w-20 shrink-0 flex-col gap-1">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-2.5 w-12" />
          <Skeleton className="h-2.5 w-10" />
          <Skeleton className="h-2.5 w-12" />
        </div>
        <Skeleton className="h-10 w-10 shrink-0 rounded-full" />
        <div className="flex w-24 shrink-0 flex-col items-center gap-1">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-2.5 w-12" />
        </div>
        <div className="flex w-16 shrink-0 flex-col items-center gap-1">
          <Skeleton className="h-3 w-14" />
          <Skeleton className="h-2.5 w-10" />
        </div>
        <div className="grid grid-cols-3 gap-0.5">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-6 w-6 rounded" />
          ))}
        </div>
        <div className="ml-auto flex gap-3">
          <div className="flex flex-col gap-px">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-3 w-[72px]" />
            ))}
          </div>
          <div className="flex flex-col gap-px">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-3 w-[72px]" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
