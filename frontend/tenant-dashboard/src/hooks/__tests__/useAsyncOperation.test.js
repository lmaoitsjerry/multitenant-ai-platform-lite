/**
 * Tests for useAsyncOperation hook and extractErrorMessage utility.
 *
 * Note: useAsyncOperation is a React hook — testing it properly requires
 * @testing-library/react (renderHook). Since that's not installed, we test
 * the extractErrorMessage utility function directly.
 */
import { describe, test, expect } from 'vitest';
import { extractErrorMessage } from '../useAsyncOperation';

describe('extractErrorMessage', () => {
  test('extracts from ServiceError response format', () => {
    const error = {
      response: { data: { detail: { error: 'KB unavailable', service: 'kb' } } },
    };
    expect(extractErrorMessage(error)).toBe('KB unavailable');
  });

  test('extracts from simple detail string', () => {
    const error = { response: { data: { detail: 'Not found' } } };
    expect(extractErrorMessage(error)).toBe('Not found');
  });

  test('extracts from message field', () => {
    const error = { response: { data: { message: 'Rate limited' } } };
    expect(extractErrorMessage(error)).toBe('Rate limited');
  });

  test('extracts from error field', () => {
    const error = { response: { data: { error: 'Bad request' } } };
    expect(extractErrorMessage(error)).toBe('Bad request');
  });

  test('handles network error', () => {
    const error = { code: 'ERR_NETWORK' };
    expect(extractErrorMessage(error)).toContain('connect');
  });

  test('handles timeout error', () => {
    const error = { code: 'ECONNABORTED' };
    expect(extractErrorMessage(error)).toContain('timed out');
  });

  test('extracts from standard Error object', () => {
    expect(extractErrorMessage(new Error('Something broke'))).toBe('Something broke');
  });

  test('handles string error', () => {
    expect(extractErrorMessage('plain string error')).toBe('plain string error');
  });

  test('uses fallback for null', () => {
    expect(extractErrorMessage(null, 'Custom fallback')).toBe('Custom fallback');
  });

  test('uses fallback for undefined', () => {
    expect(extractErrorMessage(undefined, 'Fallback')).toBe('Fallback');
  });

  test('uses fallback for empty object', () => {
    expect(extractErrorMessage({}, 'Custom fallback')).toBe('Custom fallback');
  });

  test('uses default fallback when none provided', () => {
    expect(extractErrorMessage({})).toBe('An error occurred');
  });

  test('prefers detail.error over detail string', () => {
    const error = {
      response: {
        data: {
          detail: { error: 'Specific error', service: 'kb' },
          message: 'Generic message',
        },
      },
    };
    expect(extractErrorMessage(error)).toBe('Specific error');
  });

  test('handles error with only response but no data', () => {
    const error = { response: {} };
    expect(extractErrorMessage(error, 'fallback')).toBe('fallback');
  });

  test('handles axios error with response.data but no known fields', () => {
    const error = { response: { data: { unknown_field: 'value' } } };
    expect(extractErrorMessage(error, 'fallback')).toBe('fallback');
  });
});
