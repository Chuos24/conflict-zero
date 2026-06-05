import { renderHook, act } from '@testing-library/react';
import { useWindowSize } from '../useWindowSize';

describe('useWindowSize', () => {
  const originalInnerWidth = window.innerWidth;
  const originalInnerHeight = window.innerHeight;
  const originalAddEventListener = window.addEventListener;
  const originalRemoveEventListener = window.removeEventListener;

  beforeEach(() => {
    window.innerWidth = 1024;
    window.innerHeight = 768;
  });

  afterEach(() => {
    window.innerWidth = originalInnerWidth;
    window.innerHeight = originalInnerHeight;
    window.addEventListener = originalAddEventListener;
    window.removeEventListener = originalRemoveEventListener;
  });

  it('should return initial window dimensions', () => {
    const { result } = renderHook(() => useWindowSize());
    expect(result.current.width).toBe(1024);
    expect(result.current.height).toBe(768);
  });

  it('should identify desktop breakpoint', () => {
    window.innerWidth = 1024;
    const { result } = renderHook(() => useWindowSize());
    expect(result.current.isDesktop).toBe(true);
    expect(result.current.isMobile).toBe(false);
    expect(result.current.isTablet).toBe(false);
    expect(result.current.isWide).toBe(false);
  });

  it('should identify mobile breakpoint', () => {
    window.innerWidth = 767;
    const { result } = renderHook(() => useWindowSize());
    expect(result.current.isMobile).toBe(true);
    expect(result.current.isTablet).toBe(false);
    expect(result.current.isDesktop).toBe(false);
  });

  it('should identify tablet breakpoint', () => {
    window.innerWidth = 800;
    const { result } = renderHook(() => useWindowSize());
    expect(result.current.isTablet).toBe(true);
    expect(result.current.isMobile).toBe(false);
    expect(result.current.isDesktop).toBe(false);
  });

  it('should identify wide breakpoint', () => {
    window.innerWidth = 1440;
    const { result } = renderHook(() => useWindowSize());
    expect(result.current.isWide).toBe(true);
    expect(result.current.isDesktop).toBe(false);
  });

  it('should update on window resize', () => {
    const handlers = new Map();

    window.addEventListener = jest.fn((event, handler) => {
      if (event === 'resize') {
        handlers.set('resize', handler);
      }
    });

    window.removeEventListener = jest.fn();

    const { result } = renderHook(() => useWindowSize());

    expect(result.current.width).toBe(1024);

    window.innerWidth = 500;
    window.innerHeight = 600;

    const resizeHandler = handlers.get('resize');
    if (resizeHandler) {
      act(() => {
        resizeHandler();
      });
    }

    expect(result.current.width).toBe(500);
    expect(result.current.height).toBe(600);
    expect(result.current.isMobile).toBe(true);
  });

  it('should remove event listener on cleanup', () => {
    const handlers = new Map();
    window.addEventListener = jest.fn((event, handler) => {
      handlers.set(event, handler);
    });
    window.removeEventListener = jest.fn();

    const { unmount } = renderHook(() => useWindowSize());
    unmount();
    expect(window.removeEventListener).toHaveBeenCalledWith('resize', handlers.get('resize'));
  });
});
