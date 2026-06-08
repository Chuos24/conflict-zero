import { render, screen, fireEvent, act } from '@testing-library/react';
import { Toast, ToastContainer, useToast } from '../Toast';

describe('Toast', () => {
  const mockOnClose = jest.fn();

  beforeEach(() => {
    jest.useFakeTimers();
    mockOnClose.mockClear();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('renders with default props', () => {
    render(<Toast id="1" message="Test message" onClose={mockOnClose} />);
    expect(screen.getByText('Test message')).toBeInTheDocument();
    expect(screen.getByText('ℹ')).toBeInTheDocument();
  });

  it('renders with different types', () => {
    const { rerender } = render(<Toast id="1" message="Success" type="success" onClose={mockOnClose} />);
    expect(screen.getByText('✓')).toBeInTheDocument();

    rerender(<Toast id="1" message="Error" type="error" onClose={mockOnClose} />);
    expect(screen.getByText('✕')).toBeInTheDocument();

    rerender(<Toast id="1" message="Warning" type="warning" onClose={mockOnClose} />);
    expect(screen.getByText('⚠')).toBeInTheDocument();
  });

  it('auto-dismisses after duration', () => {
    render(<Toast id="1" message="Auto dismiss" duration={1000} onClose={mockOnClose} />);
    
    act(() => {
      jest.advanceTimersByTime(50); // Show animation
    });
    
    act(() => {
      jest.advanceTimersByTime(1000); // Duration
    });
    
    act(() => {
      jest.advanceTimersByTime(300); // Exit animation
    });
    
    expect(mockOnClose).toHaveBeenCalledWith('1');
  });

  it('closes on click X button', () => {
    render(<Toast id="1" message="Close me" onClose={mockOnClose} />);
    
    const closeButton = screen.getByRole('button');
    fireEvent.click(closeButton);
    
    act(() => {
      jest.advanceTimersByTime(300); // Exit animation
    });
    
    expect(mockOnClose).toHaveBeenCalledWith('1');
  });

  it('applies correct styles for success type', () => {
    const { container } = render(<Toast id="1" message="Success" type="success" onClose={mockOnClose} />);
    const toast = container.firstChild as HTMLElement;
    expect(toast.className).toContain('bg-emerald-50');
    expect(toast.className).toContain('border-emerald-200');
    expect(toast.className).toContain('text-emerald-800');
  });

  it('applies correct styles for error type', () => {
    const { container } = render(<Toast id="1" message="Error" type="error" onClose={mockOnClose} />);
    const toast = container.firstChild as HTMLElement;
    expect(toast.className).toContain('bg-rose-50');
    expect(toast.className).toContain('border-rose-200');
    expect(toast.className).toContain('text-rose-800');
  });

  it('has hidden state initially and visible after animation', () => {
    const { container } = render(<Toast id="1" message="Test" onClose={mockOnClose} />);
    const toast = container.firstChild as HTMLElement;
    
    // Initially hidden (opacity-0, translate-x-full)
    expect(toast.className).toContain('opacity-0');
    expect(toast.className).toContain('translate-x-full');
    
    act(() => {
      jest.advanceTimersByTime(50);
    });
    
    // After animation, visible
    expect(toast.className).toContain('opacity-100');
    expect(toast.className).toContain('translate-x-0');
  });
});

describe('ToastContainer', () => {
  it('renders multiple toasts', () => {
    const toasts = [
      { id: '1', message: 'First toast', type: 'success' as const },
      { id: '2', message: 'Second toast', type: 'error' as const },
    ];
    
    render(<ToastContainer toasts={toasts} onClose={jest.fn()} />);
    
    expect(screen.getByText('First toast')).toBeInTheDocument();
    expect(screen.getByText('Second toast')).toBeInTheDocument();
  });

  it('renders empty container when no toasts', () => {
    const { container } = render(<ToastContainer toasts={[]} onClose={jest.fn()} />);
    // Container should be in the document but empty
    expect(container).toBeInTheDocument();
  });

  it('positions toasts at bottom right', () => {
    const toasts = [{ id: '1', message: 'Position test', type: 'info' as const }];
    
    const { container } = render(<ToastContainer toasts={toasts} onClose={jest.fn()} />);
    const portal = document.querySelector('.fixed.bottom-4.right-4');
    expect(portal).toBeInTheDocument();
  });
});

describe('useToast hook', () => {
  it('adds and removes toasts', () => {
    let hookResult: ReturnType<typeof useToast>;
    
    function TestComponent() {
      hookResult = useToast();
      return (
        <div>
          <button onClick={() => hookResult.addToast('Test', 'success')}>Add</button>
          <button onClick={() => hookResult.removeToast(hookResult.toasts[0]?.id)}>Remove</button>
          <span data-testid="count">{hookResult.toasts.length}</span>
        </div>
      );
    }
    
    render(<TestComponent />);
    
    // Initially empty
    expect(screen.getByTestId('count')).toHaveTextContent('0');
    
    // Add toast
    fireEvent.click(screen.getByText('Add'));
    expect(screen.getByTestId('count')).toHaveTextContent('1');
    
    // Remove toast
    fireEvent.click(screen.getByText('Remove'));
    expect(screen.getByTestId('count')).toHaveTextContent('0');
  });

  it('generates unique ids for each toast', () => {
    let hookResult: ReturnType<typeof useToast>;
    
    function TestComponent() {
      hookResult = useToast();
      return (
        <div>
          <button onClick={() => hookResult.addToast('Test')}>Add</button>
          <span data-testid="ids">{hookResult.toasts.map(t => t.id).join(',')}</span>
        </div>
      );
    }
    
    render(<TestComponent />);
    
    fireEvent.click(screen.getByText('Add'));
    fireEvent.click(screen.getByText('Add'));
    
    const ids = screen.getByTestId('ids').textContent?.split(',') || [];
    expect(ids.length).toBe(2);
    expect(ids[0]).not.toBe(ids[1]);
  });
});
