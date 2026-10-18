import PropTypes from "prop-types";
export default function PageIntro({
  title,
  description,
  eyebrow = "QuantNest",
}) {
  return (
    <header className="mb-7 max-w-3xl">
      <p className="mb-3 text-xs font-semibold uppercase tracking-[.2em] text-brand">
        {eyebrow}
      </p>
      <h1 className="text-3xl font-semibold leading-tight tracking-[-.045em] sm:text-4xl lg:text-5xl">
        {title}
      </h1>
      {description && (
        <p className="mt-4 text-base leading-7 text-muted-foreground sm:text-lg">
          {description}
        </p>
      )}
    </header>
  );
}
PageIntro.propTypes = {
  title: PropTypes.string.isRequired,
  description: PropTypes.string,
  eyebrow: PropTypes.string,
};
