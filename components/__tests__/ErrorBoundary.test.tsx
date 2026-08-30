import type React from 'react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ErrorBoundary } from '../ErrorBoundary.tsx';

const Bomb: React.FC = () => {
  throw new Error('boom');
};

describe('ErrorBoundary', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders children normally when nothing throws', () => {
    render(
      <ErrorBoundary>
        <div>Barka da zuwa</div>
      </ErrorBoundary>
    );
    expect(screen.getByText('Barka da zuwa')).toBeInTheDocument();
  });

  it('catches a render error and shows the fallback instead of a blank/crashed tree', () => {
    // React logs the caught error to the console by default -- silence it so
    // this expected-error test doesn't look like a real failure in output.
    vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <ErrorBoundary>
        <Bomb />
      </ErrorBoundary>
    );

    expect(screen.getByText('Wani kuskure ya faru')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Reload/i })).toBeInTheDocument();
    // The thing that actually crashed must not be in the tree -- this is
    // the regression this component exists to prevent: without it, a
    // render error white-screens the whole app instead of showing this.
    expect(screen.queryByText('Barka da zuwa')).not.toBeInTheDocument();
  });
});
