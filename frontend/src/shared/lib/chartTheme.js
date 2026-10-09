// Canvas charts need resolved colors; SVG charts can use CSS variables directly.
export const chartTooltipProps = {
  contentStyle: {
    backgroundColor: "hsl(var(--popover))",
    color: "hsl(var(--popover-foreground))",
    border: "1px solid hsl(var(--border))",
    borderRadius: 8,
  },
  labelStyle: { color: "hsl(var(--popover-foreground))" },
  itemStyle: { color: "hsl(var(--popover-foreground))" },
};

export function getChartPalette() {
  const styles = getComputedStyle(document.documentElement);
  const read = (name) => styles.getPropertyValue(`--chart-${name}`).trim();
  return { background: read("background"), text: read("text"), grid: read("grid-color"), border: read("border"), up: read("up"), down: read("down"), line: read("line-color") };
}
