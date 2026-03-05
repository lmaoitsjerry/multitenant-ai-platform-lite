import { forwardRef } from 'react';

/**
 * Unified Button Component
 *
 * Usage:
 *   <Button>Primary Button</Button>
 *   <Button variant="secondary">Secondary</Button>
 *   <Button variant="danger" size="sm">Delete</Button>
 *   <Button variant="ghost" asChild><Link to="/">Home</Link></Button>
 */

const variants = {
  primary: `
    bg-[var(--color-primary)] hover:bg-[var(--color-primary-dark)]
    text-white shadow-sm hover:shadow
  `,
  secondary: `
    bg-white hover:bg-gray-50
    text-gray-700 border border-gray-300 shadow-sm
  `,
  danger: `
    bg-red-600 hover:bg-red-700
    text-white shadow-sm
  `,
  success: `
    bg-emerald-600 hover:bg-emerald-700
    text-white shadow-sm
  `,
  ghost: `
    hover:bg-gray-100
    text-gray-600
  `,
  link: `
    text-[var(--color-primary)] hover:text-[var(--color-primary-dark)]
    underline-offset-4 hover:underline
  `,
  outline: `
    border border-[var(--color-primary)]
    text-[var(--color-primary)] hover:bg-[var(--color-primary)]/10
  `,
};

const sizes = {
  xs: 'px-2 py-1 text-xs rounded',
  sm: 'px-3 py-1.5 text-sm rounded-md',
  md: 'px-4 py-2 text-sm rounded-lg',
  lg: 'px-6 py-3 text-base rounded-lg',
  xl: 'px-8 py-4 text-lg rounded-xl',
};

const Button = forwardRef(
  (
    {
      variant = 'primary',
      size = 'md',
      className = '',
      disabled = false,
      loading = false,
      children,
      asChild = false,
      ...props
    },
    ref
  ) => {
    const baseStyles = `
      inline-flex items-center justify-center font-medium
      transition-colors duration-150
      focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:ring-offset-2
      disabled:opacity-50 disabled:cursor-not-allowed
    `;

    const variantStyles = variants[variant] || variants.primary;
    const sizeStyles = sizes[size] || sizes.md;

    const combinedClassName = `${baseStyles} ${variantStyles} ${sizeStyles} ${className}`
      .replace(/\s+/g, ' ')
      .trim();

    if (asChild) {
      // For wrapping other components like Link
      return children;
    }

    return (
      <button
        ref={ref}
        className={combinedClassName}
        disabled={disabled || loading}
        {...props}
      >
        {loading && (
          <svg
            className="animate-spin -ml-1 mr-2 h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';

export { Button };
export default Button;
