/**
 * Toggle - Reusable toggle switch component
 *
 * Features:
 * - Smooth color transition
 * - Multiple size variants (sm, md, lg)
 * - Disabled state
 * - Keyboard accessible
 * - Screen reader friendly
 *
 * Usage:
 *   <Toggle
 *     checked={isEnabled}
 *     onChange={(checked) => setIsEnabled(checked)}
 *     label="Enable notifications"
 *     size="md"
 *   />
 */

import { useId } from 'react';

// Size configurations with inline styles for thumb positioning
const sizeConfig = {
  sm: {
    trackClass: 'w-8 h-4',
    thumbSize: 12,
    thumbOffset: 2,
    thumbTranslate: 14,
  },
  md: {
    trackClass: 'w-11 h-6',
    thumbSize: 20,
    thumbOffset: 2,
    thumbTranslate: 22,
  },
  lg: {
    trackClass: 'w-14 h-7',
    thumbSize: 24,
    thumbOffset: 2,
    thumbTranslate: 28,
  },
};

export default function Toggle({
  checked,
  onChange,
  disabled = false,
  size = 'md',
  label = '',
  labelPosition = 'right',
  className = '',
}) {
  const id = useId();
  const config = sizeConfig[size] || sizeConfig.md;

  const handleChange = (e) => {
    if (!disabled && onChange) {
      onChange(e.target.checked);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      if (!disabled && onChange) {
        onChange(!checked);
      }
    }
  };

  // Track background color based on state
  const trackBgColor = disabled
    ? 'var(--color-border)'
    : checked
    ? 'var(--color-primary)'
    : 'var(--color-border)';

  const toggle = (
    <label
      className={`relative inline-flex items-center cursor-pointer ${
        disabled ? 'opacity-50 cursor-not-allowed' : ''
      }`}
    >
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        className="sr-only"
        aria-label={label || 'Toggle'}
      />
      {/* Track */}
      <div
        className={`${config.trackClass} rounded-full relative transition-colors duration-200`}
        style={{ backgroundColor: trackBgColor }}
      >
        {/* Thumb */}
        <div
          className="absolute bg-white rounded-full shadow-sm transition-transform duration-200"
          style={{
            width: config.thumbSize,
            height: config.thumbSize,
            top: config.thumbOffset,
            left: config.thumbOffset,
            transform: checked ? `translateX(${config.thumbTranslate}px)` : 'translateX(0)',
          }}
        />
      </div>
    </label>
  );

  if (!label) {
    return <div className={className}>{toggle}</div>;
  }

  return (
    <div
      className={`flex items-center gap-3 ${
        labelPosition === 'left' ? 'flex-row-reverse' : ''
      } ${className}`}
    >
      {toggle}
      <span
        className={`text-sm font-medium ${
          disabled ? 'text-theme-muted' : 'text-theme-secondary'
        }`}
        onClick={() => !disabled && onChange && onChange(!checked)}
      >
        {label}
      </span>
    </div>
  );
}

/**
 * ToggleCard - Toggle with card styling (like ConsentToggle)
 *
 * Usage:
 *   <ToggleCard
 *     icon={BellIcon}
 *     title="Push Notifications"
 *     description="Receive push notifications for important updates"
 *     checked={pushEnabled}
 *     onChange={setPushEnabled}
 *   />
 */
export function ToggleCard({
  icon: Icon,
  title,
  description,
  checked,
  onChange,
  disabled = false,
}) {
  return (
    <div
      className={`flex items-center justify-between p-4 border border-theme rounded-lg transition-colors ${
        disabled
          ? 'bg-theme-surface-elevated opacity-60'
          : 'hover:bg-theme-border-light bg-theme-surface'
      }`}
    >
      <div className="flex items-center gap-4">
        {Icon && (
          <div className="w-10 h-10 bg-theme-surface-elevated rounded-lg flex items-center justify-center">
            <Icon className="w-5 h-5 text-theme-muted" />
          </div>
        )}
        <div>
          <p className="font-medium text-theme">{title}</p>
          {description && (
            <p className="text-sm text-theme-muted">{description}</p>
          )}
        </div>
      </div>
      <Toggle
        checked={checked}
        onChange={onChange}
        disabled={disabled}
        size="md"
      />
    </div>
  );
}
