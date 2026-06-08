import { render, screen, fireEvent } from '@testing-library/react';
import Card, { StatCard } from '../Card';
import { Search, Users } from 'lucide-react';

describe('Card', () => {
  it('renders with children', () => {
    render(
      <Card>
        <p>Card content</p>
      </Card>
    );
    expect(screen.getByText('Card content')).toBeInTheDocument();
  });

  it('renders with title and icon', () => {
    render(
      <Card title="Test Card" icon={<Search data-testid="icon" />}>
        <p>Content</p>
      </Card>
    );
    expect(screen.getByText('Test Card')).toBeInTheDocument();
    expect(screen.getByTestId('icon')).toBeInTheDocument();
  });

  it('renders with subtitle', () => {
    render(
      <Card title="Test" subtitle="Subtitle text">
        <p>Content</p>
      </Card>
    );
    expect(screen.getByText('Subtitle text')).toBeInTheDocument();
  });

  it('renders with footer', () => {
    render(
      <Card footer={<button>Action</button>}>
        <p>Content</p>
      </Card>
    );
    expect(screen.getByText('Action')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <Card className="custom-class">
        <p>Content</p>
      </Card>
    );
    expect(container.firstChild).toHaveClass('custom-class');
  });

  it('renders without padding when noPadding is true', () => {
    const { container } = render(
      <Card noPadding>
        <p>Content</p>
      </Card>
    );
    // The inner div should not have p-6 class
    const innerDiv = container.querySelector('div > div');
    expect(innerDiv).not.toHaveClass('p-6');
  });
});

describe('StatCard', () => {
  it('renders title and value', () => {
    render(
      <StatCard title="Total Users" value="1,234" icon={<Users data-testid="icon" />} />
    );
    expect(screen.getByText('Total Users')).toBeInTheDocument();
    expect(screen.getByText('1,234')).toBeInTheDocument();
  });

  it('renders change indicator', () => {
    render(
      <StatCard
        title="Revenue"
        value="$10K"
        change="+12%"
        changeType="positive"
        icon={<Users data-testid="icon" />}
      />
    );
    expect(screen.getByText('+12%')).toBeInTheDocument();
    expect(screen.getByText('+12%')).toHaveClass('bg-emerald-50');
  });

  it('renders negative change', () => {
    render(
      <StatCard
        title="Churn"
        value="2%"
        change="-5%"
        changeType="negative"
        icon={<Users data-testid="icon" />}
      />
    );
    expect(screen.getByText('-5%')).toHaveClass('bg-rose-50');
  });

  it('renders neutral change', () => {
    render(
      <StatCard
        title="Status"
        value="OK"
        change="0%"
        changeType="neutral"
        icon={<Users data-testid="icon" />}
      />
    );
    expect(screen.getByText('0%')).toHaveClass('bg-slate-50');
  });
});
