import '@testing-library/jest-dom/vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import raw from '../../../contracts/fixtures/evaluation.json';
import type { Evaluation } from '../api/contracts.generated';
import { DashboardViews } from '../components/DashboardViews';

afterEach(cleanup);
const evaluation = raw as Evaluation;

test('defaults to Executive View and exposes four API-backed CFO summaries', () => {
  render(<DashboardViews evaluation={evaluation} inspected="cpu_migration" onInspect={vi.fn()} onEvidence={vi.fn()} />);
  expect(screen.getByRole('tab', { name: 'Executive View' })).toHaveAttribute('aria-selected', 'true');
  expect(screen.getByRole('heading', { name: 'Observed GPU spend' })).toBeVisible();
  expect(screen.getByRole('heading', { name: 'Recoverable cost range' })).toBeVisible();
  expect(screen.getByRole('heading', { name: 'Gap to the 20% target' })).toBeVisible();
  expect(screen.getByRole('heading', { name: 'Downside if this decision is wrong' })).toBeVisible();
});

test('summary cards start neutral and show selection only after interaction', () => {
  render(<DashboardViews evaluation={evaluation} inspected="cpu_migration" onInspect={vi.fn()} onEvidence={vi.fn()} />);
  const card = screen.getByRole('heading', { name: 'Observed GPU spend' }).closest('article');
  expect(card).not.toHaveAttribute('data-selected', 'true');
  fireEvent.click(card!);
  expect(card).toHaveAttribute('data-selected', 'true');
});

test('view switching preserves the inspected action and evaluation', () => {
  const onInspect = vi.fn();
  render(<DashboardViews evaluation={evaluation} inspected="idle_session_reclaim" onInspect={onInspect} onEvidence={vi.fn()} />);
  fireEvent.click(screen.getByRole('tab', { name: 'Facility Tour' }));
  expect(screen.getByText('Decision layout — not physical rack location')).toBeVisible();
  fireEvent.click(screen.getByRole('tab', { name: 'Executive View' }));
  expect(screen.getByRole('button', { name: /Reclaim idle interactive sessions/ })).toHaveAttribute('aria-pressed', 'true');
  expect(onInspect).not.toHaveBeenCalled();
});

test('facility tour renders 225 servers in 23 navigable rows', () => {
  render(<DashboardViews evaluation={evaluation} inspected="cpu_migration" onInspect={vi.fn()} onEvidence={vi.fn()} />);
  fireEvent.click(screen.getByRole('tab', { name: 'Facility Tour' }));
  const facility = screen.getByRole('region', { name: 'Full-screen facility tour' });
  expect(facility).toHaveAttribute('data-active-row', 'overview');
  expect(screen.getAllByRole('button', { name: /^Server / })).toHaveLength(225);
  expect(screen.getAllByRole('button', { name: /^View row / })).toHaveLength(23);
  fireEvent.click(screen.getByRole('button', { name: 'View row 7' }));
  expect(facility).toHaveAttribute('data-active-row', '7');
});

test('clicking a server focuses its entire row', () => {
  render(<DashboardViews evaluation={evaluation} inspected="cpu_migration" onInspect={vi.fn()} onEvidence={vi.fn()} />);
  fireEvent.click(screen.getByRole('tab', { name: 'Facility Tour' }));
  const facility = screen.getByRole('region', { name: 'Full-screen facility tour' });
  fireEvent.click(screen.getByRole('button', { name: /^Server 61,/ }));
  expect(facility).toHaveAttribute('data-active-row', '7');
});

test('focused facility rows stack five servers above five servers without overflow rows', () => {
  render(<DashboardViews evaluation={evaluation} inspected="cpu_migration" onInspect={vi.fn()} onEvidence={vi.fn()} />);
  fireEvent.click(screen.getByRole('tab', { name: 'Facility Tour' }));
  fireEvent.click(screen.getByRole('button', { name: 'View row 7' }));
  let focused = document.querySelector('.server-row.active')!;
  expect(focused).toHaveAttribute('data-focus-layout', 'stacked');
  expect(focused.querySelectorAll('.server-bank.upper .server-unit')).toHaveLength(5);
  expect(focused.querySelectorAll('.server-bank.lower .server-unit')).toHaveLength(5);

  fireEvent.click(screen.getByRole('button', { name: 'View row 23' }));
  focused = document.querySelector('.server-row.active')!;
  expect(focused.querySelectorAll('.server-bank.upper .server-unit')).toHaveLength(5);
  expect(focused.querySelectorAll('.server-bank.lower .server-unit')).toHaveLength(0);
});

test('selecting an issue server opens API-backed details on the left and evidence for the applied action', () => {
  const onEvidence = vi.fn();
  render(<DashboardViews evaluation={evaluation} inspected="idle_session_reclaim" onInspect={vi.fn()} onEvidence={onEvidence} />);
  fireEvent.click(screen.getByRole('tab', { name: 'Facility Tour' }));
  const issue = screen.getAllByRole('button', { name: /optimization opportunity/ })[0];
  fireEvent.click(issue);
  expect(screen.getByRole('complementary', { name: 'Selected server details' })).toHaveTextContent('Reclaim idle interactive sessions');
  fireEvent.click(screen.getByRole('button', { name: 'View evidence' }));
  expect(onEvidence).toHaveBeenCalledWith('idle_session_reclaim');
});

test('partial evaluations label issue servers as evidence incomplete rather than faults', () => {
  render(<DashboardViews evaluation={evaluation} inspected="cpu_migration" onInspect={vi.fn()} onEvidence={vi.fn()} />);
  fireEvent.click(screen.getByRole('tab', { name: 'Facility Tour' }));
  expect(screen.getAllByRole('button', { name: /evidence incomplete/ }).length).toBeGreaterThan(0);
  expect(screen.queryByRole('button', { name: /confirmed fault/ })).not.toBeInTheDocument();
});
