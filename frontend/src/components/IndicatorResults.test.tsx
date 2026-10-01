import { describe, expect, it } from 'vitest'
import { formatIndicatorValue } from './IndicatorResults'
describe('lossless indicator units', () => {
  it('scales fractions exactly while preserving ROE and volume ratio units', () => {
    expect(formatIndicatorValue('0.123456789012345678901', 'fraction')).toBe('12.3456789012345678901%')
    expect(formatIndicatorValue('12.3', 'percentage_value')).toBe('12.3%')
    expect(formatIndicatorValue('2', 'ratio')).toBe('2×')
    expect(formatIndicatorValue('0.5', 'dimensionless')).toBe('0.5')
    expect(formatIndicatorValue('-0.2', 'fraction')).toBe('-20%')
    expect(formatIndicatorValue('0', 'fraction')).toBe('0%')
    expect(formatIndicatorValue(null, 'fraction')).toBe('Unavailable')
  })
  it('preserves tiny and huge scientific decimals without Number conversion', () => {
    expect(formatIndicatorValue('1e-10000', 'fraction')).toBe('1e-9998%')
    expect(formatIndicatorValue('1e10000', 'fraction')).toBe('1e10002%')
    expect(formatIndicatorValue('1.23e-4', 'fraction')).toBe('0.0123%')
    expect(formatIndicatorValue('12345', 'index_points')).toBe('12345 points')
    expect(formatIndicatorValue('12345', 'CNY')).toBe('12345 CNY')
  })
})
