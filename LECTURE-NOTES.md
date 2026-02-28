# Harley Talk — 27 Feb 2026

## Abstract

(fill in)

---

## Infrastructure as Code

Infrastructure as Code (IaC) means you define cloud resources in declarative config files instead of clicking around a console. Terraform is the tool we use — it's like a blueprint for your cloud. You write `.tf` files that say "I want a storage account, a container registry, a virtual network" and Terraform figures out how to create, update, or destroy those resources to match.

The key principle here is "atomic state" — each Terraform module controls a small, self-contained group of related resources (a "goldilocks" group). This limits blast radius: if something breaks in the networking module, it doesn't take down your database. It prevents the dreaded "mega-module" where one monolithic config manages everything and a single typo can nuke your whole stack.

Remote state is stored in an Azure Storage Account (the AWS equivalent would be S3 or a DynamoDB table). This means any developer can concurrently access the state, which is what tracks what resources actually exist. Without remote state, two people running Terraform at the same time could create duplicate resources or overwrite each other. It enables CI/CD without config drift or manual console commands.

In this project, the Terraform is split into three modules: `infra/root/` (state storage itself), `infra/crawl/` (crawler infrastructure — container registry, VNet, NAT gateway, blob storage), and `infra/db/` (Synapse SQL warehouse).

---

## The Pitch

Let's say I want to build something:
- An ETL pipeline in Python and SQL
- A deployable, testable web crawler that supports code reuse and can crawl 1000+ pages per minute
- Cloud compute for data storage and analysis

These are lofty goals. I want to write protocols and subroutines with these properties. What are my options?

---

## Crawl

### A Brief History of HTTP & Why Scraping Got Hard

**[source: https://ably.com/topic/http2]**

In the old days, scraping web data was easy. HTTP/1.1, developed in 1995 and formalized in RFC 2068 (1997), introduced persistent connections, pipelining, and basic authentication. But it had real performance problems: head-of-line blocking (one slow packet holds up everything behind it), pipelining issues (a large response blocks all the ones queued after it), protocol overhead, and TCP slow start.

In 2009, Google announced SPDY, an experimental protocol that achieved a 53% reduction in page load time. SPDY directly inspired HTTP/2.

**[source: https://www.trickster.dev/post/understanding-http2-fingerprinting/]**

HTTP/2 is fundamentally different. It's a binary protocol (not text-based like HTTP/1.1), specified under RFC 7540. Where HTTP/1.1 needs one TCP connection per request, HTTP/2 multiplexes many request-response flows over a single connection. In practice, HTTP/2 is almost always wrapped in TLS. When the TLS handshake happens, the ALPN (Application-Layer Protocol Negotiation) extension decides whether to use HTTP/1.1 or HTTP/2 inside the encrypted channel.

HTTP/2 connections are subdivided into "streams" — numbered, bidirectional conversations between client and server. Each stream is a sequence of frames (HEADERS, DATA, etc. — if you've used Wireshark, you've seen these).

### HTTP/2 Fingerprinting & Anti-Bot

HTTP/2 fingerprinting works by observing the client's behavior — things like the order of HTTP/2 settings frames, header compression table size, window update values — to infer what software (OS, browser) is running on the client. It doesn't uniquely identify an end user, just the software stack. A fingerprint string gets hashed, and anti-bot companies like Akamai use this as part of their detection. You can check your own HTTP/2 and TLS fingerprints at tls.peet.ws.

At the same time, websites started tracking users more aggressively through cookies. The term comes from "magic cookie" — a Unix concept where a program receives a packet of data and sends it back unchanged. Cookies gave websites (which are inherently stateless — the connection terminates when you're done) a way to store "memory" about a user across requests. Anti-bot strategies layer on top of this: session cookies, screen size measurement, mouse movement tracking, canvas fingerprinting, and more.

### Impact on Web Scraping

Before TLS fingerprinting, HTTP/1.1 scraping was trivial — rotate your User-Agent header and you're golden. You could use BeautifulSoup and Requests in Python to parse HTML responses with CSS selectors, and that was the whole game.

It got harder for two reasons:

**Legal pressure.** In 2024, a summary judgment found that a proxy provider didn't violate Meta's ToS. But there's a consistent existential threat that scraping public data will expose you to lawsuits from large corporations. Also in 2024, X sued over scraping; it was dismissed by a California district court. The ethics are genuinely complicated — is it okay to scrape data and train an AI model? The intuition is that "personal" data should be protected, but the internet was never built for individuals to own their data. It's hard to argue either way.

**Technical evolution.** The web pivoted from server-rendered HTML to React and other JS frameworks. React is an open-source frontend JavaScript library (created by Facebook) that controls the DOM and only re-renders what changed — it's now the dominant way websites are built. The problem for scrapers is that data is now client-side rendered, not embedded in the HTML. This led to tools like Selenium (headless browsers that run a full Chromium engine on your machine), which are painfully slow — maybe 1-2 pages per minute.

So what do we do? The answer lies in two key ideas: scraping the Network tab (XHR requests) and using event-driven architecture.

### Key #1: The Network Tab

Before AJAX, only `setTimeout` and `setInterval` could provide async behavior in the browser. Then came AJAX (Asynchronous JavaScript and XML) and XMLHttpRequest (XHR) objects — configurable, event-driven calls to a server.

The insight: most websites don't embed data in HTML anymore. They have an API that the frontend calls to fetch data from a database. You can see these requests in the browser's Network tab (filter by XHR/Fetch). Instead of parsing HTML and wrestling with JavaScript injection, you can call the same API endpoints the website uses. This is the first key unlock — abandon HTML-based scraping entirely. The rabbit hole of JS injection is a labyrinth.

Note: this technique will need to adapt as React server actions (now called "server functions") gain popularity — these bundle the data-fetching into the server-rendered response, so there's no separate XHR call to intercept.

### Key #2: Event-Driven Architecture

Python doesn't have built-in async I/O primitives (well, `asyncio` exists now, but the ecosystem of third-party libraries predates it). Twisted is the grandparent of async Python — a networking engine from the early 2000s. Tornado is another well-known one.

**[source: "Architecting an event-driven networking engine: Twisted Python," Jessica McKellar, 2013]**

Why do we care about event-driven? It helps to contrast three programming paradigms:

1. **Single-threaded synchronous.** One thing at a time. If you hit an expensive operation (DB query, network request), you block and wait. Simple to reason about, but terrible for throughput.

2. **Multi-threaded.** The OS manages threads across CPUs. You can make progress on multiple tasks simultaneously. But now you have to think about shared state — concurrent access to the same data requires locking primitives to prevent corruption. The mental overhead is real: the program isn't a serial read-through anymore.

3. **Event-driven.** Single-threaded, but you yield control to an event loop that fires callbacks when I/O is ready. No shared-state headaches, no locking. Great for workloads with many independent, I/O-bound tasks — like making thousands of HTTP requests.

The core of Twisted is the "reactor" — the event loop that dispatches callbacks. Scrapy is built on top of Twisted, purpose-made for web crawling. This is what lets us hit 1000+ pages per minute. That's the second key.

### What the Code Looks Like

The crawler is a `CrawlGameData` class that inherits from Scrapy's base Spider class:
- It hits u.gg's leaderboard API (GraphQL) to get player names, paginated across ~7,500 pages (Challenger down to Bronze).
- For each player, it fetches their top 20 games — API requests are internal methods that return `JsonRequest` objects.
- Each match yields a full JSON response: post-game stats (10 players), team objectives, timeline data, player ranks.

Two important customizations:
- **GzipPlugin fix:** Modified to close the Gzip instance, not the underlying file handle. Without this, you get corrupted archives.
- **`AzureFeedStorage` + `ImmediateFeedExporter`:** Custom Scrapy extensions. The default behavior is to buffer all items and upload when the spider closes. That's terrible for long crawls — if the process dies, you lose everything. The `ImmediateFeedExporter` uploads each batch (every 150 items) as soon as it's full. Items go to Azure Blob Storage as compressed `.jsonl.gz` files.

The crawler runs at `CONCURRENT_REQUESTS = 128` with proxy rotation and TLS fingerprint spoofing (via an `Impersonate` middleware) to avoid bot detection.

**>> DEMO: show the crawler running <<**

### Containerized Deployment

The crawler is containerized with Docker and deployed to Azure. The networking setup matters for proxy whitelisting:

**Azure:** A Container Instance is launched inside a VNet, routed to a private subnet that's associated with a NAT gateway. The NAT gateway has a static public IP, and that IP is whitelisted on the proxy server. This way, all outbound traffic from the container appears to come from one known IP.

**AWS equivalent:** ECS Fargate tasks in a private subnet, with a VPC routing table that sends outbound traffic through a NAT gateway in a public subnet. The NAT gateway connects to an Internet Gateway. Same idea — the NAT gateway's IP gets whitelisted on the proxy, and the Fargate task can pull images from ECR through the NAT.

### Crawl Results

In about 1-2 hours, we crawled ~30,000 games covering Challenger down to Emerald IV. If I accidentally closed my laptop and had to restart, I'd just set the starting page index to the rank of the oldest player already crawled and pick up where I left off.

**>> SHOW: bar chart of games by rank/tier <<**

---

## Data Analysis

### Azure Synapse

The crawled data lands in Azure Blob Storage as `.jsonl.gz` files — this is essentially an eventually consistent data lake. The data doesn't live in a traditional database table; instead, we query it in place using Azure Synapse Analytics (serverless mode).

Synapse lets you run SQL directly against files in blob storage using `OPENROWSET` with a `BULK` path. You point it at a folder of JSONL files and it reads them as if they were a table. No ETL step to load data into a warehouse first — you just query the raw files. The AWS equivalent would be AWS Athena, which does the same thing on top of S3.

### Feature Extraction (SQL-First)

The feature extraction is done in `db/scripts/features.py`, but the heavy lifting is a massive SQL query, not Python. This is a deliberate design choice — doing the JSON parsing and feature computation in SQL (via `CROSS APPLY OPENJSON`) means the Synapse engine handles the work at scale, and we only pull the final feature matrix into Python.

Each match has 10 player rows (from `postGameData`), and we extract ~80 raw features per player per match, including:

- **Match info:** matchId, duration, winning team, creation time
- **Player stats:** kills, deaths, assists, CS, gold, damage, wards, items (7 slots), summoner spells (2), runes (keystone + substyle)
- **Rank:** tier and LP, looked up from `allPlayerRanks` (solo queue preferred)
- **Performance scores:** hardCarry, teamplay, damageShare, goldShare, killParticipation, visionScore, finalLevelDiff
- **Team objectives:** baron, dragon, tower, inhibitor, rift herald kills (per player's team)
- **Timeline phase splits:** kills/deaths/wards in early game (<25% duration), mid game (25-50%), and late game (>50%)
- **Dragon breakdown:** total dragons, elder count, plus each type (infernal, mountain, ocean, hextech, chemtech, cloud)
- **Teamfight counts:** early/mid/late teamfights, defined as 2+ kills within a 15-second window
- **Diff frames:** CS/gold/KA/XP differentials by phase (primary player only)
- **Team compositions:** full champion lists for both teams, passed as JSON for Python-side encoding

---

## Model

### Starting Simple: Logistic Regression

You can start with a simple logistic regression to get a baseline. The code is straightforward:

```python
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

model = LogisticRegression(
    penalty="l2", solver="liblinear", max_iter=1000, C=0.1
)
model.fit(X_train, y_train)

accuracy = model.score(X_test, y_test)
```

Where `FEATURE_NAMES` is a global constant — an array of strings like "kills", "deaths", "assists". You can deploy its weights as a JSON file and have the frontend interpret them with a SHAP plot.

The user already knows the outcome of their game. What we're trying to do is quantify the win or loss — was it expected or unexpected, according to the model? And why?

For example, if you train on 10,000 games with just kills, deaths, and assists, you'd see that high kills correlate with winning. So the model would predict a win for a player with a high kill count. If they won *without* high kills — that's a surprising result, and the model tells you so.

### Feature Engineering: Where It Gets Interesting

League of Legends is a complicated game with many interaction terms. Was it that late-game teamfight that lost me the game, or something else entirely? Feature engineering lets you capture these nuances.

On the Python side (in `model/train_xgb.py`), the ~80 SQL features get expanded to 400+:

- **Per-minute rates:** kills/min, deaths/min, assists/min, CS/min, gold/min, damage/min, etc. — normalized by game duration so short and long games are comparable.
- **Rank encoding:** Tiers mapped to integers (Iron=1, Bronze=2, ... Challenger=8) plus LP as a numeric feature.
- **Win/loss streaks:** For each player, we sort their match history by time and compute rolling streaks at thresholds of 1, 2, 3, 5, and 10 games. These are cross-match temporal features — "was this player on a hot streak?"
- **One-hot encoding:** Items get binary columns (~200 features), summoner spells (~12), and runes/keystones (~40). Each item you had in a game becomes its own yes/no column.
- **Champion interactions (label-encoded categorical):** Lane matchup pairs (your champion vs. your lane opponent) and 4 teammate synergy pairs (your champion paired with each teammate, sorted by role). These capture "does this champion combo tend to win?"

The model also includes all the SQL-side features directly: objectives, performance scores, phase breakdowns, teamfight counts, dragon types, and differential frames.

### XGBoost

We use XGBoost (Extreme Gradient Boosting), which implements gradient-boosted decision trees. The intuition:

**Gradient descent** is an iterative optimization algorithm that minimizes a loss function by adjusting parameters in the direction of steepest descent — imagine rolling a ball downhill on a surface defined by your error.

**XGBoost** is similar but uses a second-order Taylor approximation of the loss function (Newton-Raphson in function space, rather than simple gradient descent). A Taylor series expands a function as an infinite sum of terms based on its derivatives at a single point — XGBoost uses up to the second derivative, which gives it better convergence. In practice, this means it trains faster and often achieves better accuracy than vanilla gradient boosting.

The model is trained as `binary:logistic` (binary classification, outputting a win probability between 0 and 1), with `enable_categorical=True` for the champion interaction features. On the NA1 dataset, it achieved **80.39% accuracy** on 7,422 samples with an 80/20 train/test split.

### SHAP: Explaining the "Why"

SHAP (SHapley Additive exPlanations) comes from cooperative game theory. The idea: for each prediction, assign each feature a "contribution score" — how much did this feature push the prediction toward a win vs. a loss? It's based on Shapley values, which fairly distribute the "payout" of a game among its players (in this case, the "players" are features and the "payout" is the prediction).

We use SHAP's `TreeExplainer`, which is optimized for tree-based models like XGBoost. For each player in each match, we compute SHAP values for all 400+ features, then keep only the top 6 (the 3 that helped most and 3 that hurt most). These get exported to `{region}_shap.json` as a lookup table keyed by match ID and player.

Important caveat: most ML models are black boxes, and SHAP explanations are an approximation. It's "vibes" — useful for intuition, not to be taken as ground truth. The force plot shows what helped and hurt, but it's a simplified story, not a rigorous causal explanation.

The force plot itself shows a horizontal bar representing win probability (0-100%). Blue arrows on the left are positive contributions (pushed toward winning), red arrows on the right are negative (pushed toward losing). They meet at the model's predicted probability. The outcome is labeled: Dominant (win with >70% probability), Expected (55-70%), Surprising (won with <55% predicted), and the inverses for losses.

---

## Frontend

### The Tech Stack, Explained

**Next.js** is a React meta-framework — it builds on top of React and adds routing, server-side rendering (SSR), static site generation, and a built-in dev server. We're using the "App Router" (introduced in Next.js 13), which uses file-system-based routing: a file at `app/explore/page.tsx` automatically becomes the `/explore` route. We're on Next.js 16 with React 19.

**React** is a JavaScript library for building UIs. Its core idea is components — reusable pieces of UI that manage their own state and re-render efficiently when data changes. React controls the DOM (the browser's representation of the page) and only updates what actually changed, rather than re-rendering the whole page. Created by Facebook, now the dominant frontend paradigm.

**TypeScript** is JavaScript with static types. Instead of discovering at runtime that you passed a string where a number was expected, TypeScript catches it at compile time. Every `.tsx` file in the project is TypeScript + JSX (React's syntax for writing HTML-like code in JavaScript).

**Tailwind CSS** is a utility-first CSS framework. Instead of writing CSS classes like `.card { padding: 16px; border-radius: 8px; }` and then applying `className="card"`, you write utility classes directly in the markup: `className="p-4 rounded-lg"`. Each class does one thing. It feels weird at first — your HTML gets verbose — but it eliminates the need to name things, prevents style conflicts, and keeps styles co-located with the components that use them. We're on Tailwind v4.

**shadcn/ui** is not a traditional component library (you don't `npm install` it as a dependency). Instead, it's a collection of copy-paste-able React components built on top of Radix UI. You run `npx shadcn@latest add button` and it drops a fully styled, accessible Button component into your `components/ui/` folder. You own the code and can customize it however you want. It uses Tailwind for styling and Radix UI for the headless accessibility primitives (keyboard navigation, focus management, ARIA attributes, etc.).

**Radix UI** provides unstyled, accessible UI primitives — things like dropdowns, dialogs, popovers, and tooltips that handle all the tricky accessibility and interaction behavior (keyboard nav, focus trapping, screen reader support) without imposing any visual design. shadcn/ui wraps these with Tailwind styles.

### How the Frontend Works

The app has two main pages:

1. **Home page** (`app/page.tsx`): A landing page with a hero image and a link to the explore view.

2. **Explore page** (`app/explore/page.tsx`): The main interface. Users can filter matches by rank (Challenger, Grandmaster, Master, Diamond, Emerald) and by champion (using a searchable command menu powered by `cmdk`). Results are paginated at 10 per page.

Data flows through **React server functions** (previously called "server actions" until Sept 2024). You mark a function with `"use server"` and it runs on the server, not in the browser. Client components can call these functions directly — no REST API, no GraphQL endpoint, no separate backend. It's a "backend for frontend" pattern. Our server function `fetchSynapseData()` in `server/azure-query.ts` connects to Azure Synapse using the `mssql` npm package and runs the SQL query.

When a match is displayed, the frontend looks up SHAP values from the precomputed `model/{region}_shap.json` file (keyed by matchId + player). The SHAP force plot is rendered as an SVG — an alluvial diagram with blue (helped) and red (hurt) arrows meeting at the predicted win probability.

Before sending match data to the client, we strip out the heavy stuff (timeline arrays, frame-by-frame metrics) to keep the payload small. Only the essential display data — KDA, champion, items, runes, rank, team objectives — gets sent.

**>> DEMO: the website itself <<**
