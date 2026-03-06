import { describe, it, expect } from 'vitest';

describe('Hotel Pricing Calculation', () => {
  it('should multiply nightly rate by number of nights', () => {
    const nightlyRate = 4319.72;
    const nights = 7;
    const totalPrice = nightlyRate * (nights || 1);

    expect(totalPrice).toBeCloseTo(30238.04, 2);
    expect(totalPrice).not.toBe(nightlyRate);
  });

  it('should fallback to 1 night when nights is 0', () => {
    const nightlyRate = 5000;
    const nights = 0;
    const totalPrice = nightlyRate * (nights || 1);

    expect(totalPrice).toBe(5000);
  });

  it('should handle undefined nights gracefully', () => {
    const nightlyRate = 3000;
    const nights = undefined;
    const totalPrice = nightlyRate * (nights || 1);

    expect(totalPrice).toBe(3000);
  });

  it('should handle null nights gracefully', () => {
    const nightlyRate = 4000;
    const nights = null;
    const totalPrice = nightlyRate * (nights || 1);

    expect(totalPrice).toBe(4000);
  });

  it('should compute correct total for multi-night stay', () => {
    const nightlyRate = 2500;
    const nights = 14;
    const totalPrice = nightlyRate * (nights || 1);

    expect(totalPrice).toBe(35000);
  });
});
