import Image from "next/image";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { ArrowRight } from "lucide-react";

export default function HomePage() {
  return (
    <main className="mx-auto flex max-w-5xl items-center justify-center gap-12 px-8 py-6 pt-16 min-h-[calc(100vh-6rem)]">
      {/* Left */}
      <div className="flex flex-1 flex-col gap-4">
        <Link href="/explore" className="w-fit">
          <Badge
            variant="outline"
            className="flex items-center gap-2 px-3 py-1 text-sm hover:bg-accent transition-colors"
          >
            <span className="h-2 w-2 rounded-full bg-green-500" />
            leeuhm.gg is Live
            <ArrowRight className="h-3 w-3" />
          </Badge>
        </Link>
        <h2 className="text-4xl font-bold tracking-tight font-heading">
          High Elo Match Analysis
        </h2>
        <h3 className="text-lg text-muted-foreground">
          Explore Challenger, Grandmaster, and Master tier matches with
          SHAP-powered win probability breakdowns.
        </h3>
      </div>

      {/* Right */}
      <div className="relative flex-1 overflow-hidden rounded-lg">
        <Image
          src="/hero.webp"
          alt="leeuhm.gg hero"
          width={600}
          height={400}
          className="rounded-lg"
          priority
        />
        <div className="absolute inset-0 bg-primary/20 mix-blend-multiply rounded-lg" />
      </div>
    </main>
  );
}
