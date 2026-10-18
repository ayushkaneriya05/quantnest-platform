import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowRight, BookOpen, Search } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useEnums } from "@/shared/context/EnumsContext";
import WorkspaceState from "@/shared/components/WorkspaceState";
import { Input } from "@/shared/components/ui/input";
import PageIntro from "./PageIntro";
import NotFoundPage from "@/pages/NotFoundPage";

const documents = Object.entries(
  import.meta.glob("./content/docs/*.md", {
    query: "?raw",
    import: "default",
    eager: true,
  }),
)
  .map(([path, source]) => {
    const frontmatter = source.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n/);
    const fields = Object.fromEntries(
      (frontmatter?.[1] || "")
        .split(/\r?\n/)
        .filter((line) => line.includes(":"))
        .map((line) => {
          const colon = line.indexOf(":");
          return [line.slice(0, colon), line.slice(colon + 1).trim()];
        }),
    );
    return {
      slug: path.split("/").at(-1).replace(".md", ""),
      ...fields,
      body: source.slice(frontmatter?.[0].length || 0),
    };
  })
  .sort((a, b) => Number(a.order) - Number(b.order));

function BuilderReference() {
  const { enums: metadata, loading, error, refreshEnums } = useEnums();
  if (loading || error)
    return (
      <WorkspaceState
        loading={loading}
        error={
          !loading && error
            ? "The builder reference could not load. Please try again."
            : ""
        }
        onRetry={!loading && error ? refreshEnums : undefined}
      />
    );
  return (
    <article className="site-doc-article">
      <h2 className="text-2xl font-semibold">Timeframes</h2>
      <p className="my-4 text-sm leading-7 text-muted-foreground">
        Choose a default timeframe for your strategy, then set a different
        timeframe on an individual condition when your idea needs one.
      </p>
      <div className="mb-10 flex flex-wrap gap-2">
        {metadata.CandleTimeframe.map((item) => (
          <span
            className="rounded-full border px-3 py-2 text-sm"
            key={item.value}
          >
            {item.label}
          </span>
        ))}
      </div>
      <h2 className="text-2xl font-semibold">Available rule inputs</h2>
      <p className="my-4 text-sm leading-7 text-muted-foreground">
        Use these supported inputs when defining a condition. Open the parameter
        settings in the builder to choose the period or other required values.
      </p>
      <ul className="grid gap-3 sm:grid-cols-2">
        {metadata.OperandType.map((item) => (
          <li className="rounded-xl border p-4 text-sm" key={item.value}>
            {item.label}
          </li>
        ))}
      </ul>
      <p className="mt-6 text-sm leading-7 text-muted-foreground">
        A timeframe or input listed here does not add a new market. Initial
        strategy execution supports NSE cash stocks.{" "}
        <Link className="text-brand underline" to="/docs/builder/">
          Read the strategy-building guide
        </Link>{" "}
        for the full workflow.
      </p>
    </article>
  );
}

export default function Documentation() {
  const { document: slug } = useParams();
  const [search, setSearch] = useState("");
  const doc = documents.find((item) => item.slug === slug);
  const reference = slug === "reference";
  const title = reference
    ? "Builder reference"
    : doc?.title || "Your QuantNest guide";
  const filtered = documents.filter((item) =>
    `${item.title} ${item.body}`
      .toLowerCase()
      .includes(search.trim().toLowerCase()),
  );
  const currentIndex = documents.indexOf(doc);
  useEffect(() => {
    document.title = `${title} · QuantNest`;
    const description = document.querySelector('meta[name="description"]');
    if (description)
      description.content =
        doc?.description ||
        "Practical guides to research, rules, backtesting, simulated execution and review in QuantNest.";
  }, [title, doc]);
  if (slug && !reference && !doc) return <NotFoundPage />;
  return (
    <>
      <PageIntro
        title={title}
        description={
          doc?.description ||
          "Choose a task, follow the steps and understand the settings behind your results."
        }
        eyebrow="User documentation"
      />
      <div className="grid items-start gap-8 lg:grid-cols-[260px_1fr]">
        <aside className="site-doc-nav rounded-2xl border bg-card p-5 lg:sticky lg:top-24">
          <label className="mb-4 block">
            <span className="mb-2 block text-xs font-medium text-muted-foreground">
              Search the guides
            </span>
            <span className="relative block">
              <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-muted-foreground" />
              <Input
                aria-label="Search documentation"
                placeholder="Find a topic…"
                className="pl-9"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </span>
          </label>
          <nav
            aria-label="Documentation"
            className="max-h-80 space-y-1 overflow-y-auto scrollbar-thin lg:max-h-[calc(100dvh-250px)]"
          >
            {filtered.map((item) => (
              <Link
                key={item.slug}
                to={`/docs/${item.slug}/`}
                aria-current={item === doc ? "page" : undefined}
                className={`block rounded-lg px-3 py-2.5 text-sm ${item === doc ? "bg-brand/10 font-medium text-brand" : "text-muted-foreground hover:bg-accent hover:text-foreground"}`}
              >
                {item.title}
              </Link>
            ))}
            {!filtered.length && (
              <p className="px-3 py-3 text-sm text-muted-foreground">
                No guides match. Try a shorter search.
              </p>
            )}
            {(!search ||
              "builder reference timeframes indicators operands".includes(
                search.toLowerCase(),
              )) && (
              <Link
                aria-current={reference ? "page" : undefined}
                className={`block rounded-lg px-3 py-2.5 text-sm ${reference ? "bg-brand/10 font-medium text-brand" : "text-muted-foreground hover:bg-accent"}`}
                to="/docs/reference/"
              >
                Builder reference
              </Link>
            )}
          </nav>
        </aside>
        <div className="min-w-0">
          {doc ? (
            <>
              <article className="site-doc-article site-prose max-w-3xl">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {doc.body}
                </ReactMarkdown>
              </article>
              <nav
                className="mt-10 flex flex-wrap justify-between gap-4 border-t pt-6"
                aria-label="Adjacent guides"
              >
                {documents[currentIndex - 1] && (
                  <Link
                    className="text-sm text-brand"
                    to={`/docs/${documents[currentIndex - 1].slug}/`}
                  >
                    ← {documents[currentIndex - 1].title}
                  </Link>
                )}
                {documents[currentIndex + 1] && (
                  <Link
                    className="ml-auto text-sm text-brand"
                    to={`/docs/${documents[currentIndex + 1].slug}/`}
                  >
                    {documents[currentIndex + 1].title} →
                  </Link>
                )}
              </nav>
            </>
          ) : reference ? (
            <BuilderReference />
          ) : (
            <div className="grid gap-5 md:grid-cols-2">
              {filtered.map((item) => (
                <Link
                  className="site-card group"
                  key={item.slug}
                  to={`/docs/${item.slug}/`}
                >
                  <BookOpen className="h-5 w-5 text-brand" />
                  <h2 className="mt-5 font-semibold">{item.title}</h2>
                  <p className="my-4 text-sm leading-7 text-muted-foreground">
                    {item.description}
                  </p>
                  <span className="inline-flex items-center gap-2 text-sm text-brand">
                    Read guide
                    <ArrowRight className="h-4 w-4" />
                  </span>
                </Link>
              ))}
              {!filtered.length && (
                <p className="text-sm text-muted-foreground">
                  No matching guides. Clear the search to browse every topic.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
