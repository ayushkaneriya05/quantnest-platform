import PropTypes from "prop-types";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/shared/lib/utils";

function MarkdownTable({ children }) {
  return <div className="scrollbar-thin-theme overflow-x-auto rounded-lg border border-border">
    <table className="w-full text-left text-sm">{children}</table>
  </div>;
}
MarkdownTable.propTypes = { children: PropTypes.node };

function MarkdownCodeBlock({ children }) {
  return <pre className="scrollbar-thin-theme">{children}</pre>;
}
MarkdownCodeBlock.propTypes = { children: PropTypes.node };

const components = { table: MarkdownTable, pre: MarkdownCodeBlock };

export default function Markdown({ children, className, renderLink }) {
  return <div className={cn(
    "space-y-3 text-sm leading-relaxed text-foreground [overflow-wrap:anywhere] [&>:first-child]:mt-0",
    "[&_h1]:text-xl [&_h2]:text-lg [&_h3]:text-base [&_:is(h1,h2,h3,h4,h5,h6)]:mt-6 [&_:is(h1,h2,h3,h4,h5,h6)]:font-semibold [&_:is(h1,h2,h3,h4,h5,h6)]:text-foreground",
    "[&_ul]:list-disc [&_ol]:list-decimal [&_:is(ul,ol)]:pl-6 [&_li]:my-1 [&_li>p]:my-1 [&_strong]:font-semibold [&_strong]:text-foreground",
    "[&_a]:text-indigo-700 dark:[&_a]:text-indigo-300 [&_a]:underline [&_a]:underline-offset-4 [&_blockquote]:border-l-2 [&_blockquote]:border-border [&_blockquote]:pl-4 [&_blockquote]:text-muted-foreground [&_hr]:border-border",
    "[&_code]:rounded [&_code]:bg-secondary [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-xs [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:bg-background [&_pre]:p-4 [&_pre_code]:bg-transparent [&_pre_code]:p-0",
    "[&_thead]:bg-card [&_:is(th,td)]:border-b [&_:is(th,td)]:border-border [&_:is(th,td)]:px-4 [&_:is(th,td)]:py-3 [&_:is(th,td)]:align-top",
    className,
  )}>
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={renderLink ? { ...components, a: renderLink } : components} skipHtml disallowedElements={["img"]}>
      {children}
    </ReactMarkdown>
  </div>;
}

Markdown.propTypes = { children: PropTypes.string.isRequired, className: PropTypes.string, renderLink: PropTypes.func };
