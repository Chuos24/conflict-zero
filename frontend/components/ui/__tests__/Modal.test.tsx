import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Modal, { ConfirmModal } from '../Modal';
import Button from '../Button';

describe('Modal', () => {
  it('renders when isOpen is true', () => {
    render(
      <Modal isOpen={true} onClose={() => {}} title="Test Modal">
        <p>Modal content</p>
      </Modal>
    );
    expect(screen.getByText('Test Modal')).toBeInTheDocument();
    expect(screen.getByText('Modal content')).toBeInTheDocument();
  });

  it('does not render when isOpen is false', () => {
    const { container } = render(
      <Modal isOpen={false} onClose={() => {}} title="Test Modal">
        <p>Modal content</p>
      </Modal>
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('calls onClose when close button is clicked', () => {
    const onClose = jest.fn();
    render(
      <Modal isOpen={true} onClose={onClose} title="Test">
        <p>Content</p>
      </Modal>
    );
    const closeButton = screen.getByRole('button', { name: 'close' });
    fireEvent.click(closeButton);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when overlay is clicked', () => {
    const onClose = jest.fn();
    render(
      <Modal isOpen={true} onClose={onClose} closeOnOverlayClick={true}>
        <p>Content</p>
      </Modal>
    );
    const overlay = screen.getByRole('dialog').parentElement?.firstChild;
    if (overlay) {
      fireEvent.click(overlay);
      expect(onClose).toHaveBeenCalledTimes(1);
    }
  });

  it('does not close on overlay click when disabled', () => {
    const onClose = jest.fn();
    render(
      <Modal isOpen={true} onClose={onClose} closeOnOverlayClick={false}>
        <p>Content</p>
      </Modal>
    );
    const overlay = screen.getByRole('dialog').parentElement?.firstChild;
    if (overlay) {
      fireEvent.click(overlay);
      expect(onClose).not.toHaveBeenCalled();
    }
  });

  it('renders with description', () => {
    render(
      <Modal isOpen={true} onClose={() => {}} title="Test" description="Description text">
        <p>Content</p>
      </Modal>
    );
    expect(screen.getByText('Description text')).toBeInTheDocument();
  });

  it('renders with footer', () => {
    render(
      <Modal isOpen={true} onClose={() => {}} footer={<Button>Action</Button>}>
        <p>Content</p>
      </Modal>
    );
    expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument();
  });

  it('renders with different sizes', () => {
    const { rerender } = render(
      <Modal isOpen={true} onClose={() => {}} size="sm">
        <p>Content</p>
      </Modal>
    );
    let dialog = screen.getByRole('dialog');
    expect(dialog).toHaveClass('max-w-sm');

    rerender(
      <Modal isOpen={true} onClose={() => {}} size="lg">
        <p>Content</p>
      </Modal>
    );
    dialog = screen.getByRole('dialog');
    expect(dialog).toHaveClass('max-w-lg');
  });
});

describe('ConfirmModal', () => {
  it('renders with confirm and cancel buttons', () => {
    const onConfirm = jest.fn();
    const onClose = jest.fn();
    render(
      <ConfirmModal
        isOpen={true}
        onClose={onClose}
        onConfirm={onConfirm}
        title="Confirm?"
        description="Are you sure?"
      />
    );
    expect(screen.getByText('Confirm?')).toBeInTheDocument();
    // Description is rendered in header, not in body
    expect(screen.getByRole('button', { name: 'Confirmar' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeInTheDocument();
  });

  it('calls onConfirm when confirm button is clicked', () => {
    const onConfirm = jest.fn();
    const onClose = jest.fn();
    render(
      <ConfirmModal
        isOpen={true}
        onClose={onClose}
        onConfirm={onConfirm}
        title="Confirm?"
        description="Are you sure?"
      />
    );
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar' }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when cancel button is clicked', () => {
    const onConfirm = jest.fn();
    const onClose = jest.fn();
    render(
      <ConfirmModal
        isOpen={true}
        onClose={onClose}
        onConfirm={onConfirm}
        title="Confirm?"
        description="Are you sure?"
      />
    );
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
