import PropTypes from 'prop-types';
import { cn } from '@/shared/lib/utils';

/** The woven emblem: two bands gather around the central seed. */
export function LoaderMark({ className, size, ...props }) {
  return <svg {...props} viewBox="0 0 64 64" width={size} height={size}
    className={cn('brand-loader inline-block h-5 w-5 shrink-0 text-brand', className)}
    aria-hidden="true" focusable="false" fill="currentColor">
    <g transform="translate(32 32) rotate(18) scale(.94) translate(-32 -32)">
      <path className="brand-loader-band brand-loader-band-a" d="M23 11C27 5 32 3 37 4L29 18L13 44C11 48 13 50 17 50H27L21 59H17C6 59 1 49 6 39Z" />
      <path className="brand-loader-band brand-loader-band-b" d="M42 6C43 7 44 8 45 10L60 39C65 49 59 59 48 59H28L34 50H48C52 50 54 47 52 43L36 15Z" />
      <path className="brand-loader-seed" d="M27 42C26 34 31 30 39 30C40 38 35 43 27 42Z" />
    </g>
  </svg>;
}

LoaderMark.propTypes = { className: PropTypes.string, size: PropTypes.number };

/** One loading state for routes, panels and compact inline messages. */
export function GlobalLoader({ text = 'Loading…', fullHeight = true, inline = false, className }) {
  return <span role="status" aria-live="polite" aria-atomic="true"
    className={cn('text-sm text-muted-foreground', inline
      ? 'inline-flex items-center gap-2'
      : `flex w-full flex-col items-center justify-center gap-4 p-6 ${fullHeight ? 'min-h-48 flex-1' : 'py-8'}`, className)}>
    <LoaderMark className={inline ? 'h-4 w-4' : 'h-12 w-12'} />
    <span>{text}</span>
  </span>;
}

GlobalLoader.propTypes = {
  text: PropTypes.string,
  fullHeight: PropTypes.bool,
  inline: PropTypes.bool,
  className: PropTypes.string,
};
