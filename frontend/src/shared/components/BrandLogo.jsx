import PropTypes from 'prop-types';
import { useTheme } from '@/shared/context/theme';
import { cn } from '@/shared/lib/utils';

/** One approved identity for public pages, authentication and the workspace. */
export default function BrandLogo({ className, animated = false }) {
  const { resolvedTheme } = useTheme();
  return (
    <img
      src={`/brand/quantnest-${resolvedTheme}${animated ? '-animated' : ''}.svg`}
      alt="QuantNest"
      width={400}
      height={72}
      className={cn('block h-auto max-w-full object-contain', className)}
      draggable={false}
    />
  );
}

BrandLogo.propTypes = {
  className: PropTypes.string,
  animated: PropTypes.bool,
};
