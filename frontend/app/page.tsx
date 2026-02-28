import Image from "next/image";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { ArrowRight, Github } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <>
      <main className="mx-auto flex max-w-5xl items-center justify-center gap-12 px-8 py-6 pt-16 min-h-[calc(100vh-6rem)]">
        {/* Left */}
        <div className="flex flex-1 flex-col gap-4">
          <Link href="/explore" className="w-fit">
            <Badge
              variant="outline"
              className="flex items-center gap-2 px-3 py-1 text-sm hover:bg-accent transition-colors"
            >
              <span className="h-2 w-2 rounded-full bg-indigo-500" />
              leeuhm.gg is live
              <ArrowRight className="h-3 w-3" />
            </Badge>
          </Link>
          <h2 className="text-4xl font-bold tracking-tight font-heading">
            League of Legends Match Analysis
          </h2>
          <h3 className="text-lg text-muted-foreground">
            How public data can help gamers know why they lost via SHAP-powered
            win probability breakdowns.
          </h3>
          <Button variant="outline" className="w-fit" asChild>
            <a
              href="https://github.com/yi-ye-zhi-qiu/leeuhm.gg"
              target="_blank"
              rel="noopener noreferrer"
            >
              <Github className="h-4 w-4" />
              Source code
            </a>
          </Button>

          <div className="mt-4 rounded-lg border bg-card p-4 text-sm text-muted-foreground">
            <p>
              Created by Liam Isaacs as part of{" "}
              <span className="font-semibold text-foreground">
                NeapTide Conference
              </span>{" "}
              — 28 Feb 2026, 6:00 to 7:00 PM, 9 Monroe St. New York, NY.
            </p>
            <p className="mt-1">
              <span className="italic">
                &ldquo;More Solvency in the Dialectic&rdquo;
              </span>{" "}
              with Harley Hollenstein, Asher Price, and Devin Brown.
            </p>
          </div>
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

      {/* About */}
      <section className="mx-auto max-w-3xl px-8 py-0">
        <h2 className="text-3xl font-bold tracking-tight font-heading">
          About
        </h2>

        <div className="mt-8 space-y-4 text-muted-foreground leading-relaxed">
          <p>
            Liam talks with conviction about a subject he&rsquo;s interested in
            to create a compelling visual stage. The lecture connects to music
            in symbolic, metaphorical ways, rather than a functioning piece of
            software. The musicians are the visualizer; the lecturer is not
            themselves this. It&rsquo;s a closed loop with no open
            circuits&mdash;musicians and data create non-hallucinatory outputs.
          </p>
          <p>
            Code is rapid fire. We don&rsquo;t &ldquo;see&rdquo; per se.
            It&rsquo;s all kind of a hallucination. And the eye is constantly
            checking small details to see if the mental image is just as
            accurate.
          </p>
        </div>
      </section>
    </>
  );
}
